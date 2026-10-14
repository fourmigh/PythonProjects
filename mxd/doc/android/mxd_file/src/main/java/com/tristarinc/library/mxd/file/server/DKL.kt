package com.tristarinc.library.mxd.file.server

import com.socks.library.KLog
import com.tristarinc.library.bit.BitByteArray
import com.tristarinc.library.gson.JsonUtils
import com.tristarinc.library.mxd.MXDError
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.*
import com.tristarinc.library.rsa.RSAKey
import com.tristarinc.library.rsa.RSAUtils
import com.tristarinc.library.sha1.SHA1
import com.tristarinc.library.xtea.XTEACSharp
import java.nio.charset.Charset

class DKL(private val rsaPublicKey: ByteArray?, val fromServer: Boolean) : MXD() {

    companion object {
        private const val SignatureSize = 128
        private const val PinHashSize = 20
    }

    var bytesPrimarySignatureType: ByteArray? = null
        private set
    var bytesSecondarySignatureType: ByteArray? = null
        private set
    private var bytesSha1Pin: ByteArray? = null

    fun getRSAPublicKey(): ByteArray? {
        return header.rsaPublicKey
    }

    val KeyGroupsList = KeyGroupsList()

    override fun parse(
        listener: Listener?,
        data: ByteArray,
        checkCRC: Boolean,
        saveData: Boolean,
        readSchemaAndData: Boolean
    ): MXDError {
        val superResult = super.parse(listener, data, checkCRC, saveData, false)
        if (superResult != MXDError.Success) {
            return superResult
        }

        if (bytes == null) {
            return MXDError.FileDataEmpty
        }

        var index = bytes!!.size - SIZE_CRC_BYTES
        if (header.hasSecondarySignature()) {
            index -= SignatureSize
            if (index <= 0) {
                return MXDError.SecondarySignatureDataError
            }
            bytesSecondarySignatureType = ByteArray(SignatureSize)
            System.arraycopy(bytes, index, bytesSecondarySignatureType, 0, SignatureSize)
        }
        if (header.hasPrimarySignature()) {
            index -= SignatureSize
            if (index <= 0) {
                return MXDError.PrimarySignatureDataError
            }
            bytesPrimarySignatureType = ByteArray(SignatureSize)
            System.arraycopy(bytes, index, bytesPrimarySignatureType, 0, SignatureSize)
        }

        if (header.isPINRequired()) {
            //DKL来自服务端，不校验PIN

//            val pin = listener?.onPinInput()
            val pin = if (fromServer) "123456" else listener?.onPinInput()
            if (pin.isNullOrEmpty()) {
                return MXDError.PinNotInput
            }

            index -= PinHashSize
            bytesSha1Pin = ByteArray(PinHashSize)
            System.arraycopy(bytes, index, bytesSha1Pin, 0, PinHashSize)

            val bits = BitByteArray()
            val pins = pin.toByteArray(Charset.forName("US-ASCII"))
            if (pins.isEmpty()) {
                return MXDError.PinInputError
            }
            bits.add(pins)

            val salt = ByteArray(index)
            System.arraycopy(bytes, 0, salt, 0, salt.size)
            bits.add(salt)

            if (!fromServer && !SHA1.checkEquals(bits.build(), bytesSha1Pin)) {
                //根据PIN和文件计算SHA1
                //SHA1(pin + Header + Schema + Data)
                return MXDError.PinError
            }
        }
        val sizeSchemaData = index - headerBytes!!.size
        if (sizeSchemaData <= 0) {
            return MXDError.SchemaAndDataEmpty
        }
        val bytesSchemaData = ByteArray(sizeSchemaData)
        System.arraycopy(bytes, headerBytes!!.size, bytesSchemaData, 0, sizeSchemaData)

        val size = headerBytes!!.size + sizeSchemaData + (bytesSha1Pin?.size ?: 0) + (bytesPrimarySignatureType?.size ?:0) + (bytesSecondarySignatureType?.size ?: 0) + 4
        if (size != bytes!!.size) {
            return MXDError.FileDataError
        }

        if ((rsaPublicKey != null) && (bytesPrimarySignatureType == null)) {
            return MXDError.NoPrimarySignatureData
        }

        if ((bytesPrimarySignatureType != null) && (header.rsaPublicKey != null)) {
            val publicKey = RSAKey.getASN1DERPublicKey(rsaPublicKey ?: header.rsaPublicKey!!)
            val bits = BitByteArray()
            bits.add(headerBytes)
            bits.add(bytesSchemaData)
            bits.add(bytesSha1Pin)
            //用公钥验证Signature1：Header+Schema+Data+SHA1Pin, Signature1，PublicKey
            if (!RSAUtils.verify(bits.build(), bytesPrimarySignatureType!!, publicKey)) {
                return MXDError.RSAVerifyFailed
            }

            bits.clear()
        } else if ((bytesPrimarySignatureType != null) || (header.rsaPublicKey != null)) {
            // one of either the rsa key or signature not present, error
            return MXDError.RSAVerifyFailed
        }
        // else no rsa header or sig, and we have no stored rsa key, so accept insecure file

        if (header.isObfuscation()) {
            val keyBytes = SHA1.encodeBytes(headerBytes) ?: return MXDError.SHA1EncodeFailed
            val key = ByteArray(16)
            System.arraycopy(keyBytes, 0, key, 0, key.size)

            KLog.d("DKL", "encrypt(Schema+Data) : ${bytesSchemaData.toList()}")
            KLog.d("DKL", "header               : ${headerBytes!!.toList()}")
            KLog.d("DKL", "SHA1(header)         : ${keyBytes.toList()}")
            KLog.d("DKL", "key                  : ${key.toList()}")
            val xteaCSharp = XTEACSharp(key)
            val result = xteaCSharp.decipher(bytesSchemaData)
            if (!result) {
                return MXDError.XTEADecipherFailed
            }
        }

        KLog.d("DKL", "decrypt                  : ${bytesSchemaData.toList()}")
        bytes = bytesSchemaData
        super.index = 0
        schema.addAll(readData(readSchema(), false))
        KLog.d("DKL", "XTEA.decrypt")
        KLog.json("DKL", JsonUtils.toJson(schema))

        KLog.d("DKL", "schema for")
        for (sc in schema) {
            when (sc.fieldName) {
                KeyGroupsList::class.simpleName -> {
                    for (kgl in sc.elements) {
                        KLog.d("DKL", "kgl.fieldName: ${kgl.fieldName}")
                        when (kgl.fieldName) {
                            KeyGroup::class.simpleName -> {
                                for (kg in kgl.elements) {

                                    KLog.d("DKL", "kg.elements: ${kg.elements.size}")
                                    val keyGroup = KeyGroup()
                                    for (kgItem in kg.elements) {
                                        when (kgItem.fieldName) {
                                            "Name" -> {
                                                keyGroup.Name = kgItem.data.utf8 ?: ""
                                            }
                                            "Type" -> {
                                                keyGroup.Type = kgItem.data.utf8 ?: ""
                                            }
                                            KeyList::class.simpleName -> {
                                                for (klItem in kgItem.elements) {

                                                    when (klItem.fieldName) {
                                                        KeyEntry::class.simpleName -> {
                                                            for (keItem in klItem.elements) {
                                                                val keyEntry = KeyEntry()
                                                                for (ke in keItem.elements) {
                                                                    when (ke.fieldName) {
                                                                        "Name" -> {
                                                                            keyEntry.Name = ke.data.utf8 ?: ""
                                                                        }
                                                                        "KeyID" -> {
                                                                            keyEntry.KeyID = ke.getDataLong(0)
                                                                        }
                                                                    }
                                                                }
                                                                keyGroup.KeyList.KeyEntry.add(keyEntry)
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                            AccessTimeList::class.simpleName -> {
                                                for (klItem in kgItem.elements) {
                                                    when (klItem.fieldName) {
                                                        AccessTime::class.simpleName -> {
                                                            for (atItem in klItem.elements) {
                                                                val accessTime = AccessTime()
                                                                for (at in atItem.elements) {
                                                                    when (at.fieldName) {
                                                                        "DayOfWeekMask" -> {
                                                                            accessTime.DayOfWeekMask = at.getDataInt(-1)
                                                                        }
                                                                        Time::class.simpleName -> {
                                                                            for (timeItem in at.elements) {
                                                                                val time = Time()
                                                                                for (t in timeItem.elements) {
                                                                                    when (t.fieldName) {
                                                                                        "StartTime", "EndTime" -> {
                                                                                            for (tItem in t.elements) {
                                                                                                when (tItem.fieldName) {
                                                                                                    "Hour" -> {
                                                                                                        when (t.fieldName) {
                                                                                                            "StartTime" -> {
                                                                                                                time.StartTime.Hour = tItem.getDataInt(-1)
                                                                                                            }
                                                                                                            "EndTime" -> {
                                                                                                                time.EndTime.Hour = tItem.getDataInt(-1)
                                                                                                            }
                                                                                                        }
                                                                                                    }
                                                                                                    "Minute" -> {
                                                                                                        when (t.fieldName) {
                                                                                                            "StartTime" -> {
                                                                                                                time.StartTime.Minute = tItem.getDataInt(-1)
                                                                                                            }
                                                                                                            "EndTime" -> {
                                                                                                                time.EndTime.Minute = tItem.getDataInt(-1)
                                                                                                            }
                                                                                                        }
                                                                                                    }
                                                                                                }
                                                                                            }
                                                                                        }
                                                                                    }
                                                                                }
                                                                                accessTime.Time.add(time)
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                                keyGroup.AccessTimeList.AccessTime.add(accessTime)
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    KeyGroupsList.KeyGroup.add(keyGroup)
                                }
                            }
                        }
                    }
                }
            }
        }

        //清理原始数据
        bytes = null
        headerBytes = null
        schema.clear()

        return MXDError.Success
    }

//    fun getSHA1Header(): ByteArray? {
//        if (headerBytes == null) {
//            return null
//        }
//        return SHA1.encodeBytes(headerBytes)
//    }

    fun findKeyEntry(keyID: Long): KeyGroup? {
        if (KeyGroupsList.KeyGroup.isEmpty()) {
            return null
        }
        return KeyGroupsList.KeyGroup.firstNotNullOfOrNull { it.findKeyEntry(keyID) }
    }

    fun isValid(): Boolean {
        return header.isValid()
    }

    fun getValidFromTime(): Int {
        return header.validFromTime
    }

    fun getInitialCreationTime(): Int {
        return header.initialCreationTime ?: 0
    }

    fun getVersion():String?{
        return header.version
    }

    fun getoriginalFileName():String?{
        return header.originalFileName
    }

    fun getFileName():String?{
        return header.fileName
    }

    fun getCustomer():String{
        return header.customer
    }

    fun getCompatibilityLevel(): Byte {
        return header.compatibilityLevel
    }

    fun getInitialCreationTimeZone(): Byte {
        return header.initialCreationTimeZone
    }

    fun getValidFromTimeZone(): Byte {
        return header.validFromTimeZone
    }

    val obfuscationType: Byte
        get() = header.obfuscationType
}

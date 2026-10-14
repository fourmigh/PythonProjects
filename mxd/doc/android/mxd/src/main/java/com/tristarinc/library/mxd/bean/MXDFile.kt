package com.tristarinc.library.mxd.bean

import android.os.SystemClock
import android.text.TextUtils
import com.tristarinc.library.bit.ByteArrayUtils
import com.tristarinc.library.bit.BytesIntUtils
import com.tristarinc.library.bit.BytesNumberUtils
import com.tristarinc.library.converter.BytesHexUtils
import com.tristarinc.library.crc.CustomerCRC32
import com.tristarinc.library.mxd.MXDError
import kotlin.experimental.or

open class MXDFile {

    companion object {
        private const val SLEEP_TIME_IN_WHILE = 10L
        const val SIZE_CRC_BYTES = 4
    }

    var header = Header()
    var headerBytes: ByteArray? = null
    val schema = ArrayList<Element>()
    private var crc = 0

    //原始数据
    var bytes: ByteArray? = null
    //解析原始数据时的索引值
    var index = 0
    private var size = 0
    //文件大小（byte数组个数）
    private var sizeHeader = 0
    private var sizeSchema = 0
    private var sizeData = 0

    interface Listener {
        fun onPinInput(): String
    }

    private var listener: Listener? = null

    fun setListener(listener: Listener? = null) {
        this.listener = listener
    }

    private fun readTLV(): TLV? {
        if (isOutOfArray(bytes)) {
            return null
        }
        val tag = read7BitUint() ?: return null
        if (isOutOfArray(bytes)) {
            return null
        }
        val length = read7BitUint() ?: return null

        val value = ByteArrayUtils.get(bytes!!, index, length)
        index += length
        return TLV(tag, length, value)
    }
    private fun writeTLV(t: Int, v: Byte): List<Byte> {
        return writeTLV(t, BytesNumberUtils.numberToBytes(v))
    }
    private fun writeTLV(t: Int, v: Int): List<Byte> {
        return writeTLV(t, BytesNumberUtils.numberToBytes(v))
    }
    private fun writeTLV(t: Int, v: Long): List<Byte> {
        return writeTLV(t, BytesNumberUtils.numberToBytes(v))
    }
    private fun writeTLV(t: Int, v: String): List<Byte> {
        return writeTLV(t, v.toByteArray())
    }
    private fun writeTLV(t: Int, v: ByteArray): List<Byte> {
        val tagBytes = write7BitUint(t)
        val lengthBytes = write7BitUint(v.size)
        val bytes = ArrayList<Byte>(tagBytes.size + lengthBytes.size + v.size)
        bytes.addAll(write7BitUint(t).toList())
        bytes.addAll(write7BitUint(v.size).toList())
        bytes.addAll(v.toList())
        return bytes
    }

    open fun parse(listener: Listener?, data: ByteArray, checkCRC: Boolean = false, saveData: Boolean = false, readSchemaAndData: Boolean = true): MXDError {
        if (data.isEmpty()) {
            return MXDError.FileDataEmpty
        }
        if (checkCRC && !CustomerCRC32.check(data)) {
            return MXDError.BadChecksum
        }
        bytes = data
        size = data.size
        index = 0
        readHeader()

        if (readSchemaAndData && (header.contentType == ContentType.SchemaData.ordinal.toByte())) {
            schema.addAll(readData(readSchema()))
        }

        //CRC
        val crcBytes = ByteArrayUtils.get(data, data.size - SIZE_CRC_BYTES, SIZE_CRC_BYTES)
        crc = BytesIntUtils.bytesToInt(crcBytes)

        if (!saveData && readSchemaAndData) {
            bytes = null
        }
        return MXDError.Success
    }

    private fun readHeader() {
        if (bytes == null) {
            return
        }
        while (index < bytes!!.size) {
            SystemClock.sleep(SLEEP_TIME_IN_WHILE)
            val tlv = readTLV() ?: break
            val value = tlv.v

            when (tlv.t) {
                Tag.EndOfHeader.ordinal -> {
                    //End of header.
                    headerBytes = ByteArray(index)
                    System.arraycopy(bytes!!, 0, headerBytes!!, 0, index)
                    break
                }
                Tag.FileType.ordinal -> {
                    //File type. Must be first field
                    if (value != null) {
                        header.fileType = String(value)
                    }
                }
                Tag.CompatibilityLevel.ordinal -> {
                    //Compatibility level
                    if (value != null) {
                        header.compatibilityLevel = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.MajorVersion.ordinal -> {
                    //Deprecated
                }
                Tag.MinorVersion.ordinal -> {
                    //Deprecated
                }
                Tag.ObfuscationType.ordinal -> {
                    //Obfuscation type
                    if (value != null) {
                        header.obfuscationType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.CompressionType.ordinal -> {
                    //Compression type
                    if (value != null) {
                        header.compressionType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.PrimarySignatureType.ordinal -> {
                    //Primary Signature type
                    if (value != null) {
                        header.primarySignatureType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.SecondarySignatureType.ordinal -> {
                    //Secondary Signature type
                    if (value != null) {
                        header.secondarySignatureType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.PINType.ordinal -> {
                    //PIN type
                    if (value != null) {
                        header.pinType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.ContentType.ordinal -> {
                    //Content Type
                    if (value != null) {
                        header.contentType = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.ContentLength.ordinal -> {
                    //Content length
                    if (value != null) {
                        header.contentLength = BytesIntUtils.bytesToInt(value)
                    }
                }
                Tag.CompressedContentLength.ordinal -> {
                    //Compressed Content length
                    if (value != null) {
                        header.compressedContentLength = BytesIntUtils.bytesToInt(value)
                    }
                }
                Tag.NumberOfPINDigits.ordinal -> {
                    //Number of PIN digits
                    if (value != null) {
                        header.numberOfPINDigits = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.Customer.ordinal -> {
                    //Customer - a user readable string
                    if (value != null) {
                        header.customer = String(value)
                    }
                }
                Tag.Origin.ordinal -> {
                    //Origin(Computer/Machine name)
                    if (value != null) {
                        header.origin = String(value)
                    }
                }
                Tag.UserName.ordinal -> {
                    //User name
                    if (value != null) {
                        header.userName = String(value)
                    }
                }
                Tag.InitialCreationTime.ordinal -> {
                    //Initial creation time
                    if (value != null) {
                        header.initialCreationTime = BytesIntUtils.bytesToInt(value)
                    }
                }
                Tag.FinalModificationTime.ordinal -> {
                    //Final modification time
                    if (value != null) {
                        header.finalModificationTime = BytesIntUtils.bytesToInt(value)
                    }
                }
                Tag.MachineUniqueID.ordinal -> {
                    //Machine Unique ID
                    if (value != null) {
//                        header.machineUniqueID = BytesIntUtils.bytesToInt(value)
                        header.machineUniqueID = BytesHexUtils.bytesToHexLong(value)
                    }
                }
                Tag.ValidFromTime.ordinal -> {
                    //Valid From Time
                    if (value != null) {
                        header.validFromTime = BytesIntUtils.bytesToInt(value)
                    }
                }
                Tag.ApplicationBaseAddress.ordinal -> {
                    //Application Base Address
                    if (value != null) {
                        header.applicationBaseAddress = String(value)
                    }
                }
                Tag.ApplicationEntryPoint.ordinal -> {
                    //Application Entry Point
                    if (value != null) {
                        header.applicationEntryPoint = String(value)
                    }
                }
                Tag.Version.ordinal -> {
                    //Version
                    if (value != null) {
                        header.version = String(value)
                    }
                }
                Tag.RSAPublicKey.ordinal -> {
                    //RSA Public Key
                    header.rsaPublicKey = value
                }
                Tag.ElectronicsVersion.ordinal -> {
                    //Electronics version
                    if (value != null) {
                        header.electronicsVersion = String(value)
                    }
                }
                Tag.InitialCreationTimeZone.ordinal -> {
                    //Initial creation time zone
                    if (value != null) {
                        header.initialCreationTimeZone = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.FinalModificationTimeZone.ordinal -> {
                    //Final modification time zone
                    if (value != null) {
                        header.finalModificationTimeZone = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.ValidFromTimeZone.ordinal -> {
                    //Valid from time zone
                    if (value != null) {
                        header.validFromTimeZone = BytesIntUtils.bytesToInt(value).toByte()
                    }
                }
                Tag.OriginalFileName.ordinal -> {
                    //Original file name
                    if (value != null) {
                        header.originalFileName = String(value)
                    }
                }
            }
        }
    }

    protected fun readSchema(): List<Element> {
        val rst = ReadSchema()

        var done = false
        while (!done) {
            var schemaToken = readByte()?.toInt() ?: break
            if (schemaToken < 0) {
                schemaToken += 256
            }

            if (schemaToken < SchemaTokenType.MXDDT_END_RECORD) {
                // is a data type, not a schema token
                var array = false
                if (schemaToken and SchemaTokenType.MXD_ARRAY_TYPE > 0) {
                    array = true
                    schemaToken = schemaToken and SchemaTokenType.MXD_ARRAY_TYPE.inv()
                }

                var recNum = -1
                if (schemaToken == DataType.MXDDT_RECORD.ordinal) {
                    recNum = read7BitUint() ?: break
                }

                val recName = readString()
                val element = Element()
                val dataTypes = DataType.entries.toTypedArray()
                if (schemaToken < 0 || schemaToken >= dataTypes.size) {
                    return emptyList()
                }
                element.dataType = DataType.valueOf(dataTypes[schemaToken].name)
                element.isArray = array
                element.recNo = recNum
                element.fieldName = recName
                rst.add(element)
            }
            else if (schemaToken == SchemaTokenType.MXDDT_START_CHOICE) {
                rst.startChoice()
            } else if (schemaToken == SchemaTokenType.MXDDT_END_CHOICE) {
                rst.endChoice()
            }
            else {
                done = schemaToken == SchemaTokenType.MXDDT_END_SCHEMA
                // is a schema token
                if ((schemaToken == SchemaTokenType.MXDDT_END_RECORD) || done) {
                    rst.endRecord()
                }
            }
        }
        return rst.endSchema()
    }

    protected fun readData(records: List<Element>, containsCRC: Boolean = true): List<Element> {

        if (bytes == null) {
            return ArrayList()
        }
        val data = ByteArrayUtils.get(bytes!!, index, bytes!!.size - index - (if (containsCRC) SIZE_CRC_BYTES else 0)) ?: return ArrayList()
        val readData = ReadData(data, records)
        return readData.read()
    }

    private fun readByte(): Byte? {
        if (isOutOfArray(bytes)) {
            return null
        }
        val byte = bytes!![index]
        index ++
        return byte
    }

    private fun readString(): String {
        val byteArray = readByteArray()
        if (byteArray != null) {
            return try {
                String(byteArray)
            } catch (e: Exception) {
                ""
            }
        }
        return ""
    }
    protected fun writeEnum(enum: Enum<*>): List<Byte> {
        return writeString(enum.name)
    }
    protected fun writeString(str: String): List<Byte> {
        val bytes = str.toByteArray()
        return writeByteArray(bytes)
    }

    private fun readBoolean(): Boolean {
        if (isOutOfArray(bytes)) {
            return false
        }
        val bool = bytes!![index] == 1.toByte()
        index ++
        return bool
    }
    protected fun writeBoolean(boolean: Boolean): List<Byte> {
        return listOf(if (boolean) 1 else 0)
    }

    private fun readByteArray(): ByteArray? {
        if (isOutOfArray(bytes)) {
            return null
        }
        val length = read7BitUint() ?: return null
        if (length <= 0) {
            return null
        }
        val bs = ByteArrayUtils.get(bytes!!, index, length)
        index += length
        return bs
    }
    private fun writeByteArray(byteArray: ByteArray): List<Byte> {
        val length = byteArray.size
        return write7BitUint(length) + byteArray.toList()
    }

    private fun isOutOfArray(data: ByteArray?): Boolean {
        if (data == null) {
            return true
        }
        val result = index < 0 || index >= data.size
        return result
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////
    open fun create(fileType: FileType, origin: String, machineUniqueID: Long): MXDFile {
        header.fileType = fileType.name
        header.origin = origin
        header.machineUniqueID = machineUniqueID
        header.initialCreationTime = (System.currentTimeMillis() / 1000).toInt()
        clearDataSize()
        return this
    }

    fun build(): ByteArray {
        val bits = ArrayList<Byte>()
        //Header
        writeHeader(bits)
        //Schema
        try {
            writeSchema(bits)
        }catch (e: Exception){
            e.printStackTrace()
        }

        //Data
        writeData(bits)
        val datas = bits.toByteArray()
        val crc = CustomerCRC32.calc(datas, 0, datas.size)
        val crcBytes = BytesIntUtils.intToBytes(crc)
        bits.addAll(crcBytes.toList())
        //CRC
        return bits.toByteArray()
    }

    private fun read7BitUint(): Int? {
        var value = 0
        var data: UByte
        var i = 0
        do {
            data = readByte()?.toUByte() ?: return null
            value = value or ((data and 0x7F.toUByte()).toInt() shl i)
            i += 7
        } while ((data and 0x80.toUByte()) > 0.toUByte())

        return value
    }

    private fun read7BitInt(): Int? {
        var value = 0
        var data: UByte
        var i = 0
        do {
            data = readByte()?.toUByte() ?: return null
            value = value or ((data and 0x7F.toUByte()).toInt() shl i)
            i += 7
        } while ((data and 0x80.toUByte()) > 0.toUByte())

        if (data and 0x40.toUByte() > 0.toUByte()) {
            value = value or (-1 shl i)
        }

        return value
    }

    protected fun write7BitUint(uLong: Long): List<Byte> {
        var value = uLong
        val bytes = ArrayList<Byte>(5)
        do {
            var data = (value and 0x7f).toByte()
            if (value > 127) {
                data = data or 0x80.toByte()
            }
            value = value shr 7
            bytes.add(data)
        } while (value > 0)
        return bytes
    }

    protected fun write7BitUint(uLong: Int): List<Byte> {
        return write7BitUint(uLong.toLong())
    }

    protected fun write7BitInt(long: Int): List<Byte> {
        return write7BitInt(long.toLong())
    }
    protected fun write7BitInt(long: Long): List<Byte> {
        var value = long
        val negative = value < 0
        var done = false
        val bytes = ArrayList<Byte>(5)
        while (!done) {
            var data = (value and 0x7f).toByte()
            if ((value > 63) || (value < -64)) {
                value = value shr 7
                data = data or 0x80.toByte()
            }
            else
            {
                done = true
                if (negative) {
                    data = data or 0x40.toByte()
                }
            }
            bytes.add(data)
        }
        return bytes
    }

    private fun writeHeader(bits: ArrayList<Byte>) {
        for (i in Tag.FileType.ordinal until Tag.OriginalFileName.ordinal + 1) {
            when (i) {
                Tag.FileType.ordinal -> {
                    //File type. Must be first field
                    if (header.fileType != null) {
                        val bytes = writeTLV(i, header.fileType!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.CompatibilityLevel.ordinal -> {
                    //Compatibility level
                    val bytes = writeTLV(i, header.compatibilityLevel)
                    bits.addAll(bytes)
                }
                Tag.MajorVersion.ordinal -> {
                    //Deprecated
                }
                Tag.MinorVersion.ordinal -> {
                    //Deprecated
                }
                Tag.ObfuscationType.ordinal -> {
                    //Obfuscation type
                    val bytes = writeTLV(i, header.obfuscationType)
                    bits.addAll(bytes)
                }
                Tag.CompressionType.ordinal -> {
                    //Compression type
                    val bytes = writeTLV(i, header.compressionType)
                    bits.addAll(bytes)
                }
                Tag.PrimarySignatureType.ordinal -> {
                    //Primary Signature type
                    val bytes = writeTLV(i, header.primarySignatureType)
                    bits.addAll(bytes)
                }
                Tag.SecondarySignatureType.ordinal -> {
                    //Secondary Signature type
                    val bytes = writeTLV(i, header.secondarySignatureType)
                    bits.addAll(bytes)
                }
                Tag.PINType.ordinal -> {
                    //PIN type
                    val bytes = writeTLV(i, header.pinType)
                    bits.addAll(bytes)
                }
                Tag.ContentType.ordinal -> {
                    //Content Type
                    val bytes = writeTLV(i, header.contentType)
                    bits.addAll(bytes)
                }
                Tag.ContentLength.ordinal -> {
                    //Content length
                    if (header.contentLength != null) {
                        val bytes = writeTLV(i, header.contentLength!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.CompressedContentLength.ordinal -> {
                    //Compressed Content length
                    if (header.compressedContentLength != null) {
                        val bytes = writeTLV(i, header.compressedContentLength!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.NumberOfPINDigits.ordinal -> {
                    //Number of PIN digits
                    val bytes = writeTLV(i, header.numberOfPINDigits)
                    bits.addAll(bytes)
                }
                Tag.Customer.ordinal -> {
                    //Customer - a user readable string
                    val bytes = writeTLV(i, header.customer)
                    bits.addAll(bytes)
                }
                Tag.Origin.ordinal -> {
                    //Origin(Computer/Machine name)
                    val bytes = writeTLV(i, header.origin)
                    bits.addAll(bytes)
                }
                Tag.UserName.ordinal -> {
                    //User name
                    val bytes = writeTLV(i, header.userName)
                    bits.addAll(bytes)
                }
                Tag.InitialCreationTime.ordinal -> {
                    //Initial creation time
                    if (header.initialCreationTime != null) {
                        val bytes = writeTLV(i, header.initialCreationTime!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.FinalModificationTime.ordinal -> {
                    //Final modification time
                    if (header.finalModificationTime != null) {
                        val bytes = writeTLV(i, header.finalModificationTime!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.MachineUniqueID.ordinal -> {
                    //Machine Unique ID
                    val bytes = writeTLV(i, BytesHexUtils.hexLongToBytes(header.machineUniqueID))
                    bits.addAll(bytes)
                }
                Tag.ValidFromTime.ordinal -> {
                    //Valid From Time
                    val bytes = writeTLV(i, header.validFromTime)
                    bits.addAll(bytes)
                }
                Tag.ApplicationBaseAddress.ordinal -> {
                    //Application Base Address
                    if (header.applicationBaseAddress != null) {
                        val bytes = writeTLV(i, header.applicationBaseAddress!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.ApplicationEntryPoint.ordinal -> {
                    //Application Entry Point
                    if (header.applicationEntryPoint != null) {
                        val bytes = writeTLV(i, header.applicationEntryPoint!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.Version.ordinal -> {
                    //Version
                    if (header.version != null) {
                        val bytes = writeTLV(i, header.version!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.RSAPublicKey.ordinal -> {
                    //RSA Public Key
                    if (header.rsaPublicKey != null) {
                        val bytes = writeTLV(i, header.rsaPublicKey!!)
                        bits.addAll(bytes)
                    }
                }
                Tag.ElectronicsVersion.ordinal -> {
                    //Electronics version
                    val bytes = writeTLV(i, header.electronicsVersion)
                    bits.addAll(bytes)
                }
                Tag.InitialCreationTimeZone.ordinal -> {
                    //Initial creation time zone
                    val bytes = writeTLV(i, header.initialCreationTimeZone)
                    bits.addAll(bytes)
                }
                Tag.FinalModificationTimeZone.ordinal -> {
                    //Final modification time zone
                    val bytes = writeTLV(i, header.finalModificationTimeZone)
                    bits.addAll(bytes)
                }
                Tag.ValidFromTimeZone.ordinal -> {
                    //Valid from time zone
                    val bytes = writeTLV(i, header.validFromTimeZone)
                    bits.addAll(bytes)
                }
                Tag.OriginalFileName.ordinal -> {
                    //Original file name
                    if (header.originalFileName != null) {
                        val bytes = writeTLV(i, header.originalFileName!!)
                        bits.addAll(bytes)
                    }
                }
            }
        }
        bits.add(Tag.EndOfHeader.ordinal.toByte())
        bits.add(0.toByte())
    }

    private fun writeSchema(bits: ArrayList<Byte>) {
        for (i in 0 until schema.size) {
            val record = try {
                schema[i]
            } catch (e: Exception) {
                continue
            }
            if (record.isChoice) {
                bits.add(SchemaTokenType.MXDDT_START_CHOICE.toByte())
            }

            for (element in record.elements) {
                val nameData = element.fieldName

                var dataType = element.dataType.ordinal.toByte()
                if (element.isArray) {
                    dataType = dataType or SchemaTokenType.MXD_ARRAY_TYPE.toByte()
                }
                bits.add(dataType)

                if (element.dataType == DataType.MXDDT_RECORD) {
                    val recordNum = element.recNo
                    val bytes = write7BitUint(recordNum)
                    bits.addAll(bytes)
                }

                val bytes = writeString(nameData)
                bits.addAll(bytes)
            }

            if (record.isChoice) {
                bits.add(SchemaTokenType.MXDDT_END_CHOICE.toByte())
            }

            if (i < (schema.size - 1)) {
                bits.add(SchemaTokenType.MXDDT_END_RECORD.toByte())
            }
        }
        bits.add(SchemaTokenType.MXDDT_END_SCHEMA.toByte())
    }

    open fun writeData(bits: ArrayList<Byte>) {
        for (sc in schema) {
            for (element in sc.elements) {
                when (element.dataType.ordinal) {
                    DataType.MXDDT_BOOL.ordinal -> {
                        if (element.data.bool != null) {
                            val value = writeBoolean(element.data.bool!!)
                            bits.addAll(value)
                        }
                    }
                    DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
                        element.data.bytes?.let {
                            val value = writeByteArray(it)
                            bits.addAll(value)
                        }
                    }
                    DataType.MXDDT_UTF8_STRING.ordinal -> {
                        if (element.data.utf8 != null) {
                            val value = writeString(element.data.utf8!!)
                            bits.addAll(value)
                        }
                    }
                    DataType.MXDDT_ENUM.ordinal -> {
                        if (element.data.enum != null) {
                            val value = writeString(element.data.enum!!)
                            bits.addAll(value)
                        }
                    }
                    DataType.MXDDT_VAR_UINT64.ordinal -> {
                        if (element.data.uint64 != null) {
                            val value = write7BitUint(element.data.uint64!!)
                            bits.addAll(value)
                        }
                    }
                    DataType.MXDDT_VAR_INT64.ordinal -> {
                        if (element.data.int64 != null) {
                            val value = write7BitInt(element.data.int64!!)
                            bits.addAll(value)
                        }
                    }
                }
            }
        }
        bits.add(SchemaTokenType.MXDDT_END_DATA.toByte())
    }

    /**
     * 在最后一个schema中查找序号
     * 如果是Choice，结果+1
     */
    open fun findIndex(fieldName: String?): Int {
        var index = -1
        if (TextUtils.isEmpty(fieldName) || schema.isEmpty()) {
            return index
        }
        val lastSchema = schema[schema.size - 1]
        for (i in 0 until lastSchema.elements.size) {
            val element = lastSchema.elements[i]
            if (element.fieldName == fieldName) {
                index = i
                break
            }
        }
        if (index < 0) {
            return index
        }
        if (lastSchema.isChoice) {
            index ++
        }
        return index
    }

    fun calHeaderSize(retry: Boolean = false) {
        if (sizeHeader > 0 && !retry) {
            return
        }
        val bvtes = ArrayList<Byte>()
        writeHeader(bvtes)
        sizeHeader = bvtes.size
    }
    fun calSchemaSize(retry: Boolean = false) {
        if (sizeSchema > 0 && !retry) {
            return
        }
        val bvtes = ArrayList<Byte>()
        try {
            writeSchema(bvtes)
        }catch (e: Exception){
            e.printStackTrace()
        }
        sizeSchema = bvtes.size
    }
    fun calDataSize(size: Int) {
        sizeData += size
    }
    private fun clearDataSize() {
        sizeData = 0
    }
    fun calFileSize(): Int {
        return sizeHeader + sizeSchema + sizeData + SIZE_CRC_BYTES
    }
}

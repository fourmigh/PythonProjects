package com.tristarinc.library.mxd.bean

class Header {

    //1
    var fileType: String? = null
    //2
    var compatibilityLevel: Byte = 0
    //5
    var obfuscationType: Byte = 0
    //6
    var compressionType: Byte = 0
    //7
    var primarySignatureType: Byte = 0
    //8
    var secondarySignatureType: Byte = 0
    //9
    var pinType: Byte = 0
    //10
    var contentType: Byte = ContentType.SchemaData.ordinal.toByte()
    //11
    var contentLength: Int? = null
    //12
    var compressedContentLength: Int? = null
    //13
    var numberOfPINDigits = 4.toByte()
    //14
    var customer = ""
    //15
    var origin = ""
    //16
    var userName = ""
    //17
    var initialCreationTime: Int? = null
    //18
    var finalModificationTime: Int? = null
    //19
    var machineUniqueID: Long = 0
    //20
    var validFromTime = (System.currentTimeMillis() / 1000).toInt()
    //21
    var applicationBaseAddress: String? = null//Unsigned integer
    //22
    var applicationEntryPoint: String? = null//Unsigned integer
    //23
    var version: String? = null
    //24
    var rsaPublicKey: ByteArray? = null
    //25
    var electronicsVersion = "AURA_1"
    //26
    var initialCreationTimeZone = 0.toByte()
    //27
    var finalModificationTimeZone = 0.toByte()
    //28
    var validFromTimeZone = 0.toByte()
    //29
    var originalFileName: String? = null

    //customized variable
    var fileName:String? = null

    //TEAn of schema and data with the key = first 16 bytes of SHA-1 of header.
    fun isObfuscation(): Boolean {
        return obfuscationType == 1.toByte()
    }

    fun isCompression(): Boolean {
        return compressionType != 0.toByte()
    }

    fun hasPrimarySignature(): Boolean {
        return primarySignatureType == 1.toByte()
    }

    fun hasSecondarySignature(): Boolean {
        return secondarySignatureType == 1.toByte()
    }

    fun isPINRequired(): Boolean {
        return pinType == 1.toByte()
    }

    fun isValid(): Boolean {
        return validFromTime <= (System.currentTimeMillis() / 1000)
    }

    /**
     * 生效日期和当前时间差值
     * < 0：还未生效
     * >= 0：已生效，越小离当前越近，最小的就是当前DKL
     */
    fun validTimeNearNow(): Int {
        return (System.currentTimeMillis() / 1000 - validFromTime).toInt()
    }
}
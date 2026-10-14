package com.tristarinc.library.mxd.bean

@Deprecated("Element")
class MxdElementAndRecord {

    var isElement: Boolean? = null
    var fieldName: String? = null

    //Element
    var dataType = DataType.MXDDT_NULL.ordinal.toByte()
    var isArray = false

    //Record
    var recordNumber: Int? = null
    var isChoice = false
    val elements = ArrayList<MxdElementAndRecord>()

    //Data
    val value = SchemaData()

    fun createElement(fieldName: String, dataType: Byte, isArray: Boolean) {
        this.fieldName = fieldName
        this.dataType = dataType
        this.isArray = isArray
        this.isElement = true
    }

    fun createRecord(fieldName: String, recordNumber: Int, isArray: Boolean) {
        this.fieldName = fieldName
        this.recordNumber = recordNumber
        this.isArray = isArray
        this.dataType = DataType.MXDDT_RECORD.ordinal.toByte()
        this.isElement = false
    }

    fun getBooleanValue(): Boolean? {
        return value.bool
    }

    fun getByteArrayValue(): ByteArray? {
        return value.bytes
    }

    fun getUTF8Value(): String? {
        return value.utf8
    }

    fun getEnumValue(): String? {
        return value.enum
    }

    fun getUInt64Value(): Long? {
        return value.uint64
    }

    fun getInt64Value(): Long? {
        return value.int64
    }

    //Data
    interface Listener {
        fun onGetValue(key: String, bool: Boolean)
        fun onGetValue(key: String, bytes: ByteArray)
        fun onGetValue(key: String, str: String)
        fun onGetValue(key: String, long: Long)
        fun onError(key: String, dataType: Byte)
    }
    fun getValue(listener: Listener) {
        when (dataType.toInt()) {
            DataType.MXDDT_NULL.ordinal -> {
                if (fieldName != null) {
                    listener.onError(fieldName!!, dataType)
                }
            }
            DataType.MXDDT_RECORD.ordinal -> {
            }
            DataType.MXDDT_BOOL.ordinal -> {
                if (fieldName != null) {
                    if (value.bool == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.bool ?: false)
                    }
                }
            }
            DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
                if (fieldName != null) {
                    if (value.bytes == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.bytes!!)
                    }
                }
            }
            DataType.MXDDT_UTF8_STRING.ordinal -> {
                if (fieldName != null) {
                    if (value.utf8 == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.utf8!!)
                    }
                }
            }
            DataType.MXDDT_ENUM.ordinal -> {
                if (fieldName != null) {
                    if (value.enum == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.enum!!)
                    }
                }
            }
            DataType.MXDDT_VAR_UINT64.ordinal-> {
                if (fieldName != null) {
                    if (value.uint64 == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.uint64!!)
                    }
                }
            }
            DataType.MXDDT_VAR_INT64.ordinal -> {
                if (fieldName != null) {
                    if (value.int64 == null) {
                        listener.onError(fieldName!!, dataType)
                    } else {
                        listener.onGetValue(fieldName!!, value.int64!!)
                    }
                }
            }
            else -> {
                if (fieldName != null) {
                    listener.onError(fieldName!!, dataType)
                }
            }
        }
    }

    fun createRecord(recordNumber: Int, isChoice: Boolean, elements: List<MxdElementAndRecord>) {
        this.recordNumber = recordNumber
        this.isChoice = isChoice
        this.elements.addAll(elements)
    }
}
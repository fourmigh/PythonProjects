package com.tristarinc.library.mxd.bean

import android.text.TextUtils

@Deprecated("")
class SchemaField {

    var dataType = DataType.MXDDT_NULL.ordinal
    var fieldNameLength = 0
    var fieldName = ""

    var value = SchemaData()

    fun parse(tlv: TLV): SchemaField {
        dataType = tlv.t.toInt()
        fieldNameLength = tlv.l.toInt()
        if (tlv.v != null) {
            fieldName = String(tlv.v!!)
        }

        return this
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

    interface Listener {
        fun onGetValue(key: String, bool: Boolean)
        fun onGetValue(key: String, bytes: ByteArray)
        fun onGetValue(key: String, str: String)
        fun onGetValue(key: String, int: Long)
        fun onError(key: String, dataType: Int)
    }
    fun getValue(listener: Listener) {
        when (dataType) {
            DataType.MXDDT_NULL.ordinal, DataType.MXDDT_RECORD.ordinal -> {
                listener.onError(fieldName, dataType)
            }
            DataType.MXDDT_BOOL.ordinal -> {
                if (value.bool == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.bool ?: false)
                }
            }
            DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
                if (value.bytes == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.bytes!!)
                }
            }
            DataType.MXDDT_UTF8_STRING.ordinal -> {
                if (value.utf8 == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.utf8!!)
                }
            }
            DataType.MXDDT_ENUM.ordinal -> {
                if (value.enum == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.enum!!)
                }
            }
            DataType.MXDDT_VAR_UINT64.ordinal -> {
                if (value.uint64 == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.uint64!!)
                }
            }
            DataType.MXDDT_VAR_INT64.ordinal -> {
                if (value.int64 == null) {
                    listener.onError(fieldName, dataType)
                } else {
                    listener.onGetValue(fieldName, value.int64!!)
                }
            }
            else -> {
                listener.onError(fieldName, dataType)
            }
        }
    }

    fun create(dataType: DataType, fieldName: String, value: Any): Boolean {

        if (TextUtils.isEmpty(fieldName)) {
            return false
        }

        if (dataType == DataType.MXDDT_BOOL && value !is Boolean) {
            return false
        }
        if (dataType == DataType.MXDDT_HEX_BYTE_ARRAY && value !is ByteArray) {
            return false
        }
        if (dataType == DataType.MXDDT_UTF8_STRING && value !is String) {
            return false
        }
        if (dataType == DataType.MXDDT_ENUM && value !is String) {
            return false
        }
        if (dataType == DataType.MXDDT_VAR_UINT64 && value !is Int) {
            return false
        }
        if (dataType == DataType.MXDDT_VAR_INT64 && value !is Int) {
            return false
        }

        when (dataType.ordinal) {
            DataType.MXDDT_BOOL.ordinal -> {
                try {
                    this.value.bool = value as Boolean
                } catch (e: Exception) {
                    return false
                }
            }
            DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
                try {
                    this.value.bytes = value as ByteArray
                } catch (e: Exception) {
                    return false
                }
            }
            DataType.MXDDT_UTF8_STRING.ordinal -> {
                try {
                    this.value.utf8 = value as String
                } catch (e: Exception) {
                    return false
                }
            }
            DataType.MXDDT_ENUM.ordinal -> {
                try {
                    this.value.enum = value as String
                } catch (e: Exception) {
                    return false
                }
            }
            DataType.MXDDT_VAR_UINT64.ordinal -> {
                try {
                    this.value.uint64 = value as Long
                } catch (e: Exception) {
                    return false
                }
            }
            DataType.MXDDT_VAR_INT64.ordinal -> {
                try {
                    this.value.int64 = value as Long
                } catch (e: Exception) {
                    return false
                }
            }
            else -> {
                return false
            }
        }
        this.dataType = dataType.ordinal
        this.fieldName = fieldName
        this.fieldNameLength = fieldName.length
        return true
    }
}
package com.tristarinc.library.mxd.bean

class SchemaData: Cloneable {

    var bool: Boolean? = null
    var bytes: ByteArray? = null
    var utf8: String? = null
    var enum: String? = null
    var uint64: Long? = null
    var int64: Long? = null

    public override fun clone(): SchemaData {
        val schemaData = SchemaData()
        schemaData.bool = bool
        schemaData.bytes = bytes
        schemaData.utf8 = utf8
        schemaData.enum = enum
        schemaData.uint64 = uint64
        schemaData.int64 = int64
        return schemaData
    }
}
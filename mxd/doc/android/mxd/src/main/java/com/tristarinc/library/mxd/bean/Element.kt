package com.tristarinc.library.mxd.bean

class Element: CommAttr, Cloneable {

    var dataType = DataType.MXDDT_NULL
    var fieldName = ""

    val elements = ArrayList<Element>()

    var data = SchemaData()

    fun getDataLong(defValue: Long): Long {
        return when (dataType) {
            DataType.MXDDT_VAR_INT64 -> data.int64 ?: defValue
            DataType.MXDDT_VAR_UINT64 -> data.uint64 ?: defValue
            else -> defValue
        }
    }

    fun getDataInt(defValue: Int): Int {
        val long = getDataLong(defValue.toLong())
        return long.toInt()
    }

    public override fun clone(): Element {
        val element = Element()
        element.dataType = dataType
        element.fieldName = fieldName
        element.recNo = recNo
        element.isArray = isArray
        element.isChoice = isChoice
        element.data = data.clone()
        if (elements.isNotEmpty()) {
            for (e in elements) {
                element.elements.add(e.clone())
            }
        }
        return element
    }

    constructor()
    constructor(dataType: DataType, fieldName: String) {
        this.dataType = dataType
        this.fieldName = fieldName
    }
    constructor(dataType: DataType, fieldName: String, uint64: Long) {
        this.dataType = dataType
        this.fieldName = fieldName
        this.data.uint64 = uint64
    }
    constructor(dataType: DataType, fieldName: String, uint64: Int) {
        this.dataType = dataType
        this.fieldName = fieldName
        this.data.uint64 = uint64.toLong()
    }
    constructor(dataType: DataType, fieldName: String, enum: String) {
        this.dataType = dataType
        this.fieldName = fieldName
        this.data.enum = enum
    }
    constructor(recNo: Int, fieldName: String?, isArray: Boolean = false, isChoice: Boolean = false) {
        this.recNo = recNo
        this.dataType = DataType.MXDDT_RECORD
        this.fieldName = fieldName ?: ""
        this.isArray = isArray
        this.isChoice = isChoice
    }
    constructor(dataType: DataType, fieldName: String, isArray: Boolean) {
        this.dataType = dataType
        this.fieldName = fieldName
        this.isArray = isArray
    }
}
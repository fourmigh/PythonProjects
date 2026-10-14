package com.tristarinc.library.mxd.bean

@Deprecated("Element")
class MxdRecordElementDef(name: String, isArray: Boolean, var recordNumber: Int): MxdElementDef(name, DataType.MXDDT_RECORD, isArray) {

}
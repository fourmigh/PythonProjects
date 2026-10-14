package com.tristarinc.library.mxd.file.client

import com.tristarinc.library.mxd.bean.DataType
import com.tristarinc.library.mxd.bean.Element
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.enums.BackOfficeRespEnum

class BOR(origin: String, machineUniqueID: Long) : MXD() {

    init {
        create(FileType.BOR, origin, machineUniqueID)
    }

    var SerialNo = 0L
    var Response = BackOfficeRespEnum.SUCCESS

    fun setSchemaData(serialNo: Long, response: BackOfficeRespEnum): BOR {

        SerialNo = serialNo
        Response = response

        val base = Element()

        var element = Element(DataType.MXDDT_VAR_UINT64, "SerialNo", SerialNo)
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "SerialNo"
//        element.data.uint64 = SerialNo
        base.elements.add(element)

        element = Element(DataType.MXDDT_ENUM, "Response", Response.name)
//        element.dataType = DataType.MXDDT_ENUM
//        element.fieldName = "Response"
//        element.data.enum = Response
        base.elements.add(element)

        schema.add(base)
        return this
    }
}
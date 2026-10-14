package com.tristarinc.library.mxd.file.server

import com.tristarinc.library.mxd.MXDError
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.enums.BackOfficeCmdEnum

class BOC : MXD() {

    var SerialNo: Long? = null
    var Command = BackOfficeCmdEnum.UNDEFINED
    var NumberPar1: Long? = null
    var StringPar1: String? = null

    var commandString: String? = null

    override fun parse(listener: Listener?, data: ByteArray, checkCRC: Boolean, saveData: Boolean, readSchemaAndData: Boolean): MXDError {

        val superResult = super.parse(listener, data, checkCRC, saveData, readSchemaAndData)
        if (superResult != MXDError.Success) {
            return superResult
        }

        if (schema.size != 1) {
            return MXDError.SchemaSizeError
        }
        for (schema in schema[0].elements) {
            when (schema.fieldName) {
                "SerialNo" -> {
                    SerialNo = schema.getDataLong(0)
                }
                "Command" -> {
                    commandString = schema.data.utf8
                    Command = commandString?.let {
                        cmd -> BackOfficeCmdEnum.entries.firstOrNull { it.name.equals(cmd, true) }
                    } ?: BackOfficeCmdEnum.UNDEFINED
                }
                "NumberPar1" -> {
                    NumberPar1 = schema.getDataLong(0)
                }
                "StringPar1" -> {
                    StringPar1 = schema.data.utf8
                }
            }
        }
        return MXDError.Success
    }

    fun create(serialNo: Long, command: BackOfficeCmdEnum, numberPar1: Long, stringPar1: String): BOC {
        this.SerialNo = serialNo
        this.Command = command
        this.NumberPar1 = numberPar1
        this.StringPar1 = stringPar1
        return this
    }
}
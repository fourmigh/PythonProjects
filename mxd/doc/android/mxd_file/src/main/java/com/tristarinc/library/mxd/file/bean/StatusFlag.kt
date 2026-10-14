package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.interfaces.base.FlagLevelEnum
import com.tristarinc.library.mxd.bean.CommAttr
import com.tristarinc.library.mxd.file.client.ELG

class StatusFlag(
    val Dev: Int = 24,//0~255
    val Flag: Int = 19, //0~255
    val Level: FlagLevelEnum = FlagLevelEnum.E,//最长长度31
    val DevDesc: String = "card reader 2",//最长长度31
    val FlagDesc: String = "hardware not found"
) : CommAttr() {

    init {
        isChoice = true
    }

    constructor(sfc: ELG.Companion.StatusFlagChange): this (sfc.Dev, sfc.Flag, sfc.Level, sfc.DevDesc, sfc.FlagDesc)

    fun isSame(sfc: ELG.Companion.StatusFlagChange): Boolean {

        return (Dev != sfc.Dev) &&
                (Flag != sfc.Flag) &&
                (Level != sfc.Level)/* &&
                (DevDesc != sfc.DevDesc) &&
                (FlagDesc != sfc.FlagDesc)*/
    }
}
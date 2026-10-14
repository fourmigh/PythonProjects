package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class BatterySnapshot : CommAttr {

    init {
        isChoice = true
    }

    var BatteryVoltage = 0

    constructor(BatteryVoltage: Int = 1356) {
        this.BatteryVoltage = BatteryVoltage
    }
}
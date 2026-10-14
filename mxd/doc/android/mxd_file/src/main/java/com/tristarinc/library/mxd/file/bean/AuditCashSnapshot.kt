package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

open class AuditCashSnapshot : CommAttr {

    //0~4294967295
    var TotalInNativeCurrency = 0L//4294967295

    init {
        isChoice = true
    }

    constructor(TotalInNativeCurrency: Long = 6065) {
        this.TotalInNativeCurrency = TotalInNativeCurrency
    }
}
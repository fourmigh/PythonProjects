package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

open class AuditTicketStockSnapshot : CommAttr {

    //0~4294967295
    var TicketsRemaining = 0L//4294967295

    init {
        isChoice = true
    }

    constructor(TicketsRemaining: Long = 0) {
        this.TicketsRemaining = TicketsRemaining
    }
}
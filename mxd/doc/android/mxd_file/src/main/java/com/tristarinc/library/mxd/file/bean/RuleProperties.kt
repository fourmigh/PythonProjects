package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class RuleProperties : CommAttr() {

    init {
        isArray = true
    }

    var MinValue = 0
    var MaxValue = 0
    var MaxExpiryTime = 0
    var MaxValueAction = ""
    var MaxOverpayment = 0
    var MessageNumber = 0
    var TicketLayout = 0
    var AuditCode = ""
    var FormNumber = 0
}
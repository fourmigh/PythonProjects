package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class RuleSet : CommAttr() {

    init {
        isArray = true
    }

    var CalculationType = ""
    var FreeTimeOption = ""
    var ClosedTimeOption = ""
    var AllowOverpayment = false
    var StealRemainder = false
    var AllowFreeIssue = false
    var WalkTime = 0
    var StepFollowsTariff = false
    var DefaultStepValue = 0
    var LimitValueType = ""
    var TariffCodeType = ""
    var VATRate = 0
    var Description = ""
    val RuleProperties = ArrayList<RuleProperties>()
    val TariffCode = ArrayList<TariffCode>()
    val TariffRule = ArrayList<TariffRule>()
}
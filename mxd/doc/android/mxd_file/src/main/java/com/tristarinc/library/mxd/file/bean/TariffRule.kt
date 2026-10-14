package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class TariffRule : CommAttr() {

    init {
        isArray = true
    }

    var RuleType = ""
    var Priority = 0
    var StartHour = 0
    var StartMinute = 0
    var EndHour = 0
    var EndMinute = 0
    var DaysAvailable = 0
    var LimitType = ""
    var ValidAfter = 0
    var ValidUntil = 0
    var StopOnLimit = false
    var PropertiesIndex = 0
    var Cost = 0
    var TimeBought = 0
    var TimeBoughtType = ""
    var AddPeriod = 0
    var AddPeriodType = ""
    var AuditCode = ""
}
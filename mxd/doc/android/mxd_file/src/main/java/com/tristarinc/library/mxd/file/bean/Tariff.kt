package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class Tariff : CommAttr() {

    init {
        isArray = true
    }

    var Description = ""
    var StartDay = 0
    var StartMonth = 0
    var StartYear = 0
    var EndDay = 0
    var EndMonth = 0
    var EndYear = 0
    val RuleSet = ArrayList<RuleSet>()
}
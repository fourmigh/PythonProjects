package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class TariffCode : CommAttr() {

    init {
        isArray = true
    }

    var Value = 0
    var AuditCode = ""
}
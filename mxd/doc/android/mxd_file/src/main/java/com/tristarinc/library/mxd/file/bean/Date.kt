package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class Date : CommAttr() {

    init {
        isArray = true
    }

    var Day = 0
    var Month = 0
    var Year = 0
}
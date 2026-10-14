package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class CategoryMap : CommAttr() {

    init {
        isArray = true
    }

    var Category = 0
    var RuleSet = 0
}
package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class MxdFile : CommAttr() {

    init {
        isArray = true
    }

    var Entry = Entry()
}
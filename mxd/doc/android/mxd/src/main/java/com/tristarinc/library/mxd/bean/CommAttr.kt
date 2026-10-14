package com.tristarinc.library.mxd.bean

open class CommAttr {

    var isArray = false
    var isChoice = false

    //如果>=0，说明有下一级Element数组，record数组中的序号
    var recNo = -1
}
package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

open class PsuAccumulatorSnapshot(var Accumulator1Voltage: Int, var Accumulator2Voltage: Int) : CommAttr() {

    init {
        isChoice = true
    }
}

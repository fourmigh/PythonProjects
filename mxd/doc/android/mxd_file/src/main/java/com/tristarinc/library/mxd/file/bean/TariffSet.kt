package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class TariffSet : CommAttr() {

    var Description = ""
    val CategoryMap = ArrayList<CategoryMap>()
    val Tariff = ArrayList<Tariff>()
}
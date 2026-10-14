package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr

class KeyEntry : CommAttr(), Cloneable {

    init {
        isArray = true
    }

    var Name = ""
    var KeyID = 0L

    public override fun clone(): KeyEntry {
        return KeyEntry().also {
            it.Name = Name
            it.KeyID = KeyID
        }
    }
}
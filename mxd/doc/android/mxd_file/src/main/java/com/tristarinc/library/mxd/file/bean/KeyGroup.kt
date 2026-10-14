package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr
import java.time.LocalDateTime

class KeyGroup : CommAttr() {

    companion object {
        const val TYPE_SERVICE = "SERVICE"
        const val TYPE_UPPER = "LOCK"
        const val TYPE_VAULT = "VAULT"
    }

    init {
        isArray = true
    }

    var Name = ""
    var Type = ""
    var KeyList = KeyList()
    var AccessTimeList = AccessTimeList()

    private fun clone(keyID: Long): KeyGroup {
        return KeyGroup().also {
            it.Name = Name
            it.Type = Type
            it.KeyList = KeyList.clone(keyID)
            it.AccessTimeList = AccessTimeList.clone()
        }
    }

    fun accessAllowed(dateTime: LocalDateTime): Boolean {
        return AccessTimeList.accessAllowed(dateTime)
    }

    fun findKeyEntry(keyID: Long): KeyGroup? {
        return KeyList.KeyEntry.firstOrNull { it.KeyID == keyID }?.let { clone(keyID) }
    }
}
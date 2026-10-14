package com.tristarinc.library.mxd.file.bean

class KeyList {
    val KeyEntry = ArrayList<KeyEntry>()

    fun clone(keyID: Long): KeyList {
        val keyList = KeyList()
        KeyEntry.firstOrNull { it.KeyID == keyID }?.let { keyList.KeyEntry.add(it.clone()) }
        return keyList
    }
}
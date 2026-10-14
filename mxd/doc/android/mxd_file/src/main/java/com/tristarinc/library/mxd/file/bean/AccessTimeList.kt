package com.tristarinc.library.mxd.file.bean

import java.time.LocalDateTime

class AccessTimeList : Cloneable {
    val AccessTime = ArrayList<AccessTime>()

    public override fun clone(): AccessTimeList {
        return AccessTimeList().also { atl ->
            atl.AccessTime.addAll(AccessTime.map { it.clone() })
        }
    }

    fun accessAllowed(dateTime: LocalDateTime): Boolean {
        return AccessTime.any { it.accessAllowed(dateTime) }
    }
}
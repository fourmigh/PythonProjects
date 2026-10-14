package com.tristarinc.library.mxd.file.bean

import java.time.LocalTime

class HourMinute: Cloneable {
    var Hour = -1
    var Minute = -1

    public override fun clone(): HourMinute {
        return HourMinute().also {
            it.Hour = Hour
            it.Minute = Minute
        }
    }

    fun getLocalTime() : LocalTime {
        return LocalTime.of(Hour, Minute)
    }
}
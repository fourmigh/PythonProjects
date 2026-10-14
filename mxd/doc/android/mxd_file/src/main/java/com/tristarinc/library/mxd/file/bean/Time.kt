package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr
import java.time.LocalTime

class Time : CommAttr(), Cloneable {

    init {
        isArray = true
    }

    var StartTime = HourMinute()
    var EndTime = HourMinute()

    public override fun clone(): Time {
        return Time().also {
            it.StartTime = StartTime.clone()
            it.EndTime = EndTime.clone()
        }
    }

    fun accessAllowed(time: LocalTime): Boolean {
        return time.isBetween(StartTime.getLocalTime(), EndTime.getLocalTime())
    }

    private fun LocalTime.isBetween(start: LocalTime, end: LocalTime): Boolean {
        // times may wrap midnight so end < start
        return if (end.isBefore(start)) {
            !this.isBefore(start) || this.isBefore(end)
        } else {
            !this.isBefore(start) && this.isBefore(end)
        }
    }
}
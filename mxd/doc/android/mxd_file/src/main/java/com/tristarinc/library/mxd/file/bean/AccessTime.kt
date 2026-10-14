package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr
import java.time.DayOfWeek
import java.time.LocalDateTime

class AccessTime : CommAttr(), Cloneable {

    enum class DayFlags(private val value: Int, private val day: DayOfWeek) {
        Sunday(0x001, DayOfWeek.SUNDAY),
        Monday(0x002, DayOfWeek.MONDAY),
        Tuesday(0x004, DayOfWeek.TUESDAY),
        Wednesday(0x008, DayOfWeek.WEDNESDAY),
        Thursday(0x010, DayOfWeek.THURSDAY),
        Friday(0x020, DayOfWeek.FRIDAY),
        Saturday(0x040, DayOfWeek.SATURDAY);

        companion object {
            fun getDays(value: Int) = entries.filter { it.value and value > 0 }.map { it.day }
        }
    }

    init {
        isArray = true
    }

    var DayOfWeekMask = -1
    val Time = ArrayList<Time>()

    public override fun clone(): AccessTime {
        return AccessTime().also { at ->
            at.DayOfWeekMask = DayOfWeekMask
            at.Time.addAll(Time.map { it.clone() })
        }
    }

    fun accessAllowed(dateTime: LocalDateTime): Boolean {
        if (!DayFlags.getDays(DayOfWeekMask).contains(dateTime.dayOfWeek)) {
            return false
        }

        // if no times specified, key is always allowed
        if (Time.isEmpty()) {
            return true
        }

        return Time.any { it.accessAllowed(dateTime.toLocalTime()) }
    }
}
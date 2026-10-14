package com.tristarinc.library.mxd.file.dkl.room

import androidx.room.TypeConverter
import com.tristarinc.library.gson.JsonUtils
import com.tristarinc.library.mlog.MLog
import com.tristarinc.library.mxd.file.server.DKL

class DKLConverter {

    @TypeConverter
    fun dklToString(dkl: DKL?): String {
        if (dkl == null) {
            return ""
        }
        return JsonUtils.toJson(dkl)
    }

    @TypeConverter
    fun stringToDKL(json: String?): DKL? {
        if (json.isNullOrEmpty()) {
            return null
        }

        val (dkl, err) = JsonUtils.fromJsonWithErrStr(json, DKL::class.java)

        if (dkl == null) {
            if (err == null) {
                MLog.e("DKLConverter", "read parse error")
            } else {
                MLog.e("DKLConverter", "read parse error: $err")
            }
        }

        return dkl
    }
}
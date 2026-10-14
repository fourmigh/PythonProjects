package com.tristarinc.library.mxd.file.dkl.room

import androidx.room.Entity
import androidx.room.TypeConverters
import com.tristarinc.library.mxd.file.server.DKL

@Entity(primaryKeys = ["fileName", "validFromTime", "initialCreationTime"])
@TypeConverters(DKLConverter::class)
class DKLData {

    var fileName = ""

    var validFromTime = 0

    var initialCreationTime = 0

    var fileLoadTime = 0L

    var dkl: DKL? = null
}

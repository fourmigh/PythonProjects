package com.tristarinc.library.mxd.file.bean

import com.tristarinc.library.mxd.bean.CommAttr
import com.tristarinc.library.mxd.file.enums.MxdContentTypeEnum

class Entry : CommAttr() {

    var FileSize = 0L//4294967295
    var FileCrc = 0L//4294967295
    var FileName = "-"
    var Customer = ""
    var CreationTime = 0L//4294967295
    var ContentType = MxdContentTypeEnum.SCHEMA_DATA
    var Version = ""
    var EncryptionType = 0//255
    var ValidFromTime = 0L//4294967295
    var CompatibilityLevel = 0//65535
    //VAR_INT64
    var CreationTz = 0//840
    //VAR_INT64
    var ValidFromTz = 0//840

    fun setFile(mxdFile: Entry) {
        this.FileSize = mxdFile.FileSize
        this.FileCrc = mxdFile.FileCrc
        this.FileName = mxdFile.FileName
        this.Customer = mxdFile.Customer
        this.CreationTime = mxdFile.CreationTime
        this.ContentType = mxdFile.ContentType
        this.Version = mxdFile.Version
        this.EncryptionType = mxdFile.EncryptionType
        this.ValidFromTime = mxdFile.ValidFromTime
        this.CompatibilityLevel = mxdFile.CompatibilityLevel
        this.CreationTz = mxdFile.CreationTz
        this.ValidFromTz = mxdFile.ValidFromTz
    }
}
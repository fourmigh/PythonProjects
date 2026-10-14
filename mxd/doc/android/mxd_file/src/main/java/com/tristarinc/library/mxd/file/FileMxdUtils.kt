package com.tristarinc.library.mxd.file

import com.tristarinc.library.crc.CustomerCRC32
import com.tristarinc.library.file.FileUtils
import com.tristarinc.library.mxd.file.bean.Entry
import com.tristarinc.library.mxd.file.bean.MxdFile
import java.io.File

object FileMxdUtils {

    fun file2MxdFile(file: File, crcVerify: Boolean = true): MxdFile? {

        val entry = file2Entry(file, crcVerify) ?: return null

        val mxdFile = MxdFile()
        mxdFile.Entry.setFile(entry)

        return mxdFile
    }

    fun file2Entry(file: File, crcVerify: Boolean = true): Entry? {
        val bytes = FileUtils.readBytes(file.absolutePath) ?: return null
        if (crcVerify){
            if (!CustomerCRC32.check(bytes)) {
                return null
            }
        }
        val entry = Entry()
        entry.FileSize = bytes.size.toLong()
        entry.FileCrc = CustomerCRC32.calc(bytes).toLong()
        entry.FileName = file.name
        entry.Customer = ""
        entry.CreationTime = file.lastModified() / 1000
        entry.Version = ""
        entry.EncryptionType = 0
        entry.ValidFromTime = 0
        entry.CompatibilityLevel = 0
        entry.CreationTz = 0
        entry.ValidFromTz = 0
        return entry
    }
}
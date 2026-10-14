package com.tristarinc.library.mxd.file.client

import com.tristarinc.library.mxd.bean.DataType
import com.tristarinc.library.mxd.bean.Element
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.file.FileMxdUtils
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.MxdFile
import java.io.File

class DIR(origin: String, machineUniqueID: Long) : MXD() {

    init {
        create(FileType.DIR, origin, machineUniqueID)
    }

    private val dirList = ArrayList<MxdFile>()

    private fun addFile(file: MxdFile) {
        dirList.add(file)
    }

    fun addFile(file: File, crcVerify: Boolean = true): Boolean {

        val mxdFile = FileMxdUtils.file2MxdFile(file, crcVerify) ?: return false
        addFile(mxdFile)

        buildSchema()

        return true
    }

    fun addFiles(files: Collection<File>, crcVerify: Boolean = true): Boolean {
        val mxdFiles = files.mapNotNull { FileMxdUtils.file2MxdFile(it, crcVerify) }

        dirList.addAll(mxdFiles)
        buildSchema()
        return true
    }

    private fun buildSchema() {

        if (dirList.isEmpty() || schema.isNotEmpty()) {
            return
        }

        //0x06,0x08,0x46,0x69,0x6c,0x65,0x53,0x69,0x7a,0x65,//FileSize
        //0x06,0x07,0x46,0x69,0x6c,0x65,0x43,0x72,0x63,//FileCrc
        //0x04,0x08,0x46,0x69,0x6c,0x65,0x4e,0x61,0x6d,0x65,//FileName
        //0x04,0x08,0x43,0x75,0x73,0x74,0x6f,0x6d,0x65,0x72,//Customer
        //0x06,0x0c,0x43,0x72,0x65,0x61,0x74,0x69,0x6f,0x6e,0x54,0x69,0x6d,0x65,//CreationTime
        //0x05,0x0b,0x43,0x6f,0x6e,0x74,0x65,0x6e,0x74,0x54,0x79,0x70,0x65,//ContentType
        //0x04,0x07,0x56,0x65,0x72,0x73,0x69,0x6f,0x6e,//Version
        //0x06,0x0e,0x45,0x6e,0x63,0x72,0x79,0x70,0x74,0x69,0x6f,0x6e,0x54,0x79,0x70,0x65,//EncryptionType
        //0x06,0x0d,0x56,0x61,0x6c,0x69,0x64,0x46,0x72,0x6f,0x6d,0x54,0x69,0x6d,0x65,//ValidFromTime
        //0x06,0x12,0x43,0x6f,0x6d,0x70,0x61,0x74,0x69,0x62,0x69,0x6c,0x69,0x74,0x79,0x4c,0x65,0x76,0x65,0x6c,//CompatibilityLevel
        //0x07,0x0a,0x43,0x72,0x65,0x61,0x74,0x69,0x6f,0x6e,0x54,0x7a,//CreationTz
        //0x07,0x0b,0x56,0x61,0x6c,0x69,0x64,0x46,0x72,0x6f,0x6d,0x54,0x7a,//ValidFromTz
        //0xf0,//MXDDT_END_RECORD, Rec 0
        //0x01,
        //0x00,0x05,0x45,0x6e,0x74,0x72,0x79,//Entry
        //0xf0,//MXDDT_END_RECORD, Rec 1
        //0xf2,//MXDDT_START_CHOICE
        //0x01,
        //0x01,0x04,0x46,0x69,0x6c,0x65,//File
        //0xf3,//MXDDT_END_CHOICE
        //0xf1,//MXDDT_END_SCHEMA

        //Rec 0
        var record = Element().apply {
            elements.addAll(
                arrayListOf(
                    Element(DataType.MXDDT_VAR_UINT64, "FileSize"),
                    Element(DataType.MXDDT_VAR_UINT64, "FileCrc"),
                    Element(DataType.MXDDT_UTF8_STRING, "FileName"),
                    Element(DataType.MXDDT_UTF8_STRING, "Customer"),
                    Element(DataType.MXDDT_VAR_UINT64, "CreationTime"),
                    Element(DataType.MXDDT_ENUM, "ContentType"),
                    Element(DataType.MXDDT_UTF8_STRING, "Version"),
                    Element(DataType.MXDDT_VAR_UINT64, "EncryptionType"),
                    Element(DataType.MXDDT_VAR_UINT64, "ValidFromTime"),
                    Element(DataType.MXDDT_VAR_UINT64, "CompatibilityLevel"),
                    Element(DataType.MXDDT_VAR_UINT64, "CreationTz"),
                    Element(DataType.MXDDT_VAR_UINT64, "ValidFromTz")
                )
            )
        }
        schema.add(record)

        //Rec 1
        record = Element()
        var element = Element(0, "Entry")
//        element.dataType = DataType.MXDDT_RECORD
//        element.recNo = 0
//        element.fieldName = "Entry"
        record.elements.add(element)
        schema.add(record)

        //Rec 2
        record = Element()
        record.isChoice = true

        element = Element(1, "File", false, true)
//        element.dataType = DataType.MXDDT_RECORD
//        element.isChoice = true
//        element.recNo = 1
//        element.fieldName = "File"
        record.elements.add(element)
        schema.add(record)
    }

    override fun writeData(bits: ArrayList<Byte>) {
        //0x01,
        //0xcc,0x29,
        //0x94,0xb5,0xdc,0x8c,0x02,
        //0x0c,0x36,0x33,0x46,0x44,0x46,0x41,0x45,0x35,0x2e,0x45,0x4c,0x47,//63FDFAE5.ELG
        //0x00,
        //0xe5,0xf5,0xf7,0x9f,0x06,
        //0x0b,0x53,0x43,0x48,0x45,0x4d,0x41,0x5f,0x44,0x41,0x54,0x41,//SCHEMA_DATA
        //0x00,
        //0x00,0x00,0x00,0x00,0x00,
        //0x01,
        //0xce,0x28,
        //0xdf,0xf7,0xdc,0xc3,0x0a,
        //0x0c,0x36,0x33,0x46,0x44,0x46,0x42,0x32,0x44,0x2e,0x45,0x4c,0x47,//63FDFB2D.ELG
        //0x00,
        //0xad,0xf6,0xf7,0x9f,0x06,
        //0x0b,0x53,0x43,0x48,0x45,0x4d,0x41,0x5f,0x44,0x41,0x54,0x41,//SCHEMA_DATA
        //0x00,
        //0x00,0x00,0x00,0x00,0x00,
        //0x00,
        for (file in dirList) {
            bits.add(1.toByte())
            bits.addAll(write7BitUint(file.Entry.FileSize))
            bits.addAll(write7BitUint(file.Entry.FileCrc))
            bits.addAll(writeString(file.Entry.FileName))
            bits.addAll(writeString(file.Entry.Customer))
            bits.addAll(write7BitUint(file.Entry.CreationTime))
            bits.addAll(writeString(file.Entry.ContentType.toString()))
            bits.addAll(writeString(file.Entry.Version))
            bits.addAll(write7BitUint(file.Entry.EncryptionType))
            bits.addAll(write7BitUint(file.Entry.ValidFromTime))
            bits.addAll(write7BitUint(file.Entry.CompatibilityLevel))
            bits.addAll(write7BitUint(file.Entry.CreationTz))
            bits.addAll(write7BitUint(file.Entry.ValidFromTz))
        }

        bits.add(0.toByte())
    }
}
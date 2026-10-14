package com.tristarinc.library.mxd.bean

import com.socks.library.KLog
import com.tristarinc.library.bit.ByteArrayUtils

class ReadData(private val bytes: ByteArray, private val records: List<Element>) {

    private var index = 0

    fun read(): List<Element> {

        val result = ArrayList<Element>()
        if (records.isEmpty()) {
            return result
        }
        val lastRecord = records[records.size - 1]
        val lastRecordElements = lastRecord.elements
        if (lastRecordElements.isEmpty()) {
            return result
        }

        index = 0
        while (true) {
            if (isOutOfArray(bytes)) {
                break
            }
            if (records.size == 1) {
                val record = records[0]
                //KLog.e("ReadData", "readElement: ${record.fieldName}")
                readElement(record)
                result.add(record)
                break
            } else {
                if (lastRecord.isChoice) {
                    val no = bytes[index].toInt()
                    index ++
                    if (no >= 0 && no <= lastRecordElements.size) {
                        val index = if (lastRecord.isChoice) (no - 1) else no
                        if (index < 0 || index >= lastRecordElements.size) {
                            break
                        }
                        val record = lastRecordElements[index]
                        //KLog.e("ReadData", "readElement: ${record.fieldName}")
                        readElement(record)
                        result.add(record)
                    } else {
                        break
                    }
                } else {
                    for (record in lastRecordElements) {
                        //KLog.e("ReadData", "readElement: ${record.fieldName}")
                        readElement(record)
                        result.add(record)
                    }
                    break
                }
            }
        }

        return result
    }

    private fun getRecordClone(index: Int): Element? {
        if (index >= 0 && index < records.size) {
            val record = records[index].clone()
//            getSubElements(record)
            return record
        }
        return null
    }
    private fun getSubElements(record: Element) {
        for (sub in record.elements) {
            val subrecord = getRecordClone(sub.recNo)
            if (subrecord != null && sub.elements.isEmpty()) {
                sub.elements.addAll(subrecord.elements)
                for (subsub in sub.elements) {
                    getSubElements(subsub)
                }
            }
        }
    }

    private fun readElement(record: Element) {
        if (isOutOfArray(bytes)) {
            return
        }
        when (record.dataType.ordinal) {
            DataType.MXDDT_BOOL.ordinal -> {
                record.data.bool = readBoolean()
                //KLog.d("ReadData", "MXDDT_BOOL: ${record.fieldName}, ${record.data.bool}")
            }
            DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
                record.data.bytes = readByteArray(true)
                //KLog.d("ReadData", "MXDDT_HEX_BYTE_ARRAY: ${record.fieldName}, ${record.data.bytes?.toMutableList()}")
            }
            DataType.MXDDT_UTF8_STRING.ordinal -> {
                record.data.utf8 = readString(true)
                //KLog.d("ReadData", "MXDDT_UTF8_STRING: ${record.fieldName}, ${record.data.utf8}")
            }
            DataType.MXDDT_ENUM.ordinal -> {
                record.data.enum = readString(true)
                //KLog.d("ReadData", "MXDDT_ENUM: ${record.fieldName}, ${record.data.enum}")
            }
            DataType.MXDDT_VAR_UINT64.ordinal -> {
                record.data.uint64 = read7BitUint()
                //KLog.d("ReadData", "MXDDT_VAR_UINT64: ${record.fieldName}, ${record.data.uint64}")
            }
            DataType.MXDDT_VAR_INT64.ordinal -> {
                record.data.int64 = read7BitInt()
                //KLog.d("ReadData", "MXDDT_VAR_INT64: ${record.fieldName}, ${record.data.int64}")
            }
            DataType.MXDDT_RECORD.ordinal -> {
                val subrecord = getRecordClone(record.recNo) ?: return
                //KLog.d("ReadData", "MXDDT_RECORD.subrecord: ${subrecord.fieldName}")
                //KLog.d("ReadData", "MXDDT_RECORD.record.isArray: ${record.isArray}")
                if (record.isArray) {
                    //KLog.d("ReadData", "index: $index")
                    val size = read7BitUint() ?: return
                    //KLog.d("ReadData", "MXDDT_RECORD.size: $size")
                    if (size > 0) {
                        for (i in 0 until size) {
                            val array = subrecord.clone()
                            //KLog.e("ReadData", "readElement: ${array.fieldName}")
                            readElement(array)
                            record.elements.add(array)
                        }
                    }
                } else {
                    for (element in subrecord.elements) {
                        //KLog.e("ReadData", "readElement: ($index / ${bytes.size})${element.fieldName}")
                        readElement(element)
                        record.elements.add(element)
                    }
                }
            }
            DataType.MXDDT_NULL.ordinal -> {
                //KLog.d("ReadData", "MXDDT_NULL")
                for (element in record.elements) {
                    //KLog.e("ReadData", "readElement: ${element.fieldName}")
                    readElement(element)
                }
            }
        }
    }

//    private fun readData(record: Element, isChoice: Boolean) {
//        if (records.size > 1) {
//            val subrecord = getRecordClone(record.recNo) ?: return
//            if (record.elements.isEmpty() && subrecord.elements.isNotEmpty()) {
//                for (e in subrecord.elements) {
//                    record.elements.add(e.clone())
//                }
//            }
//        }
//        KLog.e("ReadData", "readData: ${record.fieldName}")
//        for (i in 0 until record.elements.size) {
//            if (isOutOfArray(bytes)) {
//                return
//            }
//            val rec = record.elements[i]
//            KLog.d("ReadData", "byte.index: $index")
//            KLog.d("ReadData", "byte.hex: ${ByteHexUtils.byte2Hex(bytes[index])}")
//            when (rec.dataType.ordinal) {
//                DataType.MXDDT_BOOL.ordinal -> {
//                    rec.data.bool = readBoolean()
//                }
//                DataType.MXDDT_HEX_BYTE_ARRAY.ordinal -> {
//                    rec.data.bytes = readByteArray(true)
//                }
//                DataType.MXDDT_UTF8_STRING.ordinal -> {
//                    rec.data.utf8 = readString(true)
//                }
//                DataType.MXDDT_ENUM.ordinal -> {
//                    rec.data.enum = readString(true)
//                }
//                DataType.MXDDT_VAR_UINT64.ordinal -> {
//                    rec.data.uint64 = read7BitUint()
//                }
//                DataType.MXDDT_VAR_INT64.ordinal -> {
//                    rec.data.uint64 = read7BitInt()
//                }
//                DataType.MXDDT_RECORD.ordinal -> {
//
//                    readData(rec, isChoice)
//                    if (rec.isArray) {
//                        val size = readByte() ?: return
//                        if (size > 1) {
//                            for (j in 1 until size) {
//                                val array = rec.clone()
//                                array.isArray = false
//                                record.elements.add(i + 1, array)
//                            }
//                        }
//                    }
//                }
//                else -> {
//                    for (r in rec.elements) {
//                        readData(r, isChoice)
//                    }
//                }
//            }
//            KLog.d("ReadData", "key: ${rec.fieldName}")
//            KLog.json("ReadData", "value: ${JsonUtils.toJson(rec.data)}")
//        }
//    }

    private fun isOutOfArray(data: ByteArray?): Boolean {
        if (data == null) {
            return true
        }
        val result = index < 0 || index >= data.size
        return result
    }

    private fun readByteArray(is7BitEncodedUint64: Boolean = false): ByteArray? {
        if (isOutOfArray(bytes)) {
            return null
        }
        val length: Int
        if (is7BitEncodedUint64) {
            length = read7BitUint()?.toInt() ?: return null
        } else {
            length = bytes[index].toInt()
            index++
        }
        if (length <= 0) {
            return null
        }
        val bs = ByteArrayUtils.get(bytes, index, length)
        index += length
        return bs
    }

    private fun read7BitUint(): Long? {
        var value = 0L
        var data: UByte
        var i = 0
        do {
            data = readByte()?.toUByte() ?: return null
            value = value or ((data and 0x7F.toUByte()).toLong() shl i)
            i += 7;
        } while ((data and 0x80.toUByte()) > 0.toUByte())

        return value
    }

    private fun read7BitInt(): Long? {
        var value = 0L
        var data: UByte
        var i = 0
        do {
            data = readByte()?.toUByte() ?: return null
            value = value or ((data and 0x7F.toUByte()).toLong() shl i)
            i += 7;
        } while ((data and 0x80.toUByte()) > 0.toUByte())

        if (data and 0x40.toUByte() > 0.toUByte()) {
            value = value or (-1L shl i)
        }

        return value
    }

    private fun readByte(): Byte? {
        if (isOutOfArray(bytes)) {
            return null
        }
        val byte = bytes[index]
        index ++
        return byte
    }

    private fun readBoolean(): Boolean {
        if (isOutOfArray(bytes)) {
            return false
        }
        val bool = bytes[index] == 1.toByte()
        index ++
        return bool
    }

    private fun readString(is7BitEncodedUint64: Boolean = false): String {
        val byteArray = readByteArray(is7BitEncodedUint64)
        if (byteArray != null) {
            return try {
                String(byteArray)
            } catch (e: Exception) {
                ""
            }
        }
        return ""
    }
}
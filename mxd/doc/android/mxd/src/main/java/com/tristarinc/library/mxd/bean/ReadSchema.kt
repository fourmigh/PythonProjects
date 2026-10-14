package com.tristarinc.library.mxd.bean

/**
 * 解析二进制文件Schema时的临时数据类
 */
class ReadSchema {
    val elements = ArrayList<Element>()
    val records = ArrayList<Element>()

    private var isChoice = false

    fun add(element: Element) {
        element.isChoice = isChoice
        elements.add(element)
    }

    fun endRecord() {

        if (elements.isEmpty()) {
            return
        }
        val record = Element()
        record.isChoice = isChoice
        record.elements.addAll(elements)
        records.add(record)
        isChoice = false

        elements.clear()
    }

    fun endChoice() {
        endRecord()
    }

    fun startChoice() {
        isChoice = true
    }

    fun endSchema(): List<Element> {

        return records
    }
}
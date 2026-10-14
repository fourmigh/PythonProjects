package com.tristarinc.library.mxd.file.client

import com.socks.library.KLog
import com.tristarinc.library.gson.JsonUtils
import com.tristarinc.library.mlog.MLog
import com.tristarinc.library.mxd.bean.DataType
import com.tristarinc.library.mxd.bean.Element
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.bean.MXDFile
import com.tristarinc.library.mxd.file.MXD
import com.tristarinc.library.mxd.file.bean.*
import kotlin.math.roundToInt

class STF(origin: String, machineUniqueID: Long) : MXD() {

    init {
        create(FileType.STF, origin, machineUniqueID)
    }

//    var StatusFlag: StatusFlag? = null
    private val StatusFlags = ArrayList<StatusFlag>()
    private var CoinSnapshot: AuditCashSnapshot? = null
    private var NoteSnapshot: AuditCashSnapshot? = null
    private var BatterySnapshot: BatterySnapshot? = null
    private var LeftPrinterTicketStock: AuditTicketStockSnapshot? = null
    private var RightPrinterTicketStock: AuditTicketStockSnapshot? = null
    private var AccumulatorSnapshot: PsuAccumulatorSnapshot? = null

    fun new(origin: String = header.origin, machineUniqueID: Long = header.machineUniqueID) {
        super.create(FileType.STF, origin, machineUniqueID)
    }

    override fun create(fileType: FileType, origin: String, machineUniqueID: Long): MXDFile {
        super.create(fileType, origin, machineUniqueID)
        //Rec 0:BatterySnapshot
        var record = Element()
        var element = Element()
        element.dataType = DataType.MXDDT_VAR_UINT64
        element.fieldName = "BatteryVoltage"
        record.elements.add(element)
        schema.add(record)

        //Rec 1:AuditTicketStockSnapshot
        record = Element()
        element = Element()
        element.dataType = DataType.MXDDT_VAR_UINT64
        element.fieldName = "TicketsRemaining"
        record.elements.add(element)
        schema.add(record)

        //Rec 2:AuditCashSnapshot
        record = Element()
        element = Element()
        element.dataType = DataType.MXDDT_VAR_UINT64
        element.fieldName = "TotalInNativeCurrency"
        record.elements.add(element)
        schema.add(record)

        //Rec 3:StatusFlag
        record = Element()

        element = Element()
        element.dataType = DataType.MXDDT_VAR_UINT64
        element.fieldName = "Dev"
        record.elements.add(element)

        element = Element()
        element.dataType = DataType.MXDDT_VAR_UINT64
        element.fieldName = "Flag"
        record.elements.add(element)

        element = Element()
        element.dataType = DataType.MXDDT_ENUM
        element.fieldName = "Level"
        record.elements.add(element)

        element = Element()
        element.dataType = DataType.MXDDT_UTF8_STRING
        element.fieldName = "DevDesc"
        record.elements.add(element)

        element = Element()
        element.dataType = DataType.MXDDT_UTF8_STRING
        element.fieldName = "FlagDesc"
        record.elements.add(element)

        schema.add(record)

        //Rec 4:PsuAccumulatorSnapshot
        record = Element()
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Accumulator1Voltage"))
        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Accumulator2Voltage"))
        schema.add(record)

        //Rec 5
        record = Element()
        record.isChoice = true

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "StatusFlag"
        element.recNo = 3
        record.elements.add(element)

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "CoinSnapshot"
        element.recNo = 2
        record.elements.add(element)

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "NoteSnapshot"
        element.recNo = 2
        record.elements.add(element)

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "LeftPrinterTicketStock"
        element.recNo = 1
        record.elements.add(element)

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "RightPrinterTicketStock"
        element.recNo = 1
        record.elements.add(element)

        element = Element()
        element.isChoice = true
        element.dataType = DataType.MXDDT_RECORD
        element.fieldName = "BatterySnapshot"
        element.recNo = 0
        record.elements.add(element)

        element = Element(4, "AccumulatorSnapshot", false, true)
        record.elements.add(element)

        schema.add(record)

        //0x06,0x0e,0x42,0x61,0x74,0x74,0x65,0x72,0x79,0x56,0x6f,0x6c,0x74,0x61,0x67,0x65,//BatteryVoltage
        //0xf0,//Rec 0
        //0x06,0x10,0x54,0x69,0x63,0x6b,0x65,0x74,0x73,0x52,0x65,0x6d,0x61,0x69,0x6e,0x69,0x6e,0x67,//TicketsRemaining
        //0xf0,//Rec 1
        //0x06,0x15,0x54,0x6f,0x74,0x61,0x6c,0x49,0x6e,0x4e,0x61,0x74,0x69,0x76,0x65,0x43,0x75,0x72,0x72,0x65,0x6e,0x63,0x79,//TotalInNativeCurrency
        //0xf0,//Rec 2
        //0x06,0x03,0x44,0x65,0x76,//Dev
        //0x06,0x04,0x46,0x6c,0x61,0x67,//Flag
        //0x05,0x05,0x4c,0x65,0x76,0x65,0x6c,//Level
        //0x04,0x07,0x44,0x65,0x76,0x44,0x65,0x73,0x63,//DevDesc
        //0x04,0x08,0x46,0x6c,0x61,0x67,0x44,0x65,0x73,0x63,//FlagDesc
        //0xf0,//MXDDT_END_RECORD,//Rec 3
        //0xf2,//MXDDT_START_CHOICE
        //0x01,
        //0x03,0x0a,0x53,0x74,0x61,0x74,0x75,0x73,0x46,0x6c,0x61,0x67,//StatusFlag,Rec 3
        //0x01,
        //0x02,0x0c,0x43,0x6f,0x69,0x6e,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//CoinSnapshot,Rec 2
        //0x01,
        //0x02,0x0c,0x4e,0x6f,0x74,0x65,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//NoteSnapshot,Rec 2
        //0x01,
        //0x01,0x16,0x4c,0x65,0x66,0x74,0x50,0x72,0x69,0x6e,0x74,0x65,0x72,0x54,0x69,0x63,0x6b,0x65,0x74,0x53,0x74,0x6f,0x63,0x6b,//LeftPrinterTicketStock,Rec 1
        //0x01,
        //0x01,0x17,0x52,0x69,0x67,0x68,0x74,0x50,0x72,0x69,0x6e,0x74,0x65,0x72,0x54,0x69,0x63,0x6b,0x65,0x74,0x53,0x74,0x6f,0x63,0x6b,//RightPrinterTicketStock,Rec 1
        //0x01,
        //0x00,0x0f,0x42,0x61,0x74,0x74,0x65,0x72,0x79,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//BatterySnapshot,Rec 0
        //0xf3,//MXDDT_END_CHOICE,//Rec 4
        //0xf1,//MXDDT_END_SCHEMA

        //0x01,//StatusFlag
        //0x18,//Dev
        //0x13,//Flag
        //0x01,0x45,//Level
        //0x0d,0x63,0x61,0x72,0x64,0x00,0x72,0x65,0x61,0x64,0x65,0x72,0x00,0x32,//DevDesc
        //0x12,0x68,0x61,0x72,0x64,0x77,0x61,0x72,0x65,0x00,0x6e,0x6f,0x74,0x00,0x66,0x6f,0x75,0x6e,0x64,//FlagDesc
        //0x02,//CoinSnapshot
        //0xb1,0x2f,//TotalInNativeCurrency
        //0x06,//BatterySnapshot
        //0xcc,0x0a,//BatteryVoltage
        //0x04,//LeftPrinterTicketStock
        //0x00,//TicketsRemaining
        //0x00,
        return this
    }

//    fun setSchemaData(StatusFlag: StatusFlag?,
//                      CoinSnapshot: AuditCashSnapshot?,
//                      NoteSnapshot: AuditCashSnapshot?,
//                      BatterySnapshot: BatterySnapshot?,
//                      LeftPrinterTicketStock: AuditTicketStockSnapshot?,
//                      RightPrinterTicketStock: AuditTicketStockSnapshot?,
//                      AccumulatorSnapshot: PsuAccumulatorSnapshot?): STF {
//
//        this.StatusFlag = StatusFlag
//        this.CoinSnapshot = CoinSnapshot
//        this.NoteSnapshot = NoteSnapshot
//        this.BatterySnapshot =  BatterySnapshot
//        this.LeftPrinterTicketStock = LeftPrinterTicketStock
//        this.RightPrinterTicketStock = RightPrinterTicketStock
//        this.AccumulatorSnapshot = AccumulatorSnapshot
//
//        //Rec 0:BatterySnapshot
//        var record = Element()
//        var element = Element()
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "BatteryVoltage"
//        record.elements.add(element)
//        schema.add(record)
//
//        //Rec 1:AuditTicketStockSnapshot
//        record = Element()
//        element = Element()
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "TicketsRemaining"
//        record.elements.add(element)
//        schema.add(record)
//
//        //Rec 2:AuditCashSnapshot
//        record = Element()
//        element = Element()
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "TotalInNativeCurrency"
//        record.elements.add(element)
//        schema.add(record)
//
//        //Rec 3:StatusFlag
//        record = Element()
//
//        element = Element()
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "Dev"
//        record.elements.add(element)
//
//        element = Element()
//        element.dataType = DataType.MXDDT_VAR_UINT64
//        element.fieldName = "Flag"
//        record.elements.add(element)
//
//        element = Element()
//        element.dataType = DataType.MXDDT_ENUM
//        element.fieldName = "Level"
//        record.elements.add(element)
//
//        element = Element()
//        element.dataType = DataType.MXDDT_UTF8_STRING
//        element.fieldName = "DevDesc"
//        record.elements.add(element)
//
//        element = Element()
//        element.dataType = DataType.MXDDT_UTF8_STRING
//        element.fieldName = "FlagDesc"
//        record.elements.add(element)
//
//        schema.add(record)
//
//        //Rec 4:PsuAccumulatorSnapshot
//        record = Element()
//        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Accumulator1Voltage"))
//        record.elements.add(Element(DataType.MXDDT_VAR_UINT64, "Accumulator2Voltage"))
//        schema.add(record)
//
//        //Rec 5
//        record = Element()
//        record.isChoice = true
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "StatusFlag"
//        element.recNo = 3
//        record.elements.add(element)
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "CoinSnapshot"
//        element.recNo = 2
//        record.elements.add(element)
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "NoteSnapshot"
//        element.recNo = 2
//        record.elements.add(element)
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "LeftPrinterTicketStock"
//        element.recNo = 1
//        record.elements.add(element)
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "RightPrinterTicketStock"
//        element.recNo = 1
//        record.elements.add(element)
//
//        element = Element()
//        element.isChoice = true
//        element.dataType = DataType.MXDDT_RECORD
//        element.fieldName = "BatterySnapshot"
//        element.recNo = 0
//        record.elements.add(element)
//
//        element = Element(4, "AccumulatorSnapshot", false, true)
//        record.elements.add(element)
//
//        schema.add(record)
//
//        //0x06,0x0e,0x42,0x61,0x74,0x74,0x65,0x72,0x79,0x56,0x6f,0x6c,0x74,0x61,0x67,0x65,//BatteryVoltage
//        //0xf0,//Rec 0
//        //0x06,0x10,0x54,0x69,0x63,0x6b,0x65,0x74,0x73,0x52,0x65,0x6d,0x61,0x69,0x6e,0x69,0x6e,0x67,//TicketsRemaining
//        //0xf0,//Rec 1
//        //0x06,0x15,0x54,0x6f,0x74,0x61,0x6c,0x49,0x6e,0x4e,0x61,0x74,0x69,0x76,0x65,0x43,0x75,0x72,0x72,0x65,0x6e,0x63,0x79,//TotalInNativeCurrency
//        //0xf0,//Rec 2
//        //0x06,0x03,0x44,0x65,0x76,//Dev
//        //0x06,0x04,0x46,0x6c,0x61,0x67,//Flag
//        //0x05,0x05,0x4c,0x65,0x76,0x65,0x6c,//Level
//        //0x04,0x07,0x44,0x65,0x76,0x44,0x65,0x73,0x63,//DevDesc
//        //0x04,0x08,0x46,0x6c,0x61,0x67,0x44,0x65,0x73,0x63,//FlagDesc
//        //0xf0,//MXDDT_END_RECORD,//Rec 3
//        //0xf2,//MXDDT_START_CHOICE
//        //0x01,
//        //0x03,0x0a,0x53,0x74,0x61,0x74,0x75,0x73,0x46,0x6c,0x61,0x67,//StatusFlag,Rec 3
//        //0x01,
//        //0x02,0x0c,0x43,0x6f,0x69,0x6e,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//CoinSnapshot,Rec 2
//        //0x01,
//        //0x02,0x0c,0x4e,0x6f,0x74,0x65,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//NoteSnapshot,Rec 2
//        //0x01,
//        //0x01,0x16,0x4c,0x65,0x66,0x74,0x50,0x72,0x69,0x6e,0x74,0x65,0x72,0x54,0x69,0x63,0x6b,0x65,0x74,0x53,0x74,0x6f,0x63,0x6b,//LeftPrinterTicketStock,Rec 1
//        //0x01,
//        //0x01,0x17,0x52,0x69,0x67,0x68,0x74,0x50,0x72,0x69,0x6e,0x74,0x65,0x72,0x54,0x69,0x63,0x6b,0x65,0x74,0x53,0x74,0x6f,0x63,0x6b,//RightPrinterTicketStock,Rec 1
//        //0x01,
//        //0x00,0x0f,0x42,0x61,0x74,0x74,0x65,0x72,0x79,0x53,0x6e,0x61,0x70,0x73,0x68,0x6f,0x74,//BatterySnapshot,Rec 0
//        //0xf3,//MXDDT_END_CHOICE,//Rec 4
//        //0xf1,//MXDDT_END_SCHEMA
//
//        //0x01,//StatusFlag
//        //0x18,//Dev
//        //0x13,//Flag
//        //0x01,0x45,//Level
//        //0x0d,0x63,0x61,0x72,0x64,0x00,0x72,0x65,0x61,0x64,0x65,0x72,0x00,0x32,//DevDesc
//        //0x12,0x68,0x61,0x72,0x64,0x77,0x61,0x72,0x65,0x00,0x6e,0x6f,0x74,0x00,0x66,0x6f,0x75,0x6e,0x64,//FlagDesc
//        //0x02,//CoinSnapshot
//        //0xb1,0x2f,//TotalInNativeCurrency
//        //0x06,//BatterySnapshot
//        //0xcc,0x0a,//BatteryVoltage
//        //0x04,//LeftPrinterTicketStock
//        //0x00,//TicketsRemaining
//        //0x00,
//        return this
//    }

    override fun writeData(bits: ArrayList<Byte>) {
        synchronized(STF::class.java) {
            try {
                if (StatusFlags.isNotEmpty()) {
                    val index = findIndex("StatusFlag")
                    if (index < 0) {
                        return
                    }
                    for (statusFlag in StatusFlags) {
                        bits.addAll(write7BitUint(index))
                        bits.addAll(write7BitUint(statusFlag.Dev))
                        bits.addAll(write7BitUint(statusFlag.Flag))
                        bits.addAll(writeEnum(statusFlag.Level))
                        bits.addAll(writeString(statusFlag.DevDesc))
                        bits.addAll(writeString(statusFlag.FlagDesc))
                        // TODO Print to the log level depending on the level of the flag
                        MLog.i("STF", "writeData: ${statusFlag.Level} - ${statusFlag.DevDesc} - ${statusFlag.FlagDesc}")
                    }
                    MLog.d("STF-synchronized", "writeData: $index")
                }
            } catch (_: Exception) {
            }
        }

        if (CoinSnapshot != null) {
            val index = findIndex("CoinSnapshot")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(CoinSnapshot!!.TotalInNativeCurrency))
        }

        if (NoteSnapshot != null) {
            val index = findIndex("NoteSnapshot")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(NoteSnapshot!!.TotalInNativeCurrency))
        }

        if (LeftPrinterTicketStock != null) {
            val index = findIndex("LeftPrinterTicketStock")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(LeftPrinterTicketStock!!.TicketsRemaining))
        }

        if (RightPrinterTicketStock != null) {
            val index = findIndex("RightPrinterTicketStock")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(RightPrinterTicketStock!!.TicketsRemaining))
        }

        if (AccumulatorSnapshot != null) {
            val index = findIndex("AccumulatorSnapshot")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(AccumulatorSnapshot!!.Accumulator1Voltage))
            bits.addAll(write7BitUint(AccumulatorSnapshot!!.Accumulator2Voltage))
        }

        if (BatterySnapshot != null) {
            val index = findIndex("BatterySnapshot")
            if (index < 0) {
                return
            }
            bits.addAll(write7BitUint(index))
            bits.addAll(write7BitUint(BatterySnapshot!!.BatteryVoltage))
        }

        bits.add(0.toByte())
    }

    fun setCoinSnapshot(totalInNativeCurrency: Long? = null) {
        new()
        if (totalInNativeCurrency == null) {
            CoinSnapshot = null
        } else {
            CoinSnapshot = AuditCashSnapshot()
            CoinSnapshot?.TotalInNativeCurrency = totalInNativeCurrency
        }
    }
    fun getCoinSnapshot(): AuditCashSnapshot? {
        return CoinSnapshot
    }
    fun setNoteSnapshot(totalInNativeCurrency: Long? = null) {
        new()
        if (totalInNativeCurrency == null) {
            NoteSnapshot = null
        } else {
            NoteSnapshot = AuditCashSnapshot()
            NoteSnapshot?.TotalInNativeCurrency = totalInNativeCurrency
        }
    }
    fun getNoteSnapshot(): AuditCashSnapshot? {
        return NoteSnapshot
    }
//    fun setBatterySnapshot(BatteryVoltage: Int? = null) {
//        new()
//        if (BatteryVoltage == null) {
//            BatterySnapshot = null
//        } else {
//            BatterySnapshot = BatterySnapshot()
//            BatterySnapshot?.BatteryVoltage = BatteryVoltage
//        }
//    }
//    fun getBatterySnapshot(): BatterySnapshot? {
//        return BatterySnapshot
//    }
    fun setLeftPrinterTicketStock(ticketsRemaining: Long? = null) {
        new()
        if (ticketsRemaining == null) {
            LeftPrinterTicketStock = null
        } else {
            LeftPrinterTicketStock = AuditTicketStockSnapshot()
            LeftPrinterTicketStock?.TicketsRemaining = ticketsRemaining
        }
    }
    fun getLeftPrinterTicketStock(): AuditTicketStockSnapshot? {
        return LeftPrinterTicketStock
    }
    fun setRightPrinterTicketStock(ticketsRemaining: Long? = null) {
        new()
        if (ticketsRemaining == null) {
            RightPrinterTicketStock = null
        } else {
            RightPrinterTicketStock = AuditTicketStockSnapshot()
            RightPrinterTicketStock?.TicketsRemaining = ticketsRemaining
        }
    }
    fun getRightPrinterTicketStock(): AuditTicketStockSnapshot? {
        return RightPrinterTicketStock
    }
    fun setAccumulatorSnapshot(accumulator1VoltageMv: Int? = null, accumulator2VoltageMv: Int? = null) {
        new()
        AccumulatorSnapshot = if (accumulator1VoltageMv == null || accumulator2VoltageMv == null) {
            null
        } else {
            PsuAccumulatorSnapshot((accumulator1VoltageMv / 10.0f).roundToInt(), (accumulator2VoltageMv / 10.0f).roundToInt())
        }
    }
    fun getAccumulatorSnapshot(): PsuAccumulatorSnapshot? {
        return AccumulatorSnapshot
    }

    private var lastModifyTime = 0L
    private var isModified = false

    fun addStatusFlag(sfc: ELG.Companion.StatusFlagChange, ignoreModify: Boolean = false) {
        new()
        val i = find(sfc)
        if (i < 0) {
            val sf = StatusFlag(sfc)
            MLog.d("STFManager", "addStatusFlag: $i, ${sfc.Dev}, ${sfc.Flag}")
            synchronized(STF::class.java) {
                StatusFlags.add(sf)
                KLog.d("STF-synchronized", "addStatusFlag: ${JsonUtils.toJson(sf)}")
            }
            if (!ignoreModify) {
                modify("addStatusFlag")
            }
        }
    }

    fun addStatusFlags(list: Iterable<ELG.Companion.StatusFlagChange>, ignoreModify: Boolean = false){
        new()
        synchronized(STF::class.java) {
            val newFlags = list.filter { sfc -> StatusFlags.none { sf -> sf.isSame(sfc) } }.map { StatusFlag(it) }
            if (newFlags.isNotEmpty()) {
                newFlags.forEach { sfc -> MLog.d("STFManager", "addStatusFlag: ${sfc.Dev}, ${sfc.Flag}") }
                StatusFlags.addAll(newFlags)
                if (!ignoreModify) {
                    modify("addStatusFlag")
                }
            }
        }
    }

    fun removeStatusFlag(sfc: ELG.Companion.StatusFlagChange, ignoreModify: Boolean = false) {
        new()
        val i = find(sfc)
        if (i >= 0) {
            MLog.d("STFManager", "removeStatusFlag: $i, ${StatusFlags[i].Dev}, ${StatusFlags[i].Flag}")
            synchronized(STF::class.java) {
                try {
                    StatusFlags.removeAt(i)
                } catch (_: Exception) {
                }
                KLog.e("STF-synchronized", "removeStatusFlag: $i")
            }
            if (!ignoreModify) {
                modify("removeStatusFlag")
            }
        }
    }
    fun removeStatusFlags(deviceID: Int) {
        synchronized(STF::class.java) {
            try {
                for (i in StatusFlags.size - 1 downTo 0) {
                    val sf = StatusFlags[i]
                    if (sf.Dev == deviceID) {
                        StatusFlags.removeAt(i)
                        modify("removeStatusFlags")
                        MLog.d("STFManager", "removeStatusFlags: $deviceID")
                    }
                }
            } catch (_: Exception) {
            }
        }
    }
    fun find(sfc: ELG.Companion.StatusFlagChange): Int {
        synchronized(STF::class.java) {
            try {
                for (i in StatusFlags.indices) {
                    val statusFlag = StatusFlags[i]
                    if (statusFlag.isSame(sfc)) {
                        KLog.d("STF-synchronized", "find: $i")
                        return i
                    }
                }
            } catch (_: Exception) {
            }
            KLog.d("STF-synchronized", "find: not found")
            return -1
        }
    }

    fun isChanged(reset: Boolean): Boolean {
        return isContentModify(reset) && isContentChanged()
    }

    fun isContentModify(reset: Boolean) : Boolean{
        if (!canSendToServer) {
            return false
        }
        KLog.d("STFManager", "lastModifyTime: $lastModifyTime, isModified: $isModified, space: ${System.currentTimeMillis() - lastModifyTime}")
        val result = lastModifyTime > 0 && isModified && System.currentTimeMillis() - lastModifyTime >= 2000
        if (result) {
            KLog.d("STFManager", "before lastModifyTime: $lastModifyTime")
            KLog.i("STFManager", "before isModified: $isModified")
            if(reset) {
                modify("isChanged", true)
            }
        }
        KLog.d("STFManager", "isContentModify: $result")
        return result
    }


    private var lastContent: String? = null
    fun isContentChanged(): Boolean{

        val flags = StatusFlags.sortedWith(compareBy({it.Dev}, {it.Flag}))

        val changed = lastContent != JsonUtils.toJson(flags)
        if (changed){
            MLog.d("STFManager-Change", "isConentChanged: $flags, ${JsonUtils.toJson(flags)}")
            MLog.d("STFManager-Change", "lastContent: $lastContent")
        }
        return changed
    }

    fun getLastStatusJson() : String{
        val flags = StatusFlags.sortedWith(compareBy({it.Dev}, {it.Flag}))
        return JsonUtils.toJson(flags)
    }
    fun saveLastContent(){
        lastContent = getLastStatusJson()
        MLog.d("STFManager-Change", "saveLastContent: $lastContent")
    }

    fun addStatusFlags(list: Iterable<StatusFlag>){
        StatusFlags.addAll(list)
    }

    fun getStatusFlags(): List<StatusFlag> {
        return StatusFlags
    }

    fun modify(log: String, clear: Boolean = false) {
        if (clear) {
            isModified = false
            lastModifyTime = 0
        } else {
            isModified = true
            lastModifyTime = System.currentTimeMillis()
        }
        MLog.d("STFManager", "modify --- log: $log, clear: $clear")
        KLog.d("STFManager", "[$log]lastModifyTime: $lastModifyTime")
        KLog.i("STFManager", "[$log]isModified: $isModified")
    }

    ////////////////////////////////////////////////////////////////////////////////////////////////
    //新西兰新需求：增加一个标志位，系统启动后才可以开始向后台发送
    private var canSendToServer = false
    fun setCanSendToServer(canSendToServer: Boolean) {
        this.canSendToServer = canSendToServer
    }

    fun copySTF(): STF{
        val stf = STF(header.origin, header.machineUniqueID)
        stf.addStatusFlags(StatusFlags)
        return stf
    }
    fun containsFlag(dev: Int, flag: Int): Boolean{
        StatusFlags.forEach {
            if (it.Dev == dev && it.Flag == flag){
                return true
            }
        }
        return false
    }
}

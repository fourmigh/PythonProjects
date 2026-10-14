package com.tristarinc.library.mxd.file

import android.os.Environment
import com.tristarinc.library.converter.LongHexUtils
import com.tristarinc.library.file.FileUtils
import com.tristarinc.library.mxd.MXDError
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.bean.MXDFile
import com.tristarinc.library.mxd.file.client.*
import com.tristarinc.library.mxd.file.enums.BackOfficeRespEnum
import com.tristarinc.library.mxd.file.server.BOC
import com.tristarinc.library.mxd.file.server.DKL
import com.tristarinc.library.mxd.file.server.TRF
import java.io.File

object MXDManager {

    fun writeFile(fileType: FileType, bytes: ByteArray?, folderName: String? = null): String? {
        if (bytes?.isEmpty() != false) {
            return null
        }
        when (fileType.ordinal) {
            FileType.BOR.ordinal, FileType.STF.ordinal, FileType.DIR.ordinal, FileType.ELG.ordinal, FileType.SIN.ordinal -> {
                val time = System.currentTimeMillis() / 1000
                val hex = LongHexUtils.long2Hex(time).uppercase()
                val fileName = "$hex.${fileType}"
                val folder = folderName ?: "MXD"
                val file = FileUtils.getSaveFile(Environment.DIRECTORY_DOCUMENTS, folder, fileName)
                if (FileUtils.write(bytes, file.absolutePath)) {
                    return file.absolutePath
                }
            }
            else -> {}
        }
        return null
    }

    fun createBOR(origin: String, machineUniqueID: Long, serialNo: Long, response: BackOfficeRespEnum): Pair<File, BOR>? {
        val bor = BOR(origin, machineUniqueID)
        bor.setSchemaData(serialNo, response)
        val bytes = bor.build() ?: return null
        val path = writeFile(FileType.BOR, bytes) ?: return null
        return Pair(File(path), bor)
    }

//    fun createSTF(origin: String, machineUniqueID: Long,
//                  stc: ELG.Companion.StatusFlagChange?,
//                  CoinSnapshot: AuditCashSnapshot?,
//                  NoteSnapshot: AuditCashSnapshot?,
//                  BatterySnapshot: BatterySnapshot?,
//                  LeftPrinterTicketStock: AuditTicketStockSnapshot?,
//                  RightPrinterTicketStock: AuditTicketStockSnapshot?,
//                  AccumulatorSnapshot: PsuAccumulatorSnapshot?): File? {
//        val stf = STF(origin, machineUniqueID)
////        stf.setSchemaData(StatusFlag, CoinSnapshot, NoteSnapshot, BatterySnapshot, LeftPrinterTicketStock, RightPrinterTicketStock, AccumulatorSnapshot)
//        if (stc != null) {
//            stf.addStatusFlag(stc)
//        }
//        stf.setCoinSnapshot(CoinSnapshot?.TotalInNativeCurrency)
//        stf.setNoteSnapshot(NoteSnapshot?.TotalInNativeCurrency)
//        stf.setBatterySnapshot(BatterySnapshot?.BatteryVoltage)
//        stf.setLeftPrinterTicketStock(LeftPrinterTicketStock?.TicketsRemaining)
//        stf.setRightPrinterTicketStock(RightPrinterTicketStock?.TicketsRemaining)
//        stf.setAccumulatorSnapshot(AccumulatorSnapshot?.Accumulator1Voltage, AccumulatorSnapshot?.Accumulator2Voltage)
//        val bytes = stf.build() ?: return null
//        val path = writeFile(FileType.STF, bytes) ?: return null
//        return File(path)
//    }

    fun createDIR(origin: String, machineUniqueID: Long, folderPath: String, crcVerify: Boolean = true): File? {
        return createDIR(origin, machineUniqueID, File(folderPath), crcVerify)
    }
    fun createDIR(origin: String, machineUniqueID: Long, folder: File, crcVerify: Boolean = true, ignoreFileName: String? = null, subfix: String? = null): File? {
        if (!folder.exists() || !folder.isDirectory) {
            return null
        }

        val dir = DIR(origin, machineUniqueID)

        var files = folder.listFiles()?.asList()
        if (!files.isNullOrEmpty()) {
            if (ignoreFileName != null) {
                files = files.filter { it.name != ignoreFileName }
            }
            if (subfix != null){
                files = files.filter { it.name.endsWith(subfix) }
            }
            dir.addFiles(files.filter { it.isFile }, crcVerify)
        }
        val bytes = dir.build() ?: return null
        val path = writeFile(FileType.DIR, bytes) ?: return null
        return File(path)
    }
    fun createDIR(origin: String, machineUniqueID: Long, files: Collection<File>, crcVerify: Boolean = true): File? {

        val dir = DIR(origin, machineUniqueID)
        if (files.isNotEmpty()) {
            dir.addFiles(files.filter { it.isFile }, crcVerify)
        }
        val bytes = dir.build() ?: return null
        val path = writeFile(FileType.DIR, bytes) ?: return null
        return File(path)
    }

    fun createELG(elg: ELG, folderName: String? = null): File? {
        val bytes = elg.build() ?: return null
        val path = writeFile(FileType.ELG, bytes, folderName) ?: return null
        elg.fileWriteOK()
        return File(path)
    }

    fun createSIN(sin: SIN): File? {
        val bytes = sin.build() ?: return null
        val path = writeFile(FileType.SIN, bytes) ?: return null
        return File(path)
    }

    interface Listener {
        fun onError()
        fun onReadBOC(boc: BOC)
        fun onReadTRF(trf: TRF)
        fun onReadDKL(dkl: DKL)
    }

    fun parse(mxdFileListener: MXDFile.Listener?, fileType: FileType, bytes: ByteArray?, listener: Listener, fromServer: Boolean = false) {

        val pair = parse(mxdFileListener, fileType, bytes, fromServer)
        val mxd = pair.first
        if (mxd == null) {
            listener.onError()
            return
        }
        when (mxd) {
            is TRF -> {
                listener.onReadTRF(mxd)
                return
            }
            is BOC -> {
                listener.onReadBOC(mxd)
                return
            }
            is DKL -> {
                listener.onReadDKL(mxd)
                return
            }
        }
        listener.onError()
    }

    fun parse(listener: MXDFile.Listener?, fileType: FileType, bytes: ByteArray?, fromServer: Boolean = false, rsaPublicKey: ByteArray? = null): Pair<MXD?, MXDError> {
        if (bytes?.isEmpty() != false) {
            return Pair(null, MXDError.FileDataEmpty)
        }
        var result = MXDError.FileNotFound
        when (fileType) {
            FileType.TRF -> {
                val trf = TRF()
                result = trf.parse(listener, bytes)
                if (MXDError.Success == result) {
                    return Pair(trf, MXDError.Success)
                }
            }
            FileType.BOC -> {
                val boc = BOC()
                result = boc.parse(listener, bytes)
                if (MXDError.Success == result) {
                    return Pair(boc, MXDError.Success)
                }
            }
            FileType.DKL -> {
                val dkl = DKL(rsaPublicKey, fromServer)
                result = dkl.parse(listener, bytes)
                if (MXDError.Success == result) {
                    return Pair(dkl, MXDError.Success)
                }
            }
            else -> {}
        }
        return Pair(null, result)
    }
}
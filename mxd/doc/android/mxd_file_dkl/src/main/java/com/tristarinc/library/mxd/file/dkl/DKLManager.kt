package com.tristarinc.library.mxd.file.dkl

import android.content.Context
import com.socks.library.KLog
import com.tristarinc.library.bit.BytesLongUtils
import com.tristarinc.library.mlog.MLog
import com.tristarinc.library.mxd.MXDError
import com.tristarinc.library.mxd.bean.FileType
import com.tristarinc.library.mxd.bean.MXDFile
import com.tristarinc.library.mxd.file.MXDManager
import com.tristarinc.library.mxd.file.bean.KeyGroup
import com.tristarinc.library.mxd.file.dkl.room.DKLData
import com.tristarinc.library.mxd.file.dkl.room.DKLDatabase
import com.tristarinc.library.mxd.file.server.DKL
import java.io.File
import java.nio.ByteOrder

object DKLManager {

    fun readFile(context: Context, file: File, fromServer: Boolean = false, listener: MXDFile.Listener? = null): MXDError {
        if (!file.exists()) {
            return MXDError.FileNotFound
        }
        val bytesFile = runCatching { file.readBytes() }.getOrElse { return MXDError.FileReadError }

        val rsaPublicKey = getCurrentDKL(context)?.getRSAPublicKey()

        val (mxd, error) = MXDManager.parse(listener, FileType.DKL, bytesFile, fromServer, rsaPublicKey)
        mxd?.header?.fileName = file.name

        (mxd as? DKL)?.let { saveDatabase(context, file.name, mxd) }
        return error
    }

    private fun saveDatabase(context: Context, fileName: String, dkl: DKL) {
        val dklData = DKLData().also {
            it.fileName = fileName
            it.validFromTime = dkl.getValidFromTime()
            it.initialCreationTime = dkl.getInitialCreationTime()
            it.fileLoadTime = System.currentTimeMillis()
            it.dkl = dkl
        }
        DKLDatabase.getDatabase(context).getDao().insert(dklData)
    }

    fun hasNoDKLFiles(context: Context): Boolean {
        return getAllDKLList(context).isEmpty()
    }

    fun getAllDKLList(context: Context): List<DKLData> {
        return try {
            DKLDatabase.getDatabase(context).getDao().all
        } catch (e: Exception) {
            MLog.e("DklList", "Load failed: $e")
            emptyList()
        }
    }

    private fun getDKLList(context: Context): List<DKLData> {
        return try {
            DKLDatabase.getDatabase(context).getDao().query()
        } catch (e: Exception) {
            MLog.e("DklList", "Load failed: $e")
            emptyList()
        }
    }

    fun clearDKLDatabase(context: Context) {
        DKLDatabase.getDatabase(context).getDao().deleteAll()
    }

    fun getCurrentDKL(context: Context): DKL? {
        return getCurrentDKLData(context)?.dkl
    }

    private fun getCurrentDKLData(context: Context): DKLData? {
        return getDKLList(context).firstOrNull { it.dkl?.isValid() == true }
    }

    interface Listener {
        fun onFileNotFound(keyID: Long)
        fun onNotFoundInCurrentDKL(keyID: Long)
    }
    fun findKeyEntry(context: Context, keyID: Long, listener: Listener? = null): KeyGroup? {
        KLog.d("DallasKey - findKeyEntry", "start:getCurrentDKL")
        val currentDKL = getCurrentDKL(context)
        KLog.d("DallasKey - findKeyEntry", "end:getCurrentDKL")
        if (currentDKL == null) {
            KLog.e("DallasKey - findKeyEntry", "no DKL file")
            listener?.onFileNotFound(keyID)
        }
        KLog.d("DallasKey - findKeyEntry", "start:findKeyEntry")
        val keyGroup = currentDKL?.findKeyEntry(dallasKey2DKLKey(keyID))
        KLog.d("DallasKey - findKeyEntry", "end:findKeyEntry")
        if (keyGroup == null) {
            listener?.onNotFoundInCurrentDKL(keyID)
        }
        return keyGroup
    }

    /**
     * DallasKey转成DKL里的KeyID
     */
    fun dallasKey2DKLKey(keyID: Long): Long {
        //87496571729477800
        //Has bytes:  01 36 D9 AB 1D 00 00 A8
        //Reversed: A8 00 00 1D AB D9 36 01
        //Remove checksum & zeros: 1D AB D9 36 01
        //As an integer: 127,437,190,657
        val bytes = BytesLongUtils.longToBytes(keyID)
        KLog.d("dallasKey2DKLKey", "bytes: ${bytes.toMutableList()}")
        bytes[0] = 0
        return BytesLongUtils.bytesToLong(bytes, ByteOrder.BIG_ENDIAN)
    }
}
package com.tristarinc.library.mxd.file.dkl.room

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.tristarinc.library.room.RoomUtils

@Database(entities = [DKLData::class], version = 2, exportSchema = false)
abstract class DKLDatabase : RoomDatabase() {

    abstract fun getDao(): DKLDataDao

    companion object {
        //防止同一时间创建多个实例
        @Volatile
        private var INSTANCE: DKLDatabase? = null

        @JvmStatic
        fun getDatabase(context: Context): DKLDatabase {
            if (INSTANCE == null) {
                val file = RoomUtils.getDatabaseFile("dkldata_database.db")
                INSTANCE = Room.databaseBuilder(
                    context.applicationContext,
                    DKLDatabase::class.java,
                    file.absolutePath
                ).apply {
                    addMigrations(MIGRATION_1_2, MIGRATION_2_1)
                }
                    .allowMainThreadQueries()
                    .build()
            }
            return INSTANCE!!
        }

        @JvmStatic
        fun destroyInstance() {
            INSTANCE = null
        }
    }
}

val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE DKLData ADD COLUMN fileLoadTime INTEGER NOT NULL DEFAULT 0")
    }
}

val MIGRATION_2_1 = object : Migration(2, 1) {
    override fun migrate(db: SupportSQLiteDatabase) {
        //Drop column isn't supported by SQLite, so the data must manually be moved
        db.run {
            execSQL("CREATE TABLE DKLData_Backup (fileName TEXT NOT NULL, validFromTime INTEGER NOT NULL, initialCreationTime INTEGER NOT NULL, dkl TEXT, PRIMARY KEY (fileName, validFromTime, initialCreationTime))")
            execSQL("INSERT INTO DKLData_Backup SELECT fileName, validFromTime, initialCreationTime, dkl FROM DKLData")
            execSQL("DROP TABLE DKLData")
            execSQL("ALTER TABLE DKLData_Backup RENAME to DKLData")
        }
    }
}

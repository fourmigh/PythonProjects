package com.tristarinc.library.mxd.file.dkl.room

import androidx.room.*

@Dao
interface DKLDataDao {

    @get:Query("SELECT * FROM DKLData")
    val all: List<DKLData>

    // return all items, sorted so that the file to use should be at/near the start of the list
    @Query("SELECT * FROM DKLData ORDER BY fileLoadTime DESC, validFromTime DESC, initialCreationTime DESC")
    fun query(): List<DKLData>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun insert(data: DKLData)

    @Delete
    fun delete(vararg data: DKLData)

    @Query("DELETE FROM DKLData")
    fun deleteAll()
}
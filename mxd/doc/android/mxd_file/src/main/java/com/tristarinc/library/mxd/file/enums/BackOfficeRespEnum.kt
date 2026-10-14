package com.tristarinc.library.mxd.file.enums

enum class BackOfficeRespEnum {
    SUCCESS,
    FILE_NOT_FOUND,         //get file failed
    INVALID_CMD,            //boc is null or str
    HTTP_FAILURE,           //backoffice failed
    FILE_CREATE_FAILED,     //create mxd file failed，download file write failed
    FILE_RENAME_FAILED,
    INVALID_FILE,
    COMMAND_FAILED,         //download is empty or null
    WRONG_FILE_EXTENSION,
    CADIX_BUSY
}
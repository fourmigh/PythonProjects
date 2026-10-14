package com.tristarinc.library.mxd.file.enums

enum class BackOfficeCmdEnum {
    UNDEFINED,
    SYNC_TIME,          //Requests the terminal to synchronise its clock (date / time) with the server date/time passed
    SET_CALL_TIME,      //Requests the terminal to schedule the next call in time to that passed
    CDX_UPDATE_START,
    CDX_UPDATE_CONTINUE,
    CDX_UPDATE_END,
    CDX_H1314_DOWNLOAD,
    CDX_H1304_DOWNLOAD,
    CDX_T1314_UPLOAD,
    CDX_T1304_UPLOAD,
    CDX_T1300_UPLOAD,
    CDX_HEADER_UPLOAD,
    SIN_UPLOAD,         //Requests the terminal to upload a SIN file
    ELG_START_NEW,      //Requests the terminal to close the existing ELG file and start a new ELG file
    ELG_GET_LIST,       //Requests a directory listing of ELG files available in the terminal
    ELG_UPLOAD,         //Requests the terminal to upload the ELG file passed
    ELG_DELETE,         //Requests the terminal to delete the ELG file passed
    LOG_START_NEW,      //Requests the terminal to close the existing LOG file and start a new LOG file
    LOG_GET_LIST,       //Requests a directory listing of LOG files available in the terminal
    LOG_UPLOAD,         //Requests the terminal to upload the LOG file passed
    LOG_DELETE,         //Requests the terminal to delete the LOG file passed
    CLT_START_NEW,
    CLT_GET_LIST,
    CLT_UPLOAD,
    CLT_DELETE,
    LUL_START_NEW,
    LUL_GET_LIST,
    LUL_UPLOAD,
    LUL_DELETE,
    AP3_GET_PENDING_LIST,   //Requests a list of pending applications from the terminal
    AP3_DELETE_PENDING,     //Requests the terminal to delete the pending application passed
    AP3_DOWNLOAD,           //Requests the terminal to download the new application passed
    APP_DOWNLOAD,
    AP2_DOWNLOAD,
    BLL_GET_PENDING_LIST,
    BLL_DELETE_PENDING,
    BLL_DOWNLOAD,
    PIC_GET_PENDING_LIST,   //Requests a list of pending PIC firmware from the terminal
    PIC_DELETE_PENDING,     //Requests the terminal to delete the pending PIC firmware passed
    PIC_DOWNLOAD,           //Requests the terminal to download the new PIC firmware passed
    CFG_GET_ACTIVE_LIST,    //Requests a list of active CFG files from the terminal
    CFG_GET_PENDING_LIST,   //Requests a list of pending CFG files from the terminal
    CFG_DELETE_PENDING,     //Requests the terminal to delete the pending CFG file passed
    CFG_DOWNLOAD,           //Requests the terminal to download the new CFG file passed
    DKL_GET_ACTIVE_LIST,    //Requests a list of active dallas key DKL  files from the terminal
    DKL_GET_PENDING_LIST,   //Requests a list of pending dallas key DKL  files from the terminal
    DKL_DELETE_PENDING,     //Requests the terminal to delete the pending dallas key DKL  file passed
    DKL_DOWNLOAD,           //Requests the terminal to download the new dallas key DKL  file passed
    TRF_GET_ACTIVE_LIST,    //Requests a list of active tariff TRF files from the terminal
    TRF_GET_PENDING_LIST,   //Requests a list of pending tariff TRF files from the terminal
    TRF_DELETE_PENDING,     //Requests the terminal to delete the pending tariff TRF file passed
    TRF_DOWNLOAD,           //Requests the terminal to download the new tariff TRF file passed
    HTL_GET_ACTIVE_LIST,
    HTL_GET_PENDING_LIST,
    HTL_DELETE_PENDING,
    HTL_DOWNLOAD,
    LUL_GET_ACTIVE_LIST,
    LUL_GET_PENDING_LIST,
    LUL_DELETE_PENDING,
    LUL_DOWNLOAD,
    CLT_GET_ACTIVE_LIST,
    CLT_GET_PENDING_LIST,
    CLT_DELETE_PENDING,
    CLT_DOWNLOAD,
    DKX_GET_ACTIVE_LIST,
    DKX_GET_PENDING_LIST,
    DKX_DELETE_PENDING,
    DKX_DOWNLOAD,
    RESTART_MACHINE,
    DFT_TRF_CHANGE,
    APK_DOWNLOAD
}

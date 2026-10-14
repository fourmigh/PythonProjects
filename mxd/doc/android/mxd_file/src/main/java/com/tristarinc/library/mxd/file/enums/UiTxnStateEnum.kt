package com.tristarinc.library.mxd.file.enums

enum class UiTxnStateEnum {
    STARTED,
    REG_ENTERED,
    SUCCESS,

    /**
     * Exiting based on a user action.
     */
    CANCELED,
    PAYMENT_FAILED,
    PAYMENT_DECLINED,
    PRINT_ERROR,
    MIXCHANGE_ERROR,

    /**
     * Exiting based on a system error.
     */
    ABORT
}
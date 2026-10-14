package com.tristarinc.library.mxd.file.enums

enum class StartupReasonEnum {
    POWER_ON,
    WATCHDOG,
    EXCEPTION,
    APP_ERROR,
    ON_REQUEST,
    SAFE_MODE,
    BLL_LOAD,
    PIC_LOAD,
    POWER_CYCLED,
    UNKNOWN,
    HW_WATCHDOG,
    LOSS_OF_CLOCK,
    LOW_VOLTAGE
}
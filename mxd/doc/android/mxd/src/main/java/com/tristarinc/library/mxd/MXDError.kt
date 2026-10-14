package com.tristarinc.library.mxd

enum class MXDError {
    Success,
    FileNotFound,
    FileReadError,
    FileDataEmpty,
    BadChecksum,
    SecondarySignatureDataError,
    PrimarySignatureDataError,
    PinError,
    PinNotInput,
    PinInputError,
    SchemaAndDataEmpty,
    FileDataError,
    RSAVerifyFailed,
    SHA1EncodeFailed,
    XTEADecipherFailed,
    SchemaSizeError,
    NoPrimarySignatureData
}
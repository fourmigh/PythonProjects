"""MXD 解析/生成错误码（对应 Kotlin 的 MXDError）。"""

from enum import IntEnum


class MXDError(IntEnum):
    Success = 0
    FileDataEmpty = 1
    FileNotFound = 2
    BadChecksum = 3
    SecondarySignatureDataError = 4
    PrimarySignatureDataError = 5
    PinNotInput = 6
    PinInputError = 7
    PinError = 8
    SchemaAndDataEmpty = 9
    FileDataError = 10
    NoPrimarySignatureData = 11
    RSAVerifyFailed = 12
    SHA1EncodeFailed = 13
    XTEADecipherFailed = 14
    FileReadError = 15
    SchemaParseError = 16
    UnsupportedContentType = 17

    @property
    def message(self) -> str:
        return _MESSAGES.get(self, self.name)


_MESSAGES = {
    MXDError.Success: "成功",
    MXDError.FileDataEmpty: "文件数据为空",
    MXDError.FileNotFound: "文件不存在",
    MXDError.BadChecksum: "CRC 校验失败",
    MXDError.SecondarySignatureDataError: "次签名数据错误",
    MXDError.PrimarySignatureDataError: "主签名数据错误",
    MXDError.PinNotInput: "未输入 PIN",
    MXDError.PinInputError: "PIN 输入错误",
    MXDError.PinError: "PIN 校验失败",
    MXDError.SchemaAndDataEmpty: "Schema 与 Data 为空",
    MXDError.FileDataError: "文件结构长度错误",
    MXDError.NoPrimarySignatureData: "缺少主签名数据",
    MXDError.RSAVerifyFailed: "RSA 签名验证失败",
    MXDError.SHA1EncodeFailed: "SHA1 计算失败",
    MXDError.XTEADecipherFailed: "XTEA 解密失败",
    MXDError.FileReadError: "文件读取失败",
    MXDError.SchemaParseError: "Schema 解析失败",
    MXDError.UnsupportedContentType: "不支持的 ContentType",
}

"""通用 MXD 头部解析与构建。

Header 是若干 TLV（7bit tag + 7bit 长度 + 值）组成，以 EndOfHeader(tag 0) 结束。
"""

from dataclasses import dataclass, field
from typing import Optional

from .binary import encode_tlv, le_to_int, read_tlv
from .schema import ContentType, Tag


@dataclass
class Header:
    # 基本字段（对应 Tag）
    file_type: Optional[str] = None                 # 1
    compatibility_level: int = 0                    # 2
    major_version: Optional[int] = 0                # 3 (deprecated)
    minor_version: Optional[int] = 0                # 4 (deprecated)
    obfuscation_type: int = 0                       # 5
    compression_type: int = 0                       # 6
    primary_signature_type: int = 0                 # 7
    secondary_signature_type: int = 0               # 8
    pin_type: int = 0                               # 9
    content_type: int = int(ContentType.SchemaData)  # 10
    content_length: Optional[int] = None            # 11
    compressed_content_length: Optional[int] = None  # 12
    number_of_pin_digits: int = 4                   # 13
    customer: str = ""                              # 14
    origin: str = ""                                # 15
    user_name: str = ""                             # 16
    initial_creation_time: Optional[int] = None     # 17
    final_modification_time: Optional[int] = None   # 18
    machine_unique_id: int = 0                      # 19
    valid_from_time: int = 0                        # 20
    application_base_address: Optional[str] = None  # 21
    application_entry_point: Optional[str] = None   # 22
    version: Optional[str] = None                   # 23
    rsa_public_key: Optional[bytes] = None          # 24
    electronics_version: Optional[str] = None       # 25
    initial_creation_time_zone: Optional[int] = None  # 26
    final_modification_time_zone: Optional[int] = None  # 27
    valid_from_time_zone: Optional[int] = None      # 28
    original_file_name: Optional[str] = None        # 29

    # 非文件字段
    file_name: Optional[str] = None

    # ---- 便捷判断 ----
    def is_obfuscated(self) -> bool:
        return self.obfuscation_type == 1

    def has_primary_signature(self) -> bool:
        return self.primary_signature_type == 1

    def has_secondary_signature(self) -> bool:
        return self.secondary_signature_type == 1

    def is_pin_required(self) -> bool:
        return self.pin_type == 1


_INT8_TAGS = {Tag.CompatibilityLevel, Tag.MajorVersion, Tag.MinorVersion,
              Tag.ObfuscationType, Tag.CompressionType, Tag.PrimarySignatureType,
              Tag.SecondarySignatureType, Tag.PINType, Tag.ContentType, Tag.NumberOfPINDigits}
_INT_SIGNED8_TAGS = {Tag.InitialCreationTimeZone, Tag.FinalModificationTimeZone, Tag.ValidFromTimeZone}
_UINT_TAGS = {Tag.ContentLength, Tag.CompressedContentLength}
_TIME_TAGS = {Tag.InitialCreationTime, Tag.FinalModificationTime, Tag.ValidFromTime, Tag.MachineUniqueID}
_STR_TAGS = {Tag.FileType, Tag.Customer, Tag.Origin, Tag.UserName, Tag.ApplicationBaseAddress,
             Tag.ApplicationEntryPoint, Tag.Version, Tag.ElectronicsVersion, Tag.OriginalFileName}


def signed_le(value: int) -> bytes:
    """按 1/2/4/8 字节选择能容纳的最小宽度，编码为小端有符号整数。

    例：60 -> 1 字节 0x3C；480(+0800 的分钟数) -> 2 字节 0xE0 0x01。
    """
    for size in (1, 2, 4, 8):
        try:
            return int(value).to_bytes(size, "little", signed=True)
        except OverflowError:
            continue
    raise OverflowError("有符号整数超出 64 位范围: %r" % value)


def parse_header(data: bytes, index: int = 0):
    """解析头部，返回 (Header, 结束后的 index)。"""
    header = Header()
    attr = {
        Tag.FileType: "file_type",
        Tag.CompatibilityLevel: "compatibility_level",
        Tag.MajorVersion: "major_version",
        Tag.MinorVersion: "minor_version",
        Tag.ObfuscationType: "obfuscation_type",
        Tag.CompressionType: "compression_type",
        Tag.PrimarySignatureType: "primary_signature_type",
        Tag.SecondarySignatureType: "secondary_signature_type",
        Tag.PINType: "pin_type",
        Tag.ContentType: "content_type",
        Tag.ContentLength: "content_length",
        Tag.CompressedContentLength: "compressed_content_length",
        Tag.NumberOfPINDigits: "number_of_pin_digits",
        Tag.Customer: "customer",
        Tag.Origin: "origin",
        Tag.UserName: "user_name",
        Tag.InitialCreationTime: "initial_creation_time",
        Tag.FinalModificationTime: "final_modification_time",
        Tag.MachineUniqueID: "machine_unique_id",
        Tag.ValidFromTime: "valid_from_time",
        Tag.ApplicationBaseAddress: "application_base_address",
        Tag.ApplicationEntryPoint: "application_entry_point",
        Tag.Version: "version",
        Tag.RSAPublicKey: "rsa_public_key",
        Tag.ElectronicsVersion: "electronics_version",
        Tag.InitialCreationTimeZone: "initial_creation_time_zone",
        Tag.FinalModificationTimeZone: "final_modification_time_zone",
        Tag.ValidFromTimeZone: "valid_from_time_zone",
        Tag.OriginalFileName: "original_file_name",
    }
    while index < len(data):
        tag, value, index = read_tlv(data, index)
        if tag is None:
            break
        if tag == Tag.EndOfHeader:
            break
        name = attr.get(tag)
        if name is None or value is None:
            continue
        if tag in _UINT_TAGS:
            setattr(header, name, le_to_int(value))
        elif tag in _INT_SIGNED8_TAGS:
            setattr(header, name, le_to_int(value, signed=True))
        elif tag in _INT8_TAGS:
            setattr(header, name, le_to_int(value))
        elif tag in _TIME_TAGS:
            setattr(header, name, le_to_int(value))
        elif tag == Tag.RSAPublicKey:
            setattr(header, name, bytes(value))
        else:
            setattr(header, name, value.decode("utf-8", "replace"))
    return header, index


def build_header(header: Header) -> bytes:
    """按 Tag 顺序构建头部字节。"""
    out = bytearray()

    def add(tag, value: bytes):
        out.extend(encode_tlv(int(tag), value))

    if header.file_type is not None:
        add(Tag.FileType, header.file_type.encode("utf-8"))
    add(Tag.CompatibilityLevel, bytes([header.compatibility_level & 0xFF]))
    if header.major_version is not None:
        add(Tag.MajorVersion, bytes([header.major_version & 0xFF]))
    if header.minor_version is not None:
        add(Tag.MinorVersion, bytes([header.minor_version & 0xFF]))
    add(Tag.ObfuscationType, bytes([header.obfuscation_type & 0xFF]))
    add(Tag.CompressionType, bytes([header.compression_type & 0xFF]))
    add(Tag.PrimarySignatureType, bytes([header.primary_signature_type & 0xFF]))
    add(Tag.SecondarySignatureType, bytes([header.secondary_signature_type & 0xFF]))
    add(Tag.PINType, bytes([header.pin_type & 0xFF]))
    if header.content_type:
        add(Tag.ContentType, bytes([header.content_type & 0xFF]))
    if header.content_length is not None:
        add(Tag.ContentLength, int(header.content_length).to_bytes(4, "little"))
    if header.compressed_content_length is not None:
        add(Tag.CompressedContentLength, int(header.compressed_content_length).to_bytes(4, "little"))
    if header.pin_type == 1:
        add(Tag.NumberOfPINDigits, bytes([header.number_of_pin_digits & 0xFF]))
    add(Tag.Customer, header.customer.encode("utf-8"))
    add(Tag.Origin, header.origin.encode("utf-8"))
    add(Tag.UserName, header.user_name.encode("utf-8"))
    if header.initial_creation_time is not None:
        add(Tag.InitialCreationTime, int(header.initial_creation_time).to_bytes(4, "little"))
    if header.final_modification_time is not None:
        add(Tag.FinalModificationTime, int(header.final_modification_time).to_bytes(4, "little"))
    if header.machine_unique_id:
        add(Tag.MachineUniqueID, int(header.machine_unique_id).to_bytes(8, "little"))
    add(Tag.ValidFromTime, int(header.valid_from_time).to_bytes(4, "little"))
    if header.application_base_address is not None:
        add(Tag.ApplicationBaseAddress, header.application_base_address.encode("utf-8"))
    if header.application_entry_point is not None:
        add(Tag.ApplicationEntryPoint, header.application_entry_point.encode("utf-8"))
    if header.version is not None:
        add(Tag.Version, header.version.encode("utf-8"))
    if header.rsa_public_key is not None:
        add(Tag.RSAPublicKey, bytes(header.rsa_public_key))
    if header.electronics_version is not None:
        add(Tag.ElectronicsVersion, header.electronics_version.encode("utf-8"))
    if header.initial_creation_time_zone is not None:
        add(Tag.InitialCreationTimeZone, signed_le(header.initial_creation_time_zone))
    if header.final_modification_time_zone is not None:
        add(Tag.FinalModificationTimeZone, signed_le(header.final_modification_time_zone))
    if header.valid_from_time_zone is not None:
        add(Tag.ValidFromTimeZone, signed_le(header.valid_from_time_zone))
    if header.original_file_name is not None:
        add(Tag.OriginalFileName, header.original_file_name.encode("utf-8"))

    out.extend(encode_tlv(int(Tag.EndOfHeader), b""))
    return bytes(out)

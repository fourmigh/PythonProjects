"""DKL（Dallas Key List）文件的解析与生成。

文件结构：
  Header + Schema + Data + [加密PIN(20)] + [主签名(128)] + [次签名(128)] + CRC(4)

  - CRC    : ~zlib.crc32(body)，小端
  - 混淆    : XTEA，密钥 = SHA1(Header)[:16]
  - PIN    : SHA1(pin + Header + 加密区)[:20]
  - 主签名  : RSA-PKCS1v15-SHA1(Header + 加密区 + PIN)
  - 次签名  : RSA-PKCS1v15-SHA1(Header + 加密区 + PIN + 主签名)
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Optional

from . import crc32, rsa_sign, xtea
from .binary import write_7bit_uint
from .errors import MXDError
from .mxd import Header, build_header, parse_header
from .schema import (DataType, Element, SchemaTokenType, parse_schema, read_data,
                     record_element, write_primitive, write_schema)

PIN_HASH_SIZE = 20
SIGNATURE_SIZE = 128
CRC_SIZE = 4


@dataclass
class HourMinute:
    hour: int = 0
    minute: int = 0


@dataclass
class Time:
    start: HourMinute = field(default_factory=HourMinute)
    end: HourMinute = field(default_factory=HourMinute)


@dataclass
class AccessTime:
    day_of_week_mask: int = 127
    times: List[Time] = field(default_factory=list)


@dataclass
class KeyEntry:
    name: str = ""
    key_id: int = 0


@dataclass
class KeyGroup:
    name: str = ""
    type: str = ""
    keys: List[KeyEntry] = field(default_factory=list)
    access_times: List[AccessTime] = field(default_factory=list)

    def find_key_entry(self, key_id: int) -> Optional[KeyEntry]:
        return next((k for k in self.keys if k.key_id == key_id), None)


def _leaf_schema() -> List[Element]:
    """叶节点在前的 schema（与 signing_test/*.dkl 一致）。"""
    def prim(dt, name):
        return Element(dt, name)

    r0 = Element(field_name="")
    r0.elements = [prim(DataType.MXDDT_VAR_INT64, "Hour"),
                   prim(DataType.MXDDT_VAR_INT64, "Minute")]
    r1 = Element(field_name="")
    r1.elements = [record_element(0, "StartTime"), record_element(0, "EndTime")]
    r2 = Element(field_name="")
    r2.elements = [prim(DataType.MXDDT_VAR_INT64, "DayOfWeekMask"),
                   record_element(1, "Time", is_array=True)]
    r3 = Element(field_name="")
    r3.elements = [record_element(2, "AccessTime", is_array=True)]
    r4 = Element(field_name="")
    r4.elements = [prim(DataType.MXDDT_UTF8_STRING, "Name"),
                   prim(DataType.MXDDT_VAR_INT64, "KeyID")]
    r5 = Element(field_name="")
    r5.elements = [record_element(4, "KeyEntry", is_array=True)]
    r6 = Element(field_name="")
    r6.elements = [prim(DataType.MXDDT_UTF8_STRING, "Name"),
                   prim(DataType.MXDDT_UTF8_STRING, "Type"),
                   record_element(5, "KeyList"),
                   record_element(3, "AccessTimeList")]
    r7 = Element(field_name="")
    r7.elements = [record_element(6, "KeyGroup", is_array=True)]
    r8 = Element(field_name="")
    r8.elements = [record_element(7, "KeyGroupsList")]
    return [r0, r1, r2, r3, r4, r5, r6, r7, r8]


def _root_schema() -> List[Element]:
    """根记录在末尾、KeyGroup 在记录 0 的 schema（与 SALE2017 / CHINA1 一致）。"""
    def prim(dt, name):
        return Element(dt, name)

    r0 = Element(field_name="")
    r0.elements = [record_element(1, "KeyGroup", is_array=True)]
    r1 = Element(field_name="")
    r1.elements = [prim(DataType.MXDDT_UTF8_STRING, "Name"),
                   prim(DataType.MXDDT_UTF8_STRING, "Type"),
                   record_element(2, "KeyList"),
                   record_element(4, "AccessTimeList")]
    r2 = Element(field_name="")
    r2.elements = [record_element(3, "KeyEntry", is_array=True)]
    r3 = Element(field_name="")
    r3.elements = [prim(DataType.MXDDT_UTF8_STRING, "Name"),
                   prim(DataType.MXDDT_VAR_INT64, "KeyID")]
    r4 = Element(field_name="")
    r4.elements = [record_element(5, "AccessTime", is_array=True)]
    r5 = Element(field_name="")
    r5.elements = [prim(DataType.MXDDT_VAR_INT64, "DayOfWeekMask"),
                   record_element(6, "Time", is_array=True)]
    r6 = Element(field_name="")
    r6.elements = [record_element(7, "StartTime"), record_element(7, "EndTime")]
    r7 = Element(field_name="")
    r7.elements = [prim(DataType.MXDDT_VAR_INT64, "Hour"),
                   prim(DataType.MXDDT_VAR_INT64, "Minute")]
    r8 = Element(field_name="")
    r8.elements = [record_element(0, "KeyGroupsList")]
    return [r0, r1, r2, r3, r4, r5, r6, r7, r8]


SCHEMA_STYLES = {"leaf": _leaf_schema, "root": _root_schema}


def build_dkl_schema(style: str = "leaf") -> List[Element]:
    """返回 DKL schema 记录定义。style: 'leaf'（默认）或 'root'。"""
    try:
        return SCHEMA_STYLES[style]()
    except KeyError:
        raise ValueError("未知的 schema 风格: %r" % style)


def build_data(groups: List[KeyGroup]) -> bytes:
    """按 DKL schema 序列化数据区。"""
    out = bytearray()
    out += write_7bit_uint(len(groups))
    for g in groups:
        write_primitive(out, DataType.MXDDT_UTF8_STRING, g.name or "")
        write_primitive(out, DataType.MXDDT_UTF8_STRING, g.type or "")
        out += write_7bit_uint(len(g.keys))
        for k in g.keys:
            write_primitive(out, DataType.MXDDT_UTF8_STRING, k.name or "")
            write_primitive(out, DataType.MXDDT_VAR_INT64, int(k.key_id))
        out += write_7bit_uint(len(g.access_times))
        for at in g.access_times:
            write_primitive(out, DataType.MXDDT_VAR_INT64, int(at.day_of_week_mask))
            out += write_7bit_uint(len(at.times))
            for t in at.times:
                write_primitive(out, DataType.MXDDT_VAR_INT64, int(t.start.hour))
                write_primitive(out, DataType.MXDDT_VAR_INT64, int(t.start.minute))
                write_primitive(out, DataType.MXDDT_VAR_INT64, int(t.end.hour))
                write_primitive(out, DataType.MXDDT_VAR_INT64, int(t.end.minute))
    return bytes(out)


def _to_int(value, default=0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _map_groups(root: dict) -> List[KeyGroup]:
    groups: List[KeyGroup] = []
    node = (root or {}).get("KeyGroupsList") or {}
    for g in (node.get("KeyGroup") or []):
        if not isinstance(g, dict):
            continue
        kg = KeyGroup(name=g.get("Name") or "", type=g.get("Type") or "")
        for k in ((g.get("KeyList") or {}).get("KeyEntry") or []):
            if isinstance(k, dict):
                kg.keys.append(KeyEntry(name=k.get("Name") or "",
                                        key_id=_to_int(k.get("KeyID"))))
        for at in ((g.get("AccessTimeList") or {}).get("AccessTime") or []):
            if not isinstance(at, dict):
                continue
            acc = AccessTime(day_of_week_mask=_to_int(at.get("DayOfWeekMask"), -1))
            for t in (at.get("Time") or []):
                if not isinstance(t, dict):
                    continue
                st = t.get("StartTime") or {}
                et = t.get("EndTime") or {}
                acc.times.append(Time(
                    start=HourMinute(_to_int(st.get("Hour")), _to_int(st.get("Minute"))),
                    end=HourMinute(_to_int(et.get("Hour")), _to_int(et.get("Minute"))),
                ))
            kg.access_times.append(acc)
        groups.append(kg)
    return groups


class DKL:
    def __init__(self):
        self.header = Header()
        self.key_groups: List[KeyGroup] = []

        # 解析产物
        self.raw: bytes = b""
        self.header_bytes: bytes = b""
        self.region: bytes = b""              # 加密/明文内容区
        self.decrypted: bytes = b""
        self.pin_hash: Optional[bytes] = None
        self.primary_signature: Optional[bytes] = None
        self.secondary_signature: Optional[bytes] = None
        self.schema_records = []
        self.root: dict = {}
        self.trailer_size: int = 0

        # 校验结果
        self.crc_ok: Optional[bool] = None
        self.pin_ok: Optional[bool] = None
        self.primary_sig_ok: Optional[bool] = None
        self.secondary_sig_ok: Optional[bool] = None

    # ------------------------------------------------------------------
    # 解析
    # ------------------------------------------------------------------
    def parse(self, data: bytes, rsa_public_key: Optional[bytes] = None,
              pin: Optional[str] = None, from_server: bool = False,
              check_crc: bool = True) -> MXDError:
        if not data:
            return MXDError.FileDataEmpty
        self.raw = data

        if check_crc:
            self.crc_ok = crc32.check(data)
            if not self.crc_ok:
                return MXDError.BadChecksum

        self.header, header_end = parse_header(data)
        self.header_bytes = data[:header_end]

        pin_size = PIN_HASH_SIZE if self.header.is_pin_required() else 0
        prim_size = SIGNATURE_SIZE if self.header.has_primary_signature() else 0
        sec_size = SIGNATURE_SIZE if self.header.has_secondary_signature() else 0
        self.trailer_size = pin_size + prim_size + sec_size + CRC_SIZE

        end = len(data) - CRC_SIZE
        if sec_size:
            self.secondary_signature = data[end - sec_size:end]
            end -= sec_size
        if prim_size:
            self.primary_signature = data[end - prim_size:end]
            end -= prim_size
        if pin_size:
            self.pin_hash = data[end - pin_size:end]
            end -= pin_size

        region_end = end
        if region_end < header_end:
            return MXDError.SchemaAndDataEmpty
        self.region = data[header_end:region_end]

        expected = header_end + len(self.region) + self.trailer_size
        if expected != len(data):
            return MXDError.FileDataError

        signed = self.header_bytes + self.region + (self.pin_hash or b"")

        # PIN 校验：SHA1(pin + Header + 加密区)
        if self.header.is_pin_required() and not from_server:
            if not pin:
                return MXDError.PinNotInput
            calc = hashlib.sha1(pin.encode("ascii", "ignore") + self.header_bytes + self.region).digest()
            self.pin_ok = (calc == self.pin_hash)
            if not self.pin_ok:
                return MXDError.PinError

        # 签名校验
        if not from_server:
            err = self._verify_signatures(signed, rsa_public_key)
            if err != MXDError.Success:
                return err

        # 解密
        content = self.region
        if self.header.is_obfuscated():
            key = hashlib.sha1(self.header_bytes).digest()[:16]
            content = xtea.decrypt(self.region, key)
        self.decrypted = content

        # 解析 schema + data
        try:
            records, index = parse_schema(content, 0)
            self.schema_records = records
            self.root, _ = read_data(content, index, records)
            self.key_groups = _map_groups(self.root)
        except Exception:
            return MXDError.SchemaParseError

        return MXDError.Success

    def _verify_signatures(self, signed: bytes, rsa_public_key: Optional[bytes]) -> MXDError:
        has_prim = self.header.has_primary_signature()
        has_sec = self.header.has_secondary_signature()
        header_key = self.header.rsa_public_key

        if rsa_public_key is not None and not has_prim:
            return MXDError.NoPrimarySignatureData

        # 主签名：有机器公钥时用它，否则（且无次签名）用文件头公钥
        if has_prim and self.primary_signature is not None:
            verify_key = rsa_public_key
            if verify_key is None and not has_sec:
                verify_key = header_key
            if verify_key is not None:
                self.primary_sig_ok = rsa_sign.verify(signed, self.primary_signature, verify_key)
                if not self.primary_sig_ok:
                    return MXDError.RSAVerifyFailed

        # 次签名：用文件头公钥验证（覆盖 主签名 之后的内容）
        if has_sec and self.secondary_signature is not None and header_key:
            self.secondary_sig_ok = rsa_sign.verify(
                signed + (self.primary_signature or b""), self.secondary_signature, header_key)
            if not self.secondary_sig_ok:
                return MXDError.RSAVerifyFailed

        return MXDError.Success

    @classmethod
    def from_file(cls, path: str, rsa_public_key: Optional[bytes] = None,
                  pin: Optional[str] = None, from_server: bool = False,
                  check_crc: bool = True):
        with open(path, "rb") as f:
            data = f.read()
        dkl = cls()
        err = dkl.parse(data, rsa_public_key=rsa_public_key, pin=pin,
                        from_server=from_server, check_crc=check_crc)
        dkl.header.file_name = path
        return dkl, err

    def find_key_entry(self, key_id: int):
        for g in self.key_groups:
            entry = g.find_key_entry(key_id)
            if entry is not None:
                return g, entry
        return None

    # ------------------------------------------------------------------
    # 生成
    # ------------------------------------------------------------------
    def build(self, header: Optional[Header] = None,
              groups: Optional[List[KeyGroup]] = None,
              obfuscate: bool = False,
              pin: Optional[str] = None,
              primary_key=None,
              secondary_key=None,
              pin_digits: int = 4,
              schema_style: str = "leaf") -> bytes:
        header = header or self.header
        groups = groups if groups is not None else self.key_groups

        if secondary_key is not None and primary_key is None:
            raise ValueError("次签名（新密钥）必须同时提供主签名（机器当前/旧密钥）")

        header.obfuscation_type = 1 if obfuscate else 0
        header.primary_signature_type = 1 if primary_key is not None else 0
        header.secondary_signature_type = 1 if secondary_key is not None else 0
        header.pin_type = 1 if pin else 0
        header.number_of_pin_digits = pin_digits
        header.content_type = 0

        if secondary_key is not None:
            key = rsa_sign.load_private_key(secondary_key) if not hasattr(secondary_key, "n") else secondary_key
            header.rsa_public_key = rsa_sign.public_der(key)
        elif primary_key is not None:
            key = rsa_sign.load_private_key(primary_key) if not hasattr(primary_key, "n") else primary_key
            header.rsa_public_key = rsa_sign.public_der(key)

        header_bytes = build_header(header)

        schema_bytes = write_schema(build_dkl_schema(schema_style))
        data_bytes = build_data(groups)
        content = bytearray(schema_bytes + data_bytes)

        if obfuscate:
            # 加密时补齐到 8 字节块：先写 END_DATA(0xFF)，再补 0x00
            content.append(SchemaTokenType.MXDDT_END_DATA)
            while len(content) % 8:
                content.append(0x00)
            key = hashlib.sha1(header_bytes).digest()[:16]
            region = xtea.encrypt(bytes(content), key)
        else:
            region = bytes(content)

        pin_bytes = b""
        if pin:
            pin_bytes = hashlib.sha1(pin.encode("ascii", "ignore") + header_bytes + region).digest()[:PIN_HASH_SIZE]

        signed = header_bytes + region + pin_bytes
        primary_sig = b""
        secondary_sig = b""
        if primary_key is not None:
            primary_sig = rsa_sign.sign(signed, primary_key)
        if secondary_key is not None:
            secondary_sig = rsa_sign.sign(signed + primary_sig, secondary_key)

        body = header_bytes + region + pin_bytes + primary_sig + secondary_sig
        return body + crc32.calc_bytes(body)

    def build_to_file(self, path: str, **kwargs) -> str:
        data = self.build(**kwargs)
        with open(path, "wb") as f:
            f.write(data)
        return path

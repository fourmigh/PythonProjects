"""MXD Schema / Data 的解析与序列化。

语法：
  - Schema 由若干“记录(record)”定义组成，记录之间用 MXDDT_END_RECORD(0xF0) 分隔，
    以 MXDDT_END_SCHEMA(0xF1) 结束。
  - 每个字段定义：<DataType(+ARRAY 0x40)> [若为 RECORD 则跟 7bit 记录号] <7bit 长度 + UTF8 名称>
  - 数据区按 schema 描述的记录顺序、自描述读取，以 MXDDT_END_DATA(0xFF) 或缓冲区结束。
"""

from enum import IntEnum

from .binary import read_7bit_int, read_7bit_uint, read_length_prefixed, write_7bit_int, write_7bit_uint, write_length_prefixed


class Tag(IntEnum):
    EndOfHeader = 0
    FileType = 1
    CompatibilityLevel = 2
    MajorVersion = 3
    MinorVersion = 4
    ObfuscationType = 5
    CompressionType = 6
    PrimarySignatureType = 7
    SecondarySignatureType = 8
    PINType = 9
    ContentType = 10
    ContentLength = 11
    CompressedContentLength = 12
    NumberOfPINDigits = 13
    Customer = 14
    Origin = 15
    UserName = 16
    InitialCreationTime = 17
    FinalModificationTime = 18
    MachineUniqueID = 19
    ValidFromTime = 20
    ApplicationBaseAddress = 21
    ApplicationEntryPoint = 22
    Version = 23
    RSAPublicKey = 24
    ElectronicsVersion = 25
    InitialCreationTimeZone = 26
    FinalModificationTimeZone = 27
    ValidFromTimeZone = 28
    OriginalFileName = 29


class DataType(IntEnum):
    MXDDT_NULL = 0
    MXDDT_RECORD = 1
    MXDDT_BOOL = 2
    MXDDT_HEX_BYTE_ARRAY = 3
    MXDDT_UTF8_STRING = 4
    MXDDT_ENUM = 5
    MXDDT_VAR_UINT64 = 6
    MXDDT_VAR_INT64 = 7


class SchemaTokenType:
    MXDDT_END_RECORD = 0xF0
    MXDDT_END_SCHEMA = 0xF1
    MXDDT_START_CHOICE = 0xF2
    MXDDT_END_CHOICE = 0xF3
    MXDDT_END_DATA = 0xFF
    MXD_ARRAY_TYPE = 0x40


class ContentType(IntEnum):
    SchemaData = 0
    Binary = 1
    Text = 2


class Element:
    """一个 schema 字段，或一条记录（field_name 为记录名）。"""

    __slots__ = ("data_type", "field_name", "rec_no", "is_array", "is_choice", "elements", "value")

    def __init__(self, data_type: int = DataType.MXDDT_NULL, field_name: str = "",
                 rec_no: int = -1, is_array: bool = False, is_choice: bool = False):
        self.data_type = int(data_type)
        self.field_name = field_name
        self.rec_no = rec_no
        self.is_array = is_array
        self.is_choice = is_choice
        self.elements = []
        self.value = None


def record_element(rec_no: int, field_name: str, is_array: bool = False) -> Element:
    return Element(DataType.MXDDT_RECORD, field_name, rec_no=rec_no, is_array=is_array)


def parse_schema(data: bytes, index: int = 0):
    """解析 schema，返回 (records, new_index)。records 是 Element 列表（记录）。"""
    elements = []
    records = []
    is_choice = False
    size = len(data)

    def end_record():
        nonlocal is_choice
        if not elements:
            return
        rec = Element(field_name="")
        rec.is_choice = is_choice
        rec.elements = list(elements)
        records.append(rec)
        is_choice = False
        elements.clear()

    while index < size:
        token = data[index]
        index += 1
        if token < SchemaTokenType.MXDDT_END_RECORD:
            is_array = bool(token & SchemaTokenType.MXD_ARRAY_TYPE)
            token &= ~SchemaTokenType.MXD_ARRAY_TYPE
            rec_no = -1
            if token == DataType.MXDDT_RECORD:
                rec_no, index = read_7bit_uint(data, index)
                if rec_no is None:
                    break
            raw_name, index = read_length_prefixed(data, index)
            name = raw_name.decode("utf-8", "replace") if raw_name else ""
            el = Element(data_type=token, field_name=name, rec_no=rec_no, is_array=is_array)
            el.is_choice = is_choice
            elements.append(el)
        elif token == SchemaTokenType.MXDDT_START_CHOICE:
            is_choice = True
        elif token == SchemaTokenType.MXDDT_END_CHOICE:
            end_record()
        else:
            done = token == SchemaTokenType.MXDDT_END_SCHEMA
            if token == SchemaTokenType.MXDDT_END_RECORD or done:
                end_record()
            if done:
                break
    return records, index


class _DataReader:
    def __init__(self, data: bytes, records):
        self.data = data
        self.records = records
        self.index = 0

    def _read_record(self, rec_no: int):
        if rec_no < 0 or rec_no >= len(self.records):
            return None
        rec = self.records[rec_no]
        result = {}
        for field in rec.elements:
            result[field.field_name] = self._read_field(field)
        return result

    def _read_field(self, field: Element):
        if field.data_type == DataType.MXDDT_RECORD:
            if field.is_array:
                count, self.index = read_7bit_uint(self.data, self.index)
                if count is None:
                    return []
                return [self._read_record(field.rec_no) for _ in range(count)]
            return self._read_record(field.rec_no)

        if field.is_array:
            count, self.index = read_7bit_uint(self.data, self.index)
            if count is None:
                return []
            return [self._read_primitive(field.data_type) for _ in range(count)]

        return self._read_primitive(field.data_type)

    def _read_primitive(self, data_type: int):
        if self.index >= len(self.data):
            return None
        if data_type == DataType.MXDDT_BOOL:
            val = self.data[self.index] == 1
            self.index += 1
            return val
        if data_type in (DataType.MXDDT_HEX_BYTE_ARRAY, DataType.MXDDT_UTF8_STRING, DataType.MXDDT_ENUM):
            raw, self.index = read_length_prefixed(self.data, self.index)
            if raw is None:
                return None
            if data_type == DataType.MXDDT_HEX_BYTE_ARRAY:
                return raw
            return raw.decode("utf-8", "replace")
        if data_type == DataType.MXDDT_VAR_UINT64:
            val, self.index = read_7bit_uint(self.data, self.index)
            return val
        if data_type == DataType.MXDDT_VAR_INT64:
            val, self.index = read_7bit_int(self.data, self.index)
            return val
        return None


def read_data(data: bytes, index: int, records):
    """读取数据区，返回 (root_dict, new_index)。root 为最后一条记录（约定为根）。"""
    if not records:
        return {}, index
    reader = _DataReader(data, records)
    reader.index = index
    root = records[-1]
    result = {}
    if len(records) == 1 or not root.is_choice:
        for field in root.elements:
            result[field.field_name] = reader._read_field(field)
    else:
        # choice：先读 1 字节序号（1..N，0 表示无）
        if reader.index < len(reader.data):
            no = reader.data[reader.index]
            reader.index += 1
            if 1 <= no <= len(root.elements):
                field = root.elements[no - 1]
                result[field.field_name] = reader._read_field(field)
    return result, reader.index


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def write_schema(records) -> bytes:
    out = bytearray()
    total = len(records)
    for i, rec in enumerate(records):
        if rec.is_choice:
            out.append(SchemaTokenType.MXDDT_START_CHOICE)
        for el in rec.elements:
            dt = el.data_type
            if el.is_array:
                dt |= SchemaTokenType.MXD_ARRAY_TYPE
            out.append(dt & 0xFF)
            if el.data_type == DataType.MXDDT_RECORD:
                out += write_7bit_uint(el.rec_no)
            out += write_length_prefixed(el.field_name.encode("utf-8"))
        if rec.is_choice:
            out.append(SchemaTokenType.MXDDT_END_CHOICE)
        if i < total - 1:
            out.append(SchemaTokenType.MXDDT_END_RECORD)
    out.append(SchemaTokenType.MXDDT_END_SCHEMA)
    return bytes(out)


def write_primitive(out: bytearray, data_type: int, value):
    if data_type == DataType.MXDDT_BOOL:
        out.append(1 if value else 0)
    elif data_type in (DataType.MXDDT_HEX_BYTE_ARRAY, DataType.MXDDT_UTF8_STRING, DataType.MXDDT_ENUM):
        payload = value
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        out += write_length_prefixed(payload or b"")
    elif data_type == DataType.MXDDT_VAR_UINT64:
        out += write_7bit_uint(int(value))
    elif data_type == DataType.MXDDT_VAR_INT64:
        out += write_7bit_int(int(value))

"""生成 MxdDecode 风格的文本报告。"""

import datetime

from .binary import read_7bit_uint, read_length_prefixed, read_tlv
from .schema import DataType, SchemaTokenType

TAG_NAMES = {
    0: "END_HEADER", 1: "FILE_TYPE", 2: "COMPATIBILITY_LEVEL", 3: "_MAJOR_VERSION",
    4: "_MINOR_VERSION", 5: "ENCRYPTION_TYPE", 6: "COMPRESSION_TYPE", 7: "PRIM_SIG_TYPE",
    8: "SEC_SIG_TYPE", 9: "PIN_TYPE", 10: "CONTENT_TYPE", 11: "CONTENT_LENGTH",
    12: "COMP_CONTENT_LENGTH", 13: "PIN_DIGITS", 14: "CUSTOMER", 15: "ORIGINATING_COMPUTER",
    16: "USER_NAME", 17: "INITIAL_CREATION_TIME", 18: "FINAL_MODIFICATION_TIME",
    19: "COMPUTER_UID", 20: "VALID_FROM_TIME", 21: "APP_BASE_ADDRESS",
    22: "APP_ENTRY_POINT", 23: "VERSION", 24: "RSA_PUBLIC_KEY", 25: "ELECTRONICS_VERSION",
    26: "INITIAL_CREATION_TZ", 27: "FINAL_MODIFICATION_TZ", 28: "VALID_FROM_TZ",
    29: "ORIGINAL_FILE_NAME",
}

_TIME_TAGS = {17, 18, 20}
_TZ_TAGS = {26, 27, 28}
_STR_TAGS = {1, 14, 15, 16, 21, 22, 23, 25, 29}
_UINT_TAGS = {11, 12, 19}
_INT_TAGS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 13}

DT_NAMES = {
    DataType.MXDDT_NULL: "NULL", DataType.MXDDT_RECORD: "RECORD",
    DataType.MXDDT_BOOL: "BOOL", DataType.MXDDT_HEX_BYTE_ARRAY: "HEX_BYTE_ARRAY",
    DataType.MXDDT_UTF8_STRING: "UTF8_STRING", DataType.MXDDT_ENUM: "ENUM",
    DataType.MXDDT_VAR_UINT64: "VAR_UINT64", DataType.MXDDT_VAR_INT64: "VAR_INT64",
}


def _fmt_time(value: int) -> str:
    try:
        return datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime(
            "%d %b %Y %H:%M:%S +0000")
    except (OverflowError, OSError, ValueError):
        return str(value)


def _fmt_tz(value: int) -> str:
    # 样本/MxdDecode 均按“分钟”存储时区（如 60 -> +0100）
    sign = "+" if value >= 0 else "-"
    value = abs(value)
    return "%s%02d%02d" % (sign, value // 60, value % 60)


def _hex(data: bytes, limit: int = 64) -> str:
    s = " ".join("%02x" % b for b in data)
    if len(data) > limit:
        s = " ".join("%02x" % b for b in data[:limit]) + " ..."
    return s


def header_items(header_bytes: bytes):
    """返回 [(offset, tag, tag_name, length, value_text), ...]。"""
    items = []
    index = 0
    while index < len(header_bytes):
        start = index
        tag, value, index = read_tlv(header_bytes, index)
        if tag is None:
            break
        name = TAG_NAMES.get(tag, "UNKNOWN_%02x" % tag)
        if tag == 0:
            items.append((start, tag, name, len(value), ""))
            break
        if tag in _TIME_TAGS:
            text = _fmt_time(int.from_bytes(value, "little"))
        elif tag in _TZ_TAGS:
            text = _fmt_tz(int.from_bytes(value, "little", signed=True))
        elif tag in _STR_TAGS:
            text = value.decode("utf-8", "replace")
        elif tag == 24:
            text = _hex(value)
        elif tag in _UINT_TAGS:
            text = str(int.from_bytes(value, "little"))
        elif tag in _INT_TAGS:
            text = str(int.from_bytes(value, "little"))
        else:
            text = _hex(value)
        items.append((start, tag, name, len(value), text))
    return items


def header_lines(header_bytes: bytes):
    lines = ["   Off   Tag  Name                 Length  Value", ""]
    for start, tag, name, length, text in header_items(header_bytes):
        lines.append("%04x  %04x  %-21s%4u  %s" % (start, tag, name, length, text))
    return lines


def schema_lines(decrypted: bytes):
    """输出 schema 定义段落。"""
    lines = []
    index = 0
    rec_no = 0
    size = len(decrypted)
    while index < size:
        start = index
        token = decrypted[index]
        index += 1
        if token < SchemaTokenType.MXDDT_END_RECORD:
            is_array = bool(token & SchemaTokenType.MXD_ARRAY_TYPE)
            base = token & ~SchemaTokenType.MXD_ARRAY_TYPE
            rec_ref = -1
            if base == DataType.MXDDT_RECORD:
                rec_ref, index = read_7bit_uint(decrypted, index)
            raw, index = read_length_prefixed(decrypted, index)
            name = raw.decode("utf-8", "replace") if raw else ""
            if base == DataType.MXDDT_RECORD:
                lines.append("%04x  Rec          %4d  %s%s" %
                             (start, rec_ref, name, "[...]" if is_array else ""))
            else:
                lines.append("%04x  %-12s     %s" % (start, DT_NAMES.get(base, str(base)), name))
        elif token == SchemaTokenType.MXDDT_START_CHOICE:
            lines.append("%04x  start choice" % start)
        elif token == SchemaTokenType.MXDDT_END_CHOICE:
            lines.append("%04x  end choice" % start)
        elif token == SchemaTokenType.MXDDT_END_RECORD:
            lines.append("%04x  end record %d" % (start, rec_no))
            rec_no += 1
        elif token == SchemaTokenType.MXDDT_END_SCHEMA:
            lines.append("%04x  end schema, %d records" % (start, rec_no))
            break
    return lines, index


def data_lines(root: dict):
    lines = []

    def render(value, indent):
        pad = "  " * indent
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    lines.append("%s%s" % (pad, k))
                    lines.append("%s(" % pad)
                    render(v, indent + 1)
                    lines.append("%s)" % pad)
                else:
                    lines.append("%s%-24s = %s" % (pad, k, _val(v)))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    render(item, indent)
                else:
                    lines.append("%s%s" % (pad, _val(item)))

    def _val(v):
        if isinstance(v, bytes):
            return _hex(v)
        if isinstance(v, str):
            return '"%s"' % v
        return str(v)

    render(root, 1)
    return lines


def report(dkl) -> str:
    """生成完整报告文本。"""
    out = []
    out.append("MXD decode (mxdlib)")
    out.append("")
    out.extend(header_lines(dkl.header_bytes))
    out.append("")

    if dkl.decrypted:
        slines, schema_end = schema_lines(dkl.decrypted)
        out.extend(slines)
        out.append("")
        out.extend(data_lines(dkl.root))
        out.append("")

    out.append("--- Trailer ---")
    if dkl.pin_hash is not None:
        out.append("PIN hash        : %s" % _hex(dkl.pin_hash))
    if dkl.primary_signature is not None:
        out.append("Primary sig     : %d bytes" % len(dkl.primary_signature))
    if dkl.secondary_signature is not None:
        out.append("Secondary sig   : %d bytes" % len(dkl.secondary_signature))
    out.append("CRC             : %02x %02x %02x %02x" % tuple(dkl.raw[-4:]))
    out.append("CRC check       : %s" % (dkl.crc_ok,))
    if dkl.pin_ok is not None:
        out.append("PIN check       : %s" % (dkl.pin_ok,))
    if dkl.primary_sig_ok is not None:
        out.append("Primary sig check   : %s" % (dkl.primary_sig_ok,))
    if dkl.secondary_sig_ok is not None:
        out.append("Secondary sig check : %s" % (dkl.secondary_sig_ok,))
    return "\n".join(out)

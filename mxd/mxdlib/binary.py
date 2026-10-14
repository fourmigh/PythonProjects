"""二进制工具：7 bit 变长整数、TLV、字节序。"""


def read_7bit_uint(data: bytes, index: int):
    """读取 7 bit 编码的无符号整数，返回 (value, new_index)，越界返回 (None, index)。"""
    value = 0
    shift = 0
    size = len(data)
    while True:
        if index >= size:
            return None, index
        b = data[index]
        index += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    return value, index


def read_7bit_int(data: bytes, index: int):
    """读取 7 bit 编码的有符号整数，返回 (value, new_index)，越界返回 (None, index)。"""
    value = 0
    shift = 0
    size = len(data)
    while True:
        if index >= size:
            return None, index
        b = data[index]
        index += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            break
    if b & 0x40:
        value |= -1 << shift
    return value, index


def write_7bit_uint(value: int) -> bytes:
    """写出 7 bit 编码的无符号整数。"""
    if value < 0:
        raise ValueError("write_7bit_uint 需要非负整数")
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def write_7bit_int(value: int) -> bytes:
    """写出 7 bit 编码的有符号整数。"""
    out = bytearray()
    negative = value < 0
    while True:
        b = value & 0x7F
        if (value > 63) or (value < -64):
            value >>= 7
            out.append(b | 0x80)
        else:
            if negative:
                b |= 0x40
            out.append(b)
            break
    return bytes(out)


def write_length_prefixed(payload: bytes) -> bytes:
    """7 bit 长度前缀 + 数据。"""
    return write_7bit_uint(len(payload)) + payload


def read_length_prefixed(data: bytes, index: int):
    """读取 7 bit 长度前缀 + 数据，返回 (payload, new_index)，越界返回 (None, index)。"""
    length, index = read_7bit_uint(data, index)
    if length is None:
        return None, index
    payload = data[index:index + length]
    if len(payload) != length:
        return None, index + length
    return payload, index + length


def encode_tlv(tag: int, value: bytes) -> bytes:
    """TLV = 7bit(tag) + 7bit(len) + value。"""
    return write_7bit_uint(tag) + write_7bit_uint(len(value)) + value


def read_tlv(data: bytes, index: int):
    """读取一个 TLV，返回 (tag, value, new_index)，越界返回 (None, None, index)。"""
    tag, index = read_7bit_uint(data, index)
    if tag is None:
        return None, None, index
    length, index = read_7bit_uint(data, index)
    if length is None:
        return None, None, index
    value = data[index:index + length]
    if len(value) != length:
        return None, None, index + length
    return tag, value, index + length


def int_to_le(value: int, size: int, signed: bool = False) -> bytes:
    return int(value).to_bytes(size, "little", signed=signed)


def le_to_int(value: bytes, signed: bool = False) -> int:
    if not value:
        return 0
    return int.from_bytes(value, "little", signed=signed)

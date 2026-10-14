"""Dallas Key 编号（18 位）与 DKL 内部 KeyID（12 位）的相互转换。

来自 DKLManager.dallasKey2DKLKey：
    keyID = 0x0136D9AB1D0000A8        （十进制 87496571729477800）
    小端字节          : A8 00 00 1D AB D9 36 01
    去掉第 1 字节(校验和): 00 00 1D AB D9 36 01
    按大端解释         : 0x1DABD93601 = 127437190657

被清零的首字节（小端最低字节）是 Dallas/Maxim 1-Wire CRC8：
    crc8 = Dallas-CRC8(poly 0x8C reflected, 对剩余 7 字节逆序计算)
因此 12 位 KeyID 可以精确还原回 18 位物理编号：

    core = dkl_key.to_bytes(7, "big")
    raw  = int.from_bytes(bytes([dallas_crc8(core[::-1])]) + core, "little")
"""


def dallas_crc8(data: bytes) -> int:
    """Dallas/Maxim 1-Wire CRC8（反射，多项式 0x8C = x^8+x^5+x^4+1）。"""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 1 else crc >> 1
    return crc & 0xFF


def dallas_key_to_dkl_key(key_id: int) -> int:
    """物理 Dallas Key 编号（18 位，64bit）-> DKL 中的 KeyID（12 位）。"""
    key_id &= 0xFFFFFFFFFFFFFFFF
    little = key_id.to_bytes(8, "little")
    little = bytes([0]) + little[1:]          # 清零校验和(CRC8)字节
    return int.from_bytes(little, "big")


def dkl_key_to_dallas_key(dkl_key: int) -> int:
    """DKL 中的 KeyID（12 位）-> 物理 Dallas Key 编号（18 位），自动补 CRC8。"""
    core = (dkl_key & ((1 << 56) - 1)).to_bytes(7, "big")
    crc = dallas_crc8(core[::-1])
    return int.from_bytes(bytes([crc]) + core, "little")


def is_valid_dallas_key(key_id: int) -> bool:
    """校验 18 位 Dallas 编号的首字节是否为合法的 Dallas CRC8。"""
    key_id &= 0xFFFFFFFFFFFFFFFF
    little = key_id.to_bytes(8, "little")
    return little[0] == dallas_crc8(little[1:][::-1])

"""DKL 瑙ｆ瀽 / 鐢熸垚鐨勫洖褰掓祴璇曪紙鍩轰簬 doc/sample 涓殑鏍锋湰锛夈€?
杩愯锛歱ython -m pytest tests  锛堟垨鐩存帴 python tests/test_dkl.py锛?鏍锋湰涓嶅瓨鍦ㄦ椂鑷姩璺宠繃銆?"""

import hashlib
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mxdlib import DKL, MXDError, rsa_sign  # noqa: E402
from mxdlib.dkl import build_dkl_schema, build_data  # noqa: E402
from mxdlib.mxd import parse_header  # noqa: E402
from mxdlib.schema import write_schema  # noqa: E402

SAMPLE = os.path.join(ROOT, "doc", "sample")
SIGN = os.path.join(SAMPLE, "signing_test")


def _need(path):
    return unittest.skipUnless(os.path.exists(path), "缂哄皯鏍锋湰 %s" % path)


def _read(path):
    with open(path, "rb") as f:
        return f.read()


class DKLParseTests(unittest.TestCase):
    @_need(os.path.join(SAMPLE, "DKL", "devkeys.dkl"))
    def test_parse_devkeys(self):
        dkl, err = DKL.from_file(os.path.join(SAMPLE, "DKL", "devkeys.dkl"))
        self.assertEqual(err, MXDError.Success)
        self.assertTrue(dkl.crc_ok)
        self.assertTrue(dkl.primary_sig_ok)
        self.assertEqual([g.name for g in dkl.key_groups],
                         ["Cash Collectors", "Service Engineers", "Service Keys"])
        self.assertEqual(dkl.key_groups[0].keys[0].key_id, 97514248)

    @_need(os.path.join(SIGN, "dallas_sec.dkl"))
    def test_parse_dual_signature(self):
        pub = rsa_sign.public_der(rsa_sign.load_private_key(
            _read(os.path.join(SIGN, "primary.key"))))
        dkl, err = DKL.from_file(os.path.join(SIGN, "dallas_sec.dkl"), rsa_public_key=pub)
        self.assertEqual(err, MXDError.Success)
        self.assertTrue(dkl.primary_sig_ok)
        self.assertTrue(dkl.secondary_sig_ok)

    @_need(os.path.join(SAMPLE, "DKL", "china", "CHINA1.DKL"))
    def test_parse_obfuscated(self):
        dkl, err = DKL.from_file(os.path.join(SAMPLE, "DKL", "china", "CHINA1.DKL"), from_server=True)
        self.assertEqual(err, MXDError.Success)
        self.assertTrue(dkl.header.is_obfuscated())
        self.assertEqual(dkl.key_groups[0].name, "ENGINEERS")

    @_need(os.path.join(SIGN, "dallas_prim.dkl"))
    def test_region_byte_exact_leaf(self):
        path = os.path.join(SIGN, "dallas_prim.dkl")
        raw = _read(path)
        _, hend = parse_header(raw)
        region = raw[hend:len(raw) - 128 - 4]
        dkl, _ = DKL.from_file(path)
        rebuilt = write_schema(build_dkl_schema("leaf")) + build_data(dkl.key_groups)
        self.assertEqual(rebuilt, region)


class DKLBuildTests(unittest.TestCase):
    @_need(os.path.join(SIGN, "primary.key"))
    def test_full_reproduce_signed(self):
        for name, style, sec in (("dallas_prim.dkl", "leaf", False),
                                 ("dallas_sec.dkl", "leaf", True)):
            path = os.path.join(SIGN, name)
            if not os.path.exists(path):
                continue
            raw = _read(path)
            header, _ = parse_header(raw)
            dkl, _ = DKL.from_file(path)
            prim = _read(os.path.join(SIGN, "primary.key"))
            secondary = _read(os.path.join(SIGN, "secondary.key")) if sec else None
            out = dkl.build(header=header, groups=dkl.key_groups, obfuscate=False,
                            pin=None, primary_key=prim, secondary_key=secondary,
                            schema_style=style)
            self.assertEqual(out, raw, name)

    def test_timezone_multibyte(self):
        # 时区按分钟存储，编码为最小宽度有符号小端整数
        from mxdlib import KeyEntry, KeyGroup
        from mxdlib.mxd import Header, parse_header
        groups = [KeyGroup("G", "LOCK", [KeyEntry("K", 1)], [])]
        for tz in (60, 127, 128, 480, -480, 840):
            header = Header(file_type="dkl", valid_from_time=1700000000,
                            initial_creation_time=1700000000, initial_creation_time_zone=tz)
            data = DKL().build(header=header, groups=groups)
            parsed, _ = parse_header(data)
            self.assertEqual(parsed.initial_creation_time_zone, tz)

    @_need(os.path.join(SIGN, "primary.key"))
    def test_roundtrip_protected(self):
        from mxdlib import AccessTime, HourMinute, KeyEntry, KeyGroup, Time
        from mxdlib.mxd import Header
        prim = _read(os.path.join(SIGN, "primary.key"))
        sec = _read(os.path.join(SIGN, "secondary.key"))
        groups = [KeyGroup("G1", "VAULT", [KeyEntry("K1", 97514248)],
                           [AccessTime(127, [Time(HourMinute(0, 0), HourMinute(23, 59))])])]
        header = Header(file_type="dkl", customer="C", origin="O", user_name="U",
                        initial_creation_time=1700000000, final_modification_time=1700000000,
                        valid_from_time=1700000000)
        data = DKL().build(header=header, groups=groups, obfuscate=True, pin="1234",
                           primary_key=prim, secondary_key=sec)
        pub = rsa_sign.public_der(rsa_sign.load_private_key(prim))
        dkl = DKL()
        err = dkl.parse(data, rsa_public_key=pub, pin="1234")
        self.assertEqual(err, MXDError.Success)
        self.assertTrue(dkl.crc_ok and dkl.pin_ok and dkl.primary_sig_ok and dkl.secondary_sig_ok)
        self.assertEqual(dkl.key_groups[0].keys[0].key_id, 97514248)


class KeyUpdateTests(unittest.TestCase):
    def test_key_update_generation(self):
        """旧密钥主签名 + 新密钥次签名：头公钥=新公钥，主/次签名均可验证。"""
        from mxdlib import AccessTime, HourMinute, KeyEntry, KeyGroup, Time
        from mxdlib.mxd import Header
        old_priv, _ = rsa_sign.generate_keypair(1024)
        new_priv, _ = rsa_sign.generate_keypair(1024)
        groups = [KeyGroup("G", "VAULT", [KeyEntry("K", 12345)],
                           [AccessTime(127, [Time(HourMinute(0, 0), HourMinute(23, 59))])])]
        header = Header(file_type="dkl", customer="UPD", origin="PC", user_name="eng",
                        initial_creation_time=1700000000, final_modification_time=1700000000,
                        valid_from_time=1700000000)
        data = DKL().build(header=header, groups=groups, obfuscate=True, pin="1234",
                           primary_key=old_priv, secondary_key=new_priv)

        old_pub = rsa_sign.public_der(rsa_sign.load_private_key(old_priv))
        new_pub = rsa_sign.public_der(rsa_sign.load_private_key(new_priv))
        dkl = DKL()
        err = dkl.parse(data, rsa_public_key=old_pub, pin="1234")
        self.assertEqual(err, MXDError.Success)
        self.assertTrue(dkl.primary_sig_ok)
        self.assertTrue(dkl.secondary_sig_ok)
        self.assertEqual(dkl.header.rsa_public_key, new_pub)

    def test_secondary_requires_primary(self):
        from mxdlib import KeyGroup
        from mxdlib.mxd import Header
        _, new_priv = rsa_sign.generate_keypair(1024)
        with self.assertRaises(ValueError):
            DKL().build(header=Header(file_type="dkl"), groups=[KeyGroup("G", "LOCK")],
                        primary_key=None, secondary_key=new_priv)


class DallasTests(unittest.TestCase):
    def test_conversion(self):
        from mxdlib.dallas import dallas_key_to_dkl_key, dkl_key_to_dallas_key
        self.assertEqual(dallas_key_to_dkl_key(0x0136D9AB1D0000A8), 127437190657)
        # 12 位 <-> 18 位精确往返（首字节由 Dallas CRC8 还原）
        for raw in (87496571729477800, 121938773469560946, 102365666853519589):
            self.assertEqual(dkl_key_to_dallas_key(dallas_key_to_dkl_key(raw)), raw)

    def test_china3u_lookup(self):
        from mxdlib.dallas import dallas_key_to_dkl_key
        path = os.path.join(ROOT, "tests", "CHINA3U.DKL")
        if not os.path.exists(path):
            self.skipTest("缺少 tests/CHINA3U.DKL")
        dkl, err = DKL.from_file(path, from_server=True)
        self.assertEqual(err, MXDError.Success)
        ids = {k.key_id for g in dkl.key_groups for k in g.keys}
        self.assertIn(dallas_key_to_dkl_key(121938773469560946), ids)   # LOCK
        self.assertIn(dallas_key_to_dkl_key(102365666853519589), ids)   # VAULT


if __name__ == "__main__":
    unittest.main(verbosity=2)


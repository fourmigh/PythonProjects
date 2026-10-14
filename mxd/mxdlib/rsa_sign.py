"""RSA 签名/验签（PKCS#1 v1.5 + SHA-1）。

文档描述为 "RSA private key encrypted SHA-1 hash with no padding"，
实验确认实际为标准 PKCS#1 v1.5 SHA-1 签名。
公钥在文件头中以 PKCS#1 RSAPublicKey DER（1024 位为 140 字节）保存。
"""

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA1
from Crypto.Signature import pkcs1_15
from Crypto.Util.asn1 import DerInteger, DerSequence


def load_private_key(pem: bytes):
    if isinstance(pem, str):
        pem = pem.encode()
    return RSA.import_key(pem)


def public_der(key: RSA.RsaKey) -> bytes:
    """导出 PKCS#1 RSAPublicKey DER（与文件头中的格式一致）。"""
    pub = key.publickey()
    return DerSequence([DerInteger(pub.n), DerInteger(pub.e)]).encode()


def sign(data: bytes, private_key) -> bytes:
    key = private_key if isinstance(private_key, RSA.RsaKey) else load_private_key(private_key)
    digest = SHA1.new(data)
    return pkcs1_15.new(key).sign(digest)


def verify(data: bytes, signature: bytes, public_key) -> bool:
    try:
        key = public_key if isinstance(public_key, RSA.RsaKey) else RSA.import_key(public_key)
        digest = SHA1.new(data)
        pkcs1_15.new(key).verify(digest, signature)
        return True
    except (ValueError, TypeError, IndexError):
        return False


def generate_keypair(bits: int = 1024):
    """生成 RSA 密钥对，返回 (private_pem: bytes, public_pem: bytes)。

    MXD 要求 1024 位（公钥 PKCS#1 DER 为 140 字节，签名 128 字节）。
    """
    key = RSA.generate(bits)
    private_pem = key.export_key(format="PEM", pkcs=1)
    public_pem = key.publickey().export_key(format="PEM")
    return private_pem, public_pem


def fingerprint_der(pub_der: bytes) -> str:
    """公钥 DER 的 SHA-1 指纹（大写十六进制）。"""
    return SHA1.new(pub_der).hexdigest().upper()

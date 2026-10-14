# MXD / DKL 工具（Python 重写）

把 `doc/android` 中 Kotlin 编写的 MXD 解析逻辑用 Python 重写，并提供可视化界面。
当前版本实现了 **DKL（Dallas Key List）文件的解析与生成**，核心算法均依据
`doc/MXD File Format.doc`、Kotlin 源码与 `doc/sample` 样本实验确认。

## 目录结构

```
mxd/
├── mxdlib/                 核心库
│   ├── binary.py           7-bit 变长整数、TLV
│   ├── crc32.py            CustomerCRC32（~zlib.crc32，小端）
│   ├── xtea.py             XTEA（TEAN）加解密
│   ├── schema.py           Tag / DataType / SchemaToken / schema&data 解析与序列化
│   ├── mxd.py              Header 解析 / 构建
│   ├── rsa_sign.py         RSA PKCS#1 v1.5 + SHA-1 签名 / 验签
│   ├── dkl.py              DKL 模型与 parse / build
│   ├── dallas.py           Dallas Key 编号 <-> DKL KeyID
│   └── report.py           MxdDecode 风格文本报告
├── mxd_gui.py              Tkinter 可视化界面
├── tests/test_dkl.py       回归测试
└── requirements.txt
```

## 环境与依赖

- Python 3.8+（开发使用 3.14）
- `pycryptodome`（RSA 签名）
- GUI 使用 Python 内置的 `tkinter`，无需额外安装

```powershell
pip install -r requirements.txt
python mxd_gui.py
```

## 可视化界面

- **解析**：选择 `.dkl` → 可选填写 PIN、机器公钥（PEM/DER）、勾选“来自服务器(跳过校验)”
  → 显示头部字段（含 偏移 / **Tag 十六进制** / 长度 / 值）、密钥组树、文本报告、十六进制。
  解析成功后，头部字段与密钥组会**自动回填到生成页**。
- **生成**：头部表单**覆盖 Header 全部字段**，每个字段标签带 `[Tag]` 编号（如 `[000e] 客户`），
  可与解析页/MxdDecode 的 Tag 一一对应；表单区域支持**鼠标滚轮滚动**。（兼容级别、主/次版本、机器唯一ID、应用基址/入口、
  原始文件名、内容长度等），都有默认示例值；`文件类型`为文档定义类型的只读下拉（写入时小写），
  `电子版本`为 AURA_1/AURA_2 下拉，文本字段仅允许 ASCII 可见字符并限长，`版本`校验 `xx.yy[b]`。
  **三个时间为“日期时间 + 时区”选择控件**：选择时间的同时从常用时区（含城市/名称）下拉里选时区，
  时间按所选时区的当地壁钟理解、存盘换算为 UTC，无时区则按 UTC 处理；时区 Tag 在“自动字段”区**只读展示**。
  由生成选项/密钥决定的字段（混淆/压缩/签名类型/PIN类型/内容类型/RSA公钥）同样在“自动字段”区**只读展示**。
  编辑密钥组 / 钥匙 / 访问时间；可选 XTEA 混淆、PIN、主/次私钥（PEM）；选择 schema 风格；
  可从解析结果导入密钥组 / 头部模板；输出 `.dkl`。
  > 解析后所有头部字段会回填，**不改动直接生成即可逐字节还原** `dallas_prim.dkl`/`dallas_sec.dkl` 等样本。
  > 注：样本/MxdDecode 中时区按“分钟”存储（如 60 = +0100），本工具按此解释以保证往返一致；
  > 编码为**最小宽度的有符号小端整数**（±2h07m 内 1 字节，如 +0800=480 用 2 字节），兼容 ±14:00。
- **密钥更新**：向导式——从旧 DKL 导入内容、指定旧(主)/新(次)私钥、一键生成覆盖文件，
  并自动做头公钥指纹与签名的自检。
- **工具**：`DallasKey` ↔ `KeyID` 互转（KeyID→DallasKey 由 Dallas CRC8 自动补校验和字节，可精确还原）。
- **术语统一**：用户输入的一律叫 `DallasKey`，写入文件存储的叫 `KeyID`（`KeyID = dallas_key_to_dkl_key(DallasKey)`）。
  密钥组树“详情”同时显示 `KeyID` 与 `DallasKey`；编辑选中项里的 `DallasKey` 输入后转换为 `KeyID` 存储。

## 库用法

### 解析

```python
from mxdlib import DKL, MXDError
from mxdlib import rsa_sign

dkl, err = DKL.from_file(
    "devkeys.dkl",
    # 单签名文件可省略；双签名文件若需校验主签名，传入机器公钥(PKCS#1 DER 或 PEM)
    rsa_public_key=None,
    pin=None,            # PIN 保护文件必填
    from_server=False,   # True 则跳过 PIN / 签名校验
)
assert err == MXDError.Success
for g in dkl.key_groups:
    print(g.name, g.type, [(k.name, k.key_id) for k in g.keys])
```

### 生成

```python
from mxdlib import DKL, KeyGroup, KeyEntry, AccessTime, Time, HourMinute
from mxdlib.mxd import Header

groups = [
    KeyGroup("Cash Collectors", "VAULT",
             [KeyEntry("Key1", 97514248)],
             [AccessTime(127, [Time(HourMinute(0, 0), HourMinute(23, 59))])]),
]
header = Header(file_type="dkl", customer="DEMO", origin="PC", user_name="eng",
                initial_creation_time=1700000000,
                final_modification_time=1700000000,
                valid_from_time=1700000000)

data = DKL().build(
    header=header, groups=groups,
    obfuscate=True,                # XTEA 混淆
    pin="1234",                    # PIN 保护（可选）
    primary_key=open("primary.key", "rb").read(),    # 主签名私钥（可选）
    secondary_key=None,            # 次签名私钥（可选）
    schema_style="leaf",           # "leaf" 匹配 signing_test， "root" 匹配 SALE2017/CHINA1
)
open("out.dkl", "wb").write(data)
```

## 密钥更新（用新密钥覆盖旧 DKL）

机器当前持有“旧密钥”。要换成新密钥时，生成一个 DKL：用**旧密钥做主签名**、
**新密钥做次签名**，文件头保存**新密钥公钥**。机器流程是先用旧公钥验主签名
（确认文件可信），再用头内新公钥验次签名，通过后把新公钥写入 PCB。

- 对应样本：`doc/sample/signing_test/dallas_sec.dkl`（`dallas_prim.dkl` 为仅主签名的首次配发）。
- **界面**：切换到「密钥更新」标签页 → 选旧 DKL 点“从旧 DKL 导入内容” →
  填“当前机器私钥（旧）”与“新私钥”（可用“生成新密钥对…”生成 1024 位密钥）→
  设选项 → “一键生成覆盖文件”，下方会显示头公钥指纹与主/次签名自检结果。
- **库**：

```python
data = DKL().build(
    header=header, groups=groups,
    obfuscate=True, pin="1234",
    primary_key=open("old.key", "rb").read(),   # 机器当前/旧密钥 -> 主签名
    secondary_key=open("new.key", "rb").read(),  # 新密钥 -> 次签名，头公钥取它
    schema_style="leaf",
)
```

注意：次签名必须伴随主签名，只填 `secondary_key` 会报错。
若要复用旧 DKL 的内容，解析后用 `dkl.key_groups` 与 `dkl.header` 作为输入即可。

## DKL 文件格式速查

```
Header + Schema + Data + [加密PIN(20)] + [主签名(128)] + [次签名(128)] + CRC(4)
```

| 项目 | 说明 |
|---|---|
| Header | 7-bit tag/len 的 TLV，tag 0 结束；字段见 `schema.Tag` |
| CRC | `~zlib.crc32(body)`，小端 4 字节 |
| 混淆 | XTEA（32 轮，小端），密钥 = `SHA1(Header)[:16]`；块对齐：先写 `0xFF`，再补 `0x00` |
| PIN | `SHA1(pin_ascii + Header + 加密区)[:20]` |
| 主签名 | `RSA_PKCS1v15_SHA1(Header + 加密区 + PIN)` |
| 次签名 | `RSA_PKCS1v15_SHA1(Header + 加密区 + PIN + 主签名)` |
| 公钥 | 文件头保存 PKCS#1 RSAPublicKey DER（1024 位 = 140 字节）；双签名时保存次签名（文件）公钥 |

### DKL 数据模型

```
KeyGroupsList -> KeyGroup[] {
    Name, Type(VAULT/LOCK/SERVICE),
    KeyList -> KeyEntry[] { Name, KeyID },
    AccessTimeList -> AccessTime[] { DayOfWeekMask, Time[] { StartTime{Hour,Minute}, EndTime{Hour,Minute} } }
}
```

## 与 Android/Kotlin 模块的对应

| Kotlin | Python |
|---|---|
| `mxd/bean/MXDFile.kt`、`ReadSchema.kt`、`ReadData.kt` | `mxdlib/schema.py` |
| `mxd/bean/Header.kt`、`Tag.kt`、`DataType.kt` | `mxdlib/mxd.py`、`mxdlib/schema.py` |
| `mxd_file/server/DKL.kt` | `mxdlib/dkl.py` |
| `mxd_file_dkl/DKLManager.kt` | `mxdlib/dallas.py` |
| `library.crc.CustomerCRC32` | `mxdlib/crc32.py` |
| `library.xtea.XTEACSharp`、样本 `tean.cs` | `mxdlib/xtea.py` |
| `library.rsa.RSAUtils` / `RSAKey` | `mxdlib/rsa_sign.py` |

## 测试

```powershell
python -m unittest discover -s tests -v
```

回归内容：解析 `devkeys.dkl`、双签名 `dallas_sec.dkl`、混淆 `CHINA1.DKL`；
schema/data 与样本逐字节一致；`dallas_prim.dkl` / `dallas_sec.dkl` 的**整文件逐字节重建**；
混淆+PIN+双签名的生成/回读往返。

## 说明

- `doc/MxdDecode.exe` 为 Debug 构建，依赖调试版 CRT，当前环境无法运行，仅作参考。
- 现有样本中存在两种等价 schema 排版（叶节点在前 / 根记录在前），`build(schema_style=...)`
  可分别复现。
- 后续如需支持 BOC/BOR/STF/ELG/SIN/DIR/TRF，可复用 `mxdlib/schema.py` 与 `mxdlib/mxd.py`。

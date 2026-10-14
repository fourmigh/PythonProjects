"""DKL 文件解析 / 生成 可视化工具（Tkinter）。

运行：python mxd_gui.py
"""

import calendar
import datetime
import hashlib
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mxdlib import DKL, MXDError, KeyEntry, KeyGroup, AccessTime, Time, HourMinute
from mxdlib import report, rsa_sign
from mxdlib.dallas import dallas_key_to_dkl_key, dkl_key_to_dallas_key
from mxdlib.mxd import Header, parse_header

DAY_NAMES = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]

# 文档/Kotlin FileType 定义的文件类型（显示用大写，写入时转小写与样本一致）
FILE_TYPES = ["AP2", "APP", "BOC", "BOR", "CFG", "DKL", "ELG", "HTL", "STF", "TRF", "DIR", "SIN"]
ELECTRONICS_VERSIONS = ["AURA_1", "AURA_2"]

# 常用时区（名称, 相对 UTC 的分钟数）；首项表示“不写时区 Tag”
TZ_OPTIONS = [
    ("(不写时区)", None),
    ("UTC-12:00 国际日期变更线西", -720),
    ("UTC-11:00 萨摩亚", -660),
    ("UTC-10:00 夏威夷", -600),
    ("UTC-09:00 阿拉斯加", -540),
    ("UTC-08:00 洛杉矶/太平洋时间", -480),
    ("UTC-07:00 丹佛/山地时间", -420),
    ("UTC-06:00 芝加哥/中部时间", -360),
    ("UTC-05:00 纽约/东部时间", -300),
    ("UTC-04:00 亚特兰大", -240),
    ("UTC-03:30 纽芬兰", -210),
    ("UTC-03:00 圣保罗", -180),
    ("UTC-02:00 费尔南多", -120),
    ("UTC-01:00 亚速尔", -60),
    ("UTC+00:00 伦敦/UTC", 0),
    ("UTC+01:00 巴黎/柏林", 60),
    ("UTC+02:00 开罗/雅典", 120),
    ("UTC+03:00 莫斯科/利雅得", 180),
    ("UTC+03:30 德黑兰", 210),
    ("UTC+04:00 迪拜", 240),
    ("UTC+04:30 喀布尔", 270),
    ("UTC+05:00 卡拉奇", 300),
    ("UTC+05:30 孟买/新德里", 330),
    ("UTC+05:45 加德满都", 345),
    ("UTC+06:00 达卡", 360),
    ("UTC+06:30 仰光", 390),
    ("UTC+07:00 曼谷/雅加达", 420),
    ("UTC+08:00 北京/新加坡", 480),
    ("UTC+08:45 尤克拉", 525),
    ("UTC+09:00 东京/首尔", 540),
    ("UTC+09:30 阿德莱德", 570),
    ("UTC+10:00 悉尼", 600),
    ("UTC+10:30 豪勋爵岛", 630),
    ("UTC+11:00 所罗门群岛", 660),
    ("UTC+12:00 奥克兰", 720),
    ("UTC+12:45 查塔姆", 765),
    ("UTC+13:00 汤加", 780),
    ("UTC+14:00 基里巴斯", 840),
]
TZ_FIELD_KEYS = ("initial_creation_time", "final_modification_time", "valid_from_time")
TZ_TAG_KEY = {
    "initial_creation_time": "initial_creation_time_zone",
    "final_modification_time": "final_modification_time_zone",
    "valid_from_time": "valid_from_time_zone",
}

# 生成页头部表单：覆盖 Header 全部可编辑字段
#   (key, 标签, Tag编号, 控件类型, 参数, 默认值)
#   控件类型：combo / combo_opt / spin / uint / ascii / version / tz / datetime
HEADER_FIELDS = [
    ("file_type", "文件类型", 1, "combo_opt", FILE_TYPES, "DKL"),
    ("compatibility_level", "兼容级别", 2, "spin", (0, 255), "0"),
    ("major_version", "主版本(废弃)", 3, "uint", 4, "0"),
    ("minor_version", "次版本(废弃)", 4, "uint", 4, "0"),
    ("customer", "客户", 14, "ascii", 32, "DEMO CUSTOMER"),
    ("origin", "来源计算机", 15, "ascii", 20, "PCWM00001"),
    ("user_name", "用户名", 16, "ascii", 20, "engineer"),
    ("initial_creation_time", "初始创建时间", 17, "datetime", None, "NOW"),
    ("final_modification_time", "最终修改时间", 18, "datetime", None, "NOW"),
    ("valid_from_time", "生效时间", 20, "datetime", None, "NOW"),
    ("machine_unique_id", "机器唯一ID", 19, "uint", 20, "0"),
    ("application_base_address", "应用基址", 21, "ascii", 32, ""),
    ("application_entry_point", "应用入口点", 22, "ascii", 32, ""),
    ("version", "版本", 23, "version", 8, "1.00"),
    ("electronics_version", "电子版本", 25, "combo_opt", ELECTRONICS_VERSIONS, "AURA_1"),
    ("pin_digits", "PIN 位数", 13, "spin", (1, 8), "4"),
    ("original_file_name", "原始文件名", 29, "ascii", 64, ""),
    ("content_length", "内容长度", 11, "uint", 10, ""),
    ("compressed_content_length", "压缩内容长度", 12, "uint", 10, ""),
]

# 由生成选项/密钥决定，仅只读展示。(key, 标签, Tag编号)
AUTO_FIELDS = [
    ("obfuscation_type", "混淆类型", 5),
    ("compression_type", "压缩类型", 6),
    ("primary_signature_type", "主签名类型", 7),
    ("secondary_signature_type", "次签名类型", 8),
    ("pin_type", "PIN 类型", 9),
    ("content_type", "内容类型", 10),
    ("rsa_public_key", "RSA 公钥", 24),
]

# 时区（由时间选择器决定，只读展示）。(key, 标签, Tag编号)
TZ_AUTO = [
    ("initial_creation_time_zone", "创建时区", 26),
    ("final_modification_time_zone", "修改时区", 27),
    ("valid_from_time_zone", "生效时区", 28),
]

_ASCII_ONLY = "仅允许 ASCII 可见字符(0x20-0x7E)"


def _is_ascii_printable(text):
    return all(0x20 <= ord(c) <= 0x7E for c in text)


def _valid_version(text):
    import re
    return re.fullmatch(r"\d{1,2}\.\d{2}[A-Za-z]?", text or "") is not None


def _ascii_validator(maxlen, pattern_checker=None):
    """返回可用于 Entry(validate='key') 的校验函数。"""
    def check(proposed):
        if len(proposed) > maxlen or not _is_ascii_printable(proposed):
            return False
        if proposed == "" or pattern_checker is None:
            return True
        return pattern_checker(proposed)
    return check


def _int_validator(maxlen=20):
    def check(proposed):
        if len(proposed) > maxlen:
            return False
        return proposed == "" or all(c.isdigit() or c.lower() in "abcdefx" for c in proposed)
    return check


def _dallas_validator(max_dec=20):
    """KeyID(18位 Dallas) 输入限制：十进制 ≤ 2^64-1，或 0x + ≤16 位十六进制。"""
    def check(proposed):
        if proposed == "":
            return True
        if proposed[:2].lower() == "0x":
            body = proposed[2:]
            return 1 <= len(body) <= 16 and all(c in "0123456789abcdefABCDEF" for c in body)
        if not proposed.isdigit() or len(proposed) > max_dec:
            return False
        return int(proposed) <= 0xFFFFFFFFFFFFFFFF
    return check


def _mask_validator(maxlen=6):
    def check(proposed):
        if len(proposed) > maxlen:
            return False
        body = proposed[1:] if proposed.startswith("-") else proposed
        return body == "" or body.isdigit()
    return check


def _digits_only(text):
    """仅数字（非空由上层校验器处理）。"""
    return text.isdigit()


def _tz_validator(text):
    """时区 shhmm：可选正负号 + 最多 4 位数字，且 hh<=14、mm<60。"""
    if text and text[0] in "+-":
        text = text[1:]
    if not text.isdigit() or len(text) > 4:
        return False
    digits = text.zfill(4)
    return int(digits[:-2]) <= 14 and int(digits[-2:]) < 60


def epoch_to_str(value):
    if value is None:
        return ""
    try:
        return datetime.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")
    except (OverflowError, OSError, ValueError):
        return str(value)


def str_to_epoch(text):
    text = (text or "").strip()
    if not text:
        return None
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.datetime.strptime(text, fmt).timestamp())
        except ValueError:
            continue
    raise ValueError("无法解析时间: %r（可用时间戳或 YYYY-MM-DD HH:MM:SS）" % text)


def _tz_to_str(value):
    """时区分钟数 -> '+hhmm' / '-hhmm'（样本/MxdDecode 均按分钟存储，如 60 -> +0100）。"""
    value = int(value)
    sign = "+" if value >= 0 else "-"
    v = abs(value)
    return "%s%02d%02d" % (sign, v // 60, v % 60)


def _tz_from_str(text):
    """'+hhmm' / '-hhmm' -> 时区分钟数；空串返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    sign = -1 if text[0] == "-" else 1
    if text[0] in "+-":
        text = text[1:]
    digits = text.zfill(4)
    hh = int(digits[:-2]) if len(digits) > 2 else 0
    mm = int(digits[-2:])
    return sign * (hh * 60 + mm)


def _tz_label(minutes):
    """时区分钟数 -> 下拉项标签（含名称）。"""
    for label, m in TZ_OPTIONS:
        if m == minutes:
            return label
    if minutes is None:
        return TZ_OPTIONS[0][0]
    sign = "+" if minutes >= 0 else "-"
    v = abs(int(minutes))
    return "UTC%s%02d:%02d" % (sign, v // 60, v % 60)


def _tz_minutes_from_label(label):
    for text, m in TZ_OPTIONS:
        if text == label:
            return m
    return None


def _epoch_to_wall(epoch, tz_minutes):
    """绝对时间(epoch) -> 指定时区的壁钟字符串（tz 为空视作 UTC）。"""
    dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(
        seconds=int(epoch) + (tz_minutes or 0) * 60)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _wall_to_epoch(text, tz_minutes):
    """指定时区的壁钟字符串 -> 绝对时间(epoch)；空串返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    dt = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    return calendar.timegm(dt.timetuple()) - (tz_minutes or 0) * 60


def mask_to_days(mask):
    return ",".join(DAY_NAMES[i] for i in range(7) if mask & (1 << i)) or "-"


def hex_dump(data):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexs = " ".join("%02x" % b for b in chunk).ljust(47)
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append("%08x  %s  %s" % (off, hexs, asci))
    return "\n".join(lines)


def _clone_groups(groups):
    out = []
    for g in groups:
        out.append(KeyGroup(
            name=g.name, type=g.type,
            keys=[KeyEntry(k.name, k.key_id) for k in g.keys],
            access_times=[AccessTime(a.day_of_week_mask,
                                     [Time(HourMinute(t.start.hour, t.start.minute),
                                           HourMinute(t.end.hour, t.end.minute)) for t in a.times])
                          for a in g.access_times],
        ))
    return out


class ScrollFrame(ttk.Frame):
    """带垂直滚动条的容器（支持鼠标滚轮）。"""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        # 滚轮：全局监听，仅当鼠标位于本容器内时滚动
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._on_mousewheel, add="+")

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _contains(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_mousewheel(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, AttributeError):
            widget = None
        if not self._contains(widget):
            return
        num = getattr(event, "num", None)
        if num == 4:
            delta = 1
        elif num == 5:
            delta = -1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MXD / DKL 工具")
        self.geometry("1120x760")
        self.minsize(1000, 660)
        self.parsed = None
        self.groups = []
        self.current_group = None
        self.current_key = None

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_parse = ttk.Frame(nb)
        self.tab_gen = ttk.Frame(nb)
        self.tab_update = ttk.Frame(nb)
        self.tab_tools = ttk.Frame(nb)
        nb.add(self.tab_parse, text="解析")
        nb.add(self.tab_gen, text="生成")
        nb.add(self.tab_update, text="密钥更新")
        nb.add(self.tab_tools, text="工具")

        self._build_parse()
        self._build_generate()
        self._build_update()
        self._build_tools()

    # ==================================================================
    # 解析
    # ==================================================================
    def _build_parse(self):
        top = ttk.LabelFrame(self.tab_parse, text="输入")
        top.pack(fill="x", padx=6, pady=6)

        self.p_file = tk.StringVar()
        self.p_pin = tk.StringVar()
        self.p_pub = tk.StringVar()
        self.p_server = tk.BooleanVar(value=False)

        r = ttk.Frame(top); r.pack(fill="x", padx=4, pady=2)
        ttk.Label(r, text="DKL 文件", width=12).pack(side="left")
        ttk.Entry(r, textvariable=self.p_file).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="浏览", command=self._pick_parse_file).pack(side="left", padx=4)

        r = ttk.Frame(top); r.pack(fill="x", padx=4, pady=2)
        ttk.Label(r, text="PIN", width=12).pack(side="left")
        ttk.Entry(r, textvariable=self.p_pin, width=16).pack(side="left")
        ttk.Label(r, text="  机器公钥(PEM/DER)").pack(side="left")
        ttk.Entry(r, textvariable=self.p_pub).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="浏览", command=self._pick_pub).pack(side="left", padx=4)
        ttk.Checkbutton(r, text="来自服务器(跳过PIN/签名校验)", variable=self.p_server).pack(side="left", padx=6)

        r = ttk.Frame(top); r.pack(fill="x", padx=4, pady=4)
        ttk.Button(r, text="解析", command=self.on_parse).pack(side="left")
        self.p_status = ttk.Label(r, text="就绪")
        self.p_status.pack(side="left", padx=10)

        nb = ttk.Notebook(self.tab_parse)
        nb.pack(fill="both", expand=True, padx=6, pady=4)

        self.header_tree = ttk.Treeview(nb, columns=("off", "tag", "len", "val"), show="headings")
        for c, w, t in (("off", 70, "偏移"), ("tag", 60, "Tag"), ("len", 60, "长度"), ("val", 480, "值")):
            self.header_tree.heading(c, text=t)
            self.header_tree.column(c, width=w, anchor="w")
        nb.add(self.header_tree, text="头部")

        self.group_tree = ttk.Treeview(nb, columns=("detail",), show="tree headings")
        self.group_tree.heading("#0", text="名称")
        self.group_tree.heading("detail", text="详情")
        self.group_tree.column("#0", width=320)
        self.group_tree.column("detail", width=420)
        nb.add(self.group_tree, text="密钥组")

        self.report_text = tk.Text(nb, wrap="none")
        nb.add(self.report_text, text="报告")

        self.hex_text = tk.Text(nb, wrap="none", font=("Consolas", 9))
        nb.add(self.hex_text, text="十六进制")

    def _pick_parse_file(self):
        path = filedialog.askopenfilename(filetypes=[("MXD/DKL", "*.dkl *.DKL"), ("所有文件", "*.*")])
        if path:
            self.p_file.set(path)

    def _pick_pub(self):
        path = filedialog.askopenfilename(filetypes=[("密钥", "*.pem *.key *.der *.pub"), ("所有文件", "*.*")])
        if path:
            self.p_pub.set(path)

    def on_parse(self):
        path = self.p_file.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("错误", "请选择有效的 DKL 文件")
            return
        pub = None
        if self.p_pub.get().strip():
            try:
                with open(self.p_pub.get().strip(), "rb") as f:
                    pub = f.read()
            except OSError as e:
                messagebox.showerror("错误", "读取公钥失败: %s" % e)
                return
        try:
            dkl, err = DKL.from_file(path, rsa_public_key=pub,
                                     pin=self.p_pin.get().strip() or None,
                                     from_server=self.p_server.get())
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("异常", str(e))
            return
        self.parsed = dkl
        self._fill_header(dkl)
        self._fill_groups(dkl.key_groups)
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", report.report(dkl))
        self.hex_text.delete("1.0", "end")
        self.hex_text.insert("1.0", hex_dump(dkl.raw))
        if err == MXDError.Success:
            self._load_into_generate(dkl)
        self.p_status.config(text="%s | %s | 密钥组 %d" % (
            err.message, "CRC OK" if dkl.crc_ok else "CRC 未校验", len(dkl.key_groups)))

    def _load_into_generate(self, dkl):
        """解析成功后，把头部字段与密钥组回填到生成页。"""
        self._apply_header_to_form(dkl.header)
        self.groups = _clone_groups(dkl.key_groups)
        self._refresh_edit_tree()
        self.opt_obf.set(dkl.header.is_obfuscated())
        if hasattr(self, "u_summary"):
            self._wiz_refresh_summary()
        self.gen_log.insert("end", "已把解析结果回填到生成页（%d 个密钥组）\n" % len(self.groups))
        self.gen_log.see("end")

    def _fill_header(self, dkl):
        for i in self.header_tree.get_children():
            self.header_tree.delete(i)
        for off, tag, name, length, text in report.header_items(dkl.header_bytes):
            self.header_tree.insert("", "end",
                                    values=("%04x" % off, "%04x" % tag, length, "%s  %s" % (name, text)))

    def _fill_groups(self, groups):
        for i in self.group_tree.get_children():
            self.group_tree.delete(i)
        for gi, g in enumerate(groups):
            node = self.group_tree.insert("", "end", text="[%d] %s" % (gi, g.name),
                                          values=("%s / %d 把钥匙" % (g.type, len(g.keys)),), open=True)
            for k in g.keys:
                self.group_tree.insert(
                    node, "end", text="  " + k.name,
                    values=("KeyID(12位)=%d (0x%x)   Dallas(18位)=%d"
                            % (k.key_id, k.key_id, dkl_key_to_dallas_key(k.key_id)),))
            for at in g.access_times:
                times = "; ".join("%02d:%02d-%02d:%02d" % (t.start.hour, t.start.minute,
                                                           t.end.hour, t.end.minute) for t in at.times)
                self.group_tree.insert(node, "end", text="  访问时间",
                                       values=("mask=%d(%s) %s" % (at.day_of_week_mask,
                                                                   mask_to_days(at.day_of_week_mask), times),))

    # ==================================================================
    # 生成
    # ==================================================================
    def _build_generate(self):
        left = ttk.LabelFrame(self.tab_gen, text="头部字段")
        left.pack(side="left", fill="y", padx=6, pady=6)
        sf = ScrollFrame(left)
        sf.pack(fill="both", expand=True)
        form = sf.inner

        form.columnconfigure(1, weight=1)
        self.g = {}
        self.tz_min = {k: None for k in TZ_FIELD_KEYS}
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        for row, (key, label, tag, kind, arg, default) in enumerate(HEADER_FIELDS):
            if default == "NOW":
                default = now
            disp = "[%04x] %s" % (tag, label)
            if kind == "datetime":
                self.g[key] = self._datetime_field(form, row, key, disp, default)
                continue
            ttk.Label(form, text=disp).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            self.g[key] = self._make_header_widget(form, row, kind, arg, default)

        ttk.Button(form, text="时间=现在", command=self._fill_now).grid(
            row=len(HEADER_FIELDS), column=1, sticky="w", padx=4, pady=4)

        # 只读“自动字段”（由生成选项/密钥/时间选择器决定）
        auto = ttk.LabelFrame(form, text="自动字段（由生成选项/密钥/时间选择器决定，只读）")
        auto.grid(row=len(HEADER_FIELDS) + 1, column=0, columnspan=2, sticky="we", padx=4, pady=6)
        self.auto_vars = {}
        for i, (akey, alabel, atag) in enumerate(list(AUTO_FIELDS) + list(TZ_AUTO)):
            ttk.Label(auto, text="[%04x] %s" % (atag, alabel)).grid(row=i, column=0, sticky="w", padx=4, pady=1)
            var = tk.StringVar(value="-")
            ttk.Label(auto, textvariable=var, foreground="#333").grid(row=i, column=1, sticky="w", padx=4, pady=1)
            self.auto_vars[akey] = var

        right = ttk.Frame(self.tab_gen)
        right.pack(side="left", fill="both", expand=True)

        # 密钥组编辑
        grp = ttk.LabelFrame(right, text="密钥组")
        grp.pack(fill="both", expand=True, padx=6, pady=6)
        grp.columnconfigure(0, weight=1)
        grp.columnconfigure(1, minsize=120)
        grp.rowconfigure(0, weight=1)
        self.e_group_tree = ttk.Treeview(grp, columns=("detail",), show="tree headings", height=10)
        self.e_group_tree.heading("#0", text="名称")
        self.e_group_tree.heading("detail", text="详情")
        self.e_group_tree.column("#0", width=170)
        self.e_group_tree.column("detail", width=260)
        self.e_group_tree.grid(row=0, column=0, sticky="nsew", padx=(4, 2), pady=4)
        self.e_group_tree.bind("<<TreeviewSelect>>", self._on_edit_select)
        btns = ttk.Frame(grp)
        btns.grid(row=0, column=1, sticky="new", padx=(2, 4), pady=4)
        for text, cmd in (("新增组", self._add_group), ("新增钥匙", self._add_key),
                          ("删除", self._del_sel), ("上移", lambda: self._move(-1)),
                          ("下移", lambda: self._move(1))):
            ttk.Button(btns, text=text, command=cmd).pack(pady=2, fill="x")

        # 编辑区
        edit = ttk.LabelFrame(right, text="编辑选中项")
        edit.pack(fill="x", padx=6, pady=4)
        self.e_name = tk.StringVar()
        self.e_type = tk.StringVar()
        self.e_keyid = tk.StringVar()
        self.e_mask = tk.StringVar()
        self.e_sh = tk.StringVar(); self.e_sm = tk.StringVar()
        self.e_eh = tk.StringVar(); self.e_em = tk.StringVar()

        from tkinter import Spinbox
        ttk.Label(edit, text="名称").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(edit, textvariable=self.e_name, width=24, validate="key",
                  validatecommand=(edit.register(_ascii_validator(32)), "%P")).grid(row=0, column=1, padx=4)
        ttk.Label(edit, text="类型").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Combobox(edit, textvariable=self.e_type, values=("VAULT", "LOCK", "SERVICE"),
                     width=12, state="readonly").grid(row=0, column=3, padx=4)
        ttk.Label(edit, text="KeyID(18位)").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Entry(edit, textvariable=self.e_keyid, width=24, validate="key",
                  validatecommand=(edit.register(_dallas_validator()), "%P")).grid(row=1, column=1, padx=4)
        ttk.Label(edit, text="星期掩码").grid(row=1, column=2, sticky="w", padx=4)
        ttk.Entry(edit, textvariable=self.e_mask, width=12, validate="key",
                  validatecommand=(edit.register(_mask_validator()), "%P")).grid(row=1, column=3, padx=4)
        ttk.Label(edit, text="起 HH:MM").grid(row=2, column=0, sticky="w", padx=4)
        f = ttk.Frame(edit); f.grid(row=2, column=1, sticky="w")
        Spinbox(f, from_=0, to=23, textvariable=self.e_sh, width=4, wrap=True).pack(side="left")
        ttk.Label(f, text=":").pack(side="left")
        Spinbox(f, from_=0, to=59, textvariable=self.e_sm, width=4, wrap=True).pack(side="left")
        ttk.Label(edit, text="止 HH:MM").grid(row=2, column=2, sticky="w", padx=4)
        f2 = ttk.Frame(edit); f2.grid(row=2, column=3, sticky="w")
        Spinbox(f2, from_=0, to=23, textvariable=self.e_eh, width=4, wrap=True).pack(side="left")
        ttk.Label(f2, text=":").pack(side="left")
        Spinbox(f2, from_=0, to=59, textvariable=self.e_em, width=4, wrap=True).pack(side="left")
        ttk.Button(edit, text="应用修改", command=self._apply_edit).grid(row=3, column=1, sticky="w", padx=4, pady=4)

        # 选项
        opt = ttk.LabelFrame(right, text="生成选项")
        opt.pack(fill="x", padx=6, pady=6)
        self.opt_obf = tk.BooleanVar(value=True)
        self.opt_pin = tk.StringVar()
        self.opt_prim = tk.StringVar()
        self.opt_sec = tk.StringVar()
        self.opt_style = tk.StringVar(value="leaf")
        self.opt_out = tk.StringVar()

        ttk.Checkbutton(opt, text="XTEA 混淆", variable=self.opt_obf).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(opt, text="PIN").grid(row=0, column=1, sticky="w")
        ttk.Entry(opt, textvariable=self.opt_pin, width=10).grid(row=0, column=2, sticky="w")
        ttk.Label(opt, text="Schema 风格").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Combobox(opt, textvariable=self.opt_style, values=("leaf", "root"), width=8,
                     state="readonly").grid(row=0, column=4, sticky="w")

        ttk.Label(opt, text="主签名私钥（机器当前/旧）").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Entry(opt, textvariable=self.opt_prim, width=40).grid(row=1, column=1, columnspan=3, sticky="we")
        ttk.Button(opt, text="浏览", command=lambda v=self.opt_prim: self._pick_key(v)).grid(row=1, column=4, padx=4)

        ttk.Label(opt, text="次签名私钥（新，覆盖用）").grid(row=2, column=0, sticky="w", padx=4)
        ttk.Entry(opt, textvariable=self.opt_sec, width=40).grid(row=2, column=1, columnspan=3, sticky="we")
        ttk.Button(opt, text="浏览", command=lambda v=self.opt_sec: self._pick_key(v)).grid(row=2, column=4, padx=4)

        ttk.Label(opt, text="填“次签名私钥”即用新密钥覆盖旧 DKL，须同时填主签名私钥",
                  foreground="#555").grid(row=3, column=1, columnspan=4, sticky="w", padx=4)

        ttk.Label(opt, text="输出文件").grid(row=4, column=0, sticky="w", padx=4)
        ttk.Entry(opt, textvariable=self.opt_out, width=40).grid(row=4, column=1, columnspan=3, sticky="we")
        ttk.Button(opt, text="浏览", command=self._pick_out).grid(row=4, column=4, padx=4)
        ttk.Button(opt, text="生成 DKL", command=self.on_generate).grid(row=5, column=1, sticky="w", padx=4, pady=6)
        ttk.Button(opt, text="导入密钥组", command=self._import_groups).grid(row=5, column=2, sticky="w", padx=4)
        ttk.Button(opt, text="头部模板", command=self._import_header_template).grid(row=5, column=3, sticky="w", padx=4)

        self.gen_log = tk.Text(right, height=8, wrap="word")
        self.gen_log.pack(fill="x", padx=6, pady=4)

        self._refresh_edit_tree()

    def _make_header_widget(self, parent, row, kind, arg, default):
        """按字段类型创建控件并返回绑定变量。"""
        if kind == "combo":
            control = ttk.Combobox(parent, values=arg, width=23, state="readonly")
        elif kind == "combo_opt":
            control = ttk.Combobox(parent, values=[""] + list(arg), width=23, state="readonly")
        elif kind == "spin":
            lo, hi = arg
            control = ttk.Spinbox(parent, from_=lo, to=hi, width=22, state="readonly")
        else:
            checker = {"uint": _digits_only, "version": _valid_version}.get(kind)
            vcmd = (parent.register(_ascii_validator(arg, checker)), "%P")
            control = ttk.Entry(parent, width=26, validate="key", validatecommand=vcmd)
        var = tk.StringVar(value=default)
        control.configure(textvariable=var)
        control.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        return var

    def _ascii_entry(self, parent, row, default, maxlen, checker=None, width=26):
        var = tk.StringVar(value=default)
        vcmd = (parent.register(_ascii_validator(maxlen, checker)), "%P")
        ttk.Entry(parent, textvariable=var, width=width, validate="key",
                  validatecommand=vcmd).grid(row=row, column=1, sticky="we", padx=4, pady=2)
        return var

    def _datetime_field(self, parent, row, key, label_text, default=""):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        var = tk.StringVar(value=default)
        box = ttk.Frame(parent)
        box.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        ttk.Entry(box, textvariable=var, width=18, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(box, text="…", width=3,
                   command=lambda k=key: self._pick_datetime_key(k)).pack(side="left", padx=2)
        return var

    def _pick_datetime_key(self, key):
        res = self._ask_datetime(self.g[key].get(), self.tz_min.get(key))
        if res is None:
            return
        text, tzm = res
        self.g[key].set(text)
        self.tz_min[key] = tzm
        self._update_tz_auto()

    def _update_tz_auto(self):
        for time_key in TZ_FIELD_KEYS:
            tz_key = TZ_TAG_KEY[time_key]
            m = self.tz_min.get(time_key)
            self.auto_vars[tz_key].set(_tz_to_str(m) if m is not None else "-")

    def _ask_datetime(self, initial_time, initial_tz=None):
        """日期时间+时区选择对话框。

        返回 (壁钟字符串, 时区分钟数或None)；清空返回 ('', None)；取消返回 None。
        """
        from tkinter import Spinbox
        dlg = tk.Toplevel(self)
        dlg.title("选择日期时间与时区")
        dlg.transient(self)
        dlg.grab_set()
        try:
            dt = datetime.datetime.strptime(initial_time, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        fields = [("年", 1970, 2100, dt.year), ("月", 1, 12, dt.month), ("日", 1, 31, dt.day),
                  ("时", 0, 23, dt.hour), ("分", 0, 59, dt.minute), ("秒", 0, 59, dt.second)]
        vars_ = []
        for col, (name, lo, hi, val) in enumerate(fields):
            ttk.Label(dlg, text=name).grid(row=0, column=col, padx=4, pady=4)
            v = tk.StringVar(value=str(val))
            Spinbox(dlg, from_=lo, to=hi, textvariable=v, width=5, wrap=True).grid(row=1, column=col, padx=4)
            vars_.append(v)

        ttk.Label(dlg, text="时区").grid(row=2, column=0, sticky="e", padx=4, pady=6)
        tz_var = tk.StringVar(value=_tz_label(initial_tz))
        ttk.Combobox(dlg, textvariable=tz_var, values=[label for label, _ in TZ_OPTIONS],
                     state="readonly", width=30).grid(row=2, column=1, columnspan=5, sticky="we", padx=4)
        result = {"value": None}

        def set_now():
            n = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            for v, x in zip(vars_, (n.year, n.month, n.day, n.hour, n.minute, n.second)):
                v.set(str(x))

        def ok():
            try:
                y, mo, da, h, mi, s = (int(v.get()) for v in vars_)
                value = datetime.datetime(y, mo, da, h, mi, s)
            except ValueError:
                messagebox.showerror("错误", "日期或时间无效", parent=dlg)
                return
            result["value"] = (value.strftime("%Y-%m-%d %H:%M:%S"),
                               _tz_minutes_from_label(tz_var.get()))
            dlg.destroy()

        def clear():
            result["value"] = ("", None)
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.grid(row=3, column=0, columnspan=6, pady=6)
        ttk.Button(btns, text="现在", command=set_now).pack(side="left", padx=4)
        ttk.Button(btns, text="清空", command=clear).pack(side="left", padx=4)
        ttk.Button(btns, text="确定", command=ok).pack(side="left", padx=4)
        ttk.Button(btns, text="取消", command=dlg.destroy).pack(side="left", padx=4)
        dlg.wait_window()
        return result["value"]

    def _fill_now(self):
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        for k in TZ_FIELD_KEYS:
            self.g[k].set(_epoch_to_wall(now, self.tz_min.get(k)))

    def _pick_key(self, var):
        path = filedialog.askopenfilename(filetypes=[("RSA 私钥", "*.key *.pem"), ("所有文件", "*.*")])
        if path:
            var.set(path)

    def _pick_out(self):
        path = filedialog.asksaveasfilename(defaultextension=".dkl",
                                            filetypes=[("DKL", "*.dkl")])
        if path:
            self.opt_out.set(path)

    # ---- 密钥组编辑 ----
    def _refresh_edit_tree(self):
        for i in self.e_group_tree.get_children():
            self.e_group_tree.delete(i)
        for gi, g in enumerate(self.groups):
            node = self.e_group_tree.insert("", "end", iid="g%d" % gi,
                                            text=g.name, values=(g.type,), open=True)
            for ki, k in enumerate(g.keys):
                self.e_group_tree.insert(
                    node, "end", iid="g%d_k%d" % (gi, ki), text="  " + k.name,
                    values=("KeyID(12位)=%d   Dallas(18位)=%d"
                            % (k.key_id, dkl_key_to_dallas_key(k.key_id)),))

    def _on_edit_select(self, _event=None):
        sel = self.e_group_tree.selection()
        if not sel:
            return
        iid = sel[0]
        parts = iid.split("_")
        gi = int(parts[0][1:])
        g = self.groups[gi]
        if len(parts) == 1:
            self.current_group, self.current_key = gi, None
            self.e_name.set(g.name); self.e_type.set(g.type)
            self.e_keyid.set("")
            at = g.access_times[0] if g.access_times else None
            if at:
                self.e_mask.set(str(at.day_of_week_mask))
                t = at.times[0] if at.times else Time()
                self.e_sh.set(str(t.start.hour)); self.e_sm.set(str(t.start.minute))
                self.e_eh.set(str(t.end.hour)); self.e_em.set(str(t.end.minute))
            else:
                for v in (self.e_mask, self.e_sh, self.e_sm, self.e_eh, self.e_em):
                    v.set("")
        else:
            ki = int(parts[1][1:])
            self.current_group, self.current_key = gi, ki
            k = g.keys[ki]
            self.e_name.set(k.name)
            self.e_type.set(g.type)                       # 显示所属组类型（可改，同步到组）
            self.e_keyid.set(str(dkl_key_to_dallas_key(k.key_id)))   # 显示 18 位 Dallas
            for v in (self.e_mask, self.e_sh, self.e_sm, self.e_eh, self.e_em):
                v.set("")

    def _add_group(self):
        self.groups.append(KeyGroup(name="New Group", type="VAULT",
                                    keys=[], access_times=[AccessTime(127, [Time(HourMinute(0, 0), HourMinute(23, 59))])]))
        self._refresh_edit_tree()

    def _add_key(self):
        if self.current_group is None:
            messagebox.showinfo("提示", "请先选择一个组")
            return
        self.groups[self.current_group].keys.append(KeyEntry(name="New Key", key_id=0))
        self._refresh_edit_tree()

    def _del_sel(self):
        if self.current_group is None:
            return
        if self.current_key is None:
            del self.groups[self.current_group]
        else:
            del self.groups[self.current_group].keys[self.current_key]
        self.current_group = self.current_key = None
        self._refresh_edit_tree()

    def _move(self, delta):
        if self.current_group is None:
            return
        gi = self.current_group
        if self.current_key is None:
            ni = gi + delta
            if 0 <= ni < len(self.groups):
                self.groups[gi], self.groups[ni] = self.groups[ni], self.groups[gi]
                self.current_group = ni
        else:
            keys = self.groups[gi].keys
            ni = self.current_key + delta
            if 0 <= ni < len(keys):
                keys[self.current_key], keys[ni] = keys[ni], keys[self.current_key]
                self.current_key = ni
        self._refresh_edit_tree()

    def _apply_edit(self):
        if self.current_group is None:
            return
        g = self.groups[self.current_group]
        if self.current_key is None:
            g.name = self.e_name.get()
            g.type = self.e_type.get()
            mask = self.e_mask.get().strip()
            if mask == "":
                g.access_times = []
            else:
                try:
                    at = AccessTime(int(mask), [Time(
                        HourMinute(int(self.e_sh.get() or 0), int(self.e_sm.get() or 0)),
                        HourMinute(int(self.e_eh.get() or 23), int(self.e_em.get() or 59)))])
                except ValueError:
                    messagebox.showerror("错误", "访问时间格式错误")
                    return
                g.access_times = [at]
        else:
            k = g.keys[self.current_key]
            k.name = self.e_name.get()
            g.type = self.e_type.get()                    # 类型属于组，键上修改同步到组
            text = self.e_keyid.get().strip()
            if text:
                try:
                    raw = int(text, 0)
                except ValueError:
                    messagebox.showerror("错误", "KeyID 必须是整数（18 位 Dallas 编号，支持 0x 前缀）")
                    return
                if not (0 <= raw <= 0xFFFFFFFFFFFFFFFF):
                    messagebox.showerror("错误", "Dallas 编号超出 64 位范围")
                    return
                k.key_id = dallas_key_to_dkl_key(raw)
            else:
                k.key_id = 0
        self._refresh_edit_tree()

    # ---- 生成辅助 ----
    def _import_groups(self):
        if not self.parsed or not self.parsed.key_groups:
            messagebox.showinfo("提示", "请先在“解析”页解析一个 DKL")
            return
        self.groups = _clone_groups(self.parsed.key_groups)
        self._refresh_edit_tree()
        self.gen_log.insert("end", "已导入 %d 个密钥组（来自解析结果）\n" % len(self.groups))
        self.gen_log.see("end")

    def _import_header_template(self):
        if not self.parsed:
            messagebox.showinfo("提示", "请先在“解析”页解析一个 DKL")
            return
        self._apply_header_to_form(self.parsed.header)
        self.gen_log.insert("end", "已用解析文件的头部填充表单\n")
        self.gen_log.see("end")

    def _apply_header_to_form(self, header):
        ft = (header.file_type or "").upper()
        self.g["file_type"].set(ft if ft in FILE_TYPES else "")
        self.g["compatibility_level"].set(str(header.compatibility_level or 0))
        self.g["major_version"].set("" if header.major_version is None else str(header.major_version))
        self.g["minor_version"].set("" if header.minor_version is None else str(header.minor_version))
        self.g["machine_unique_id"].set(str(header.machine_unique_id or 0))
        self.g["pin_digits"].set(str(header.number_of_pin_digits or 4))
        self.g["content_length"].set("" if header.content_length is None else str(header.content_length))
        self.g["compressed_content_length"].set(
            "" if header.compressed_content_length is None else str(header.compressed_content_length))

        self.g["customer"].set(header.customer or "")
        self.g["origin"].set(header.origin or "")
        self.g["user_name"].set(header.user_name or "")
        self.g["version"].set(header.version or "")
        ev = header.electronics_version
        self.g["electronics_version"].set(ev if ev in ELECTRONICS_VERSIONS else "")
        self.g["application_base_address"].set(header.application_base_address or "")
        self.g["application_entry_point"].set(header.application_entry_point or "")
        self.g["original_file_name"].set(header.original_file_name or "")

        for time_key in TZ_FIELD_KEYS:
            tz_key = TZ_TAG_KEY[time_key]
            epoch = getattr(header, time_key)
            tzm = getattr(header, tz_key)
            self.tz_min[time_key] = tzm
            self.g[time_key].set("" if epoch is None else _epoch_to_wall(epoch, tzm))

        self._refresh_auto_fields(header)

    def _refresh_auto_fields(self, header):
        for key, _label, _tag in AUTO_FIELDS:
            val = getattr(header, key, None)
            if key == "rsa_public_key":
                text = "-" if not val else "%d bytes  SHA1 %s" % (len(val), rsa_sign.fingerprint_der(val))
            elif val is None:
                text = "-"
            else:
                text = str(val)
            self.auto_vars[key].set(text)
        self._update_tz_auto()

    def _header_from_form(self):
        for key, lab in (("customer", "客户"), ("origin", "来源计算机"), ("user_name", "用户名"),
                         ("application_base_address", "应用基址"), ("application_entry_point", "应用入口点"),
                         ("original_file_name", "原始文件名")):
            if not _is_ascii_printable(self.g[key].get()):
                raise ValueError("%s 含非法字符（%s）" % (lab, _ASCII_ONLY))
        version = self.g["version"].get().strip()
        if version and not _valid_version(version):
            raise ValueError("版本格式应为 xx.yy[b]，例如 1.00 或 2.10a")

        def opt_int(key):
            text = self.g[key].get().strip()
            return int(text) if text else None

        content_length = opt_int("content_length")
        if content_length is not None and not (0 <= content_length <= 0xFFFFFFFF):
            raise ValueError("内容长度超出 32 位范围(0..4294967295)")
        compressed_length = opt_int("compressed_content_length")
        if compressed_length is not None and not (0 <= compressed_length <= 0xFFFFFFFF):
            raise ValueError("压缩内容长度超出 32 位范围(0..4294967295)")
        machine_uid = int(self.g["machine_unique_id"].get() or 0)
        if not (0 <= machine_uid <= 0xFFFFFFFFFFFFFFFF):
            raise ValueError("机器唯一ID 超出 64 位范围(0..18446744073709551615)")

        header = Header(
            file_type=(self.g["file_type"].get().strip().lower() or None),
            compatibility_level=int(self.g["compatibility_level"].get() or 0),
            major_version=opt_int("major_version"),
            minor_version=opt_int("minor_version"),
            customer=self.g["customer"].get(),
            origin=self.g["origin"].get(),
            user_name=self.g["user_name"].get(),
            machine_unique_id=machine_uid,
            application_base_address=self.g["application_base_address"].get() or None,
            application_entry_point=self.g["application_entry_point"].get() or None,
            version=version or None,
            electronics_version=self.g["electronics_version"].get() or None,
            number_of_pin_digits=int(self.g["pin_digits"].get() or 4),
            content_length=content_length,
            compressed_content_length=compressed_length,
            original_file_name=self.g["original_file_name"].get() or None,
        )
        # 时间按“所选时区的当地壁钟”处理；时区仅在时间存在时写入
        ve = _wall_to_epoch(self.g["valid_from_time"].get(), self.tz_min.get("valid_from_time"))
        ie = _wall_to_epoch(self.g["initial_creation_time"].get(), self.tz_min.get("initial_creation_time"))
        fe = _wall_to_epoch(self.g["final_modification_time"].get(), self.tz_min.get("final_modification_time"))
        header.valid_from_time = ve if ve is not None else 0
        header.initial_creation_time = ie
        header.final_modification_time = fe
        header.valid_from_time_zone = self.tz_min.get("valid_from_time") if ve is not None else None
        header.initial_creation_time_zone = self.tz_min.get("initial_creation_time") if ie is not None else None
        header.final_modification_time_zone = self.tz_min.get("final_modification_time") if fe is not None else None
        return header

    @staticmethod
    def _read_key(path):
        if not path:
            return None
        with open(path, "rb") as f:
            return f.read()

    def _self_check_text(self, data, machine_pub=None, pin=None):
        dkl = DKL()
        err = dkl.parse(data, rsa_public_key=machine_pub, pin=pin)
        lines = ["解析结果: %s" % err.message]
        if dkl.header.rsa_public_key:
            lines.append("头内公钥指纹(SHA1): %s" % rsa_sign.fingerprint_der(dkl.header.rsa_public_key))
        lines.append("CRC: %s" % ("OK" if dkl.crc_ok else "未校验/失败"))
        if dkl.primary_sig_ok is not None:
            lines.append("主签名(机器当前密钥): %s" % ("通过" if dkl.primary_sig_ok else "失败"))
        if dkl.secondary_sig_ok is not None:
            lines.append("次签名(头内新公钥): %s" % ("通过" if dkl.secondary_sig_ok else "失败"))
        if dkl.pin_ok is not None:
            lines.append("PIN: %s" % ("通过" if dkl.pin_ok else "失败"))
        return "\n".join(lines)

    def on_generate(self):
        out = self.opt_out.get().strip()
        if not out:
            messagebox.showerror("错误", "请填写输出文件")
            return
        try:
            header = self._header_from_form()
            pin_digits = int(self.g["pin_digits"].get() or 4)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return
        try:
            prim = self._read_key(self.opt_prim.get().strip())
            sec = self._read_key(self.opt_sec.get().strip())
        except OSError as e:
            messagebox.showerror("错误", "读取私钥失败: %s" % e)
            return

        machine_pub = rsa_sign.public_der(rsa_sign.load_private_key(prim)) if prim is not None else None
        pin = self.opt_pin.get().strip() or None
        try:
            data = DKL().build(header=header, groups=self.groups,
                               obfuscate=self.opt_obf.get(), pin=pin,
                               primary_key=prim, secondary_key=sec,
                               pin_digits=pin_digits, schema_style=self.opt_style.get())
            with open(out, "wb") as f:
                f.write(data)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("异常", str(e))
            return
        self.gen_log.insert("end", "已生成 %s (%d 字节)\n%s\n" %
                            (out, len(data), self._self_check_text(data, machine_pub, pin)))
        self.gen_log.see("end")
        self.p_file.set(out)
        self._refresh_auto_fields(header)   # build() 已回写混淆/签名/PIN/公钥等自动字段

    # ==================================================================
    # 密钥更新（用新密钥覆盖旧 DKL）
    # ==================================================================
    def _build_update(self):
        tip = ttk.LabelFrame(self.tab_update, text="用新密钥覆盖旧 DKL（密钥更新）")
        tip.pack(fill="x", padx=8, pady=6)
        ttk.Label(tip, foreground="#555", justify="left", wraplength=940,
                  text=("机器当前持有“旧密钥”。用旧密钥做【主签名】、新密钥做【次签名】，"
                        "文件头保存【新密钥公钥】。机器用旧公钥验主签名通过后，再把新公钥写入。\n"
                        "内容（钥匙清单）与头部字段取自“解析/生成”页；可点“从旧 DKL 导入内容”一键填充。")).pack(
            anchor="w", padx=6, pady=4)

        f1 = ttk.LabelFrame(self.tab_update, text="步骤 1 · 导入旧 DKL 内容（可选）")
        f1.pack(fill="x", padx=8, pady=4)
        self.u_old_dkl = tk.StringVar()
        ttk.Label(f1, text="旧 DKL 文件").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(f1, textvariable=self.u_old_dkl).grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(f1, text="浏览", command=self._wiz_pick_old_dkl).grid(row=0, column=2, padx=4)
        ttk.Button(f1, text="从旧 DKL 导入内容", command=self._wiz_import).grid(row=0, column=3, padx=4)
        f1.columnconfigure(1, weight=1)

        self.u_summary = ttk.Treeview(f1, columns=("d",), show="tree headings", height=5)
        self.u_summary.heading("#0", text="当前内容（密钥组）")
        self.u_summary.heading("d", text="详情")
        self.u_summary.column("#0", width=280)
        self.u_summary.column("d", width=520)
        self.u_summary.grid(row=1, column=0, columnspan=4, sticky="we", padx=4, pady=4)

        f2 = ttk.LabelFrame(self.tab_update, text="步骤 2 · 签名密钥")
        f2.pack(fill="x", padx=8, pady=4)
        self.u_old_key = tk.StringVar()
        self.u_new_key = tk.StringVar()
        ttk.Label(f2, text="当前机器私钥（旧，主签名）").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(f2, textvariable=self.u_old_key).grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(f2, text="浏览", command=lambda: self._pick_key(self.u_old_key)).grid(row=0, column=2, padx=4)
        ttk.Label(f2, text="新私钥（次签名/覆盖用）").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(f2, textvariable=self.u_new_key).grid(row=1, column=1, sticky="we", padx=4)
        ttk.Button(f2, text="浏览", command=lambda: self._pick_key(self.u_new_key)).grid(row=1, column=2, padx=4)
        ttk.Button(f2, text="生成新密钥对…", command=self._wiz_gen_newkey).grid(row=1, column=3, padx=4)
        f2.columnconfigure(1, weight=1)

        f3 = ttk.LabelFrame(self.tab_update, text="步骤 3 · 选项与输出")
        f3.pack(fill="x", padx=8, pady=4)
        self.u_obf = tk.BooleanVar(value=True)
        self.u_pin = tk.StringVar()
        self.u_style = tk.StringVar(value="leaf")
        self.u_out = tk.StringVar()
        ttk.Checkbutton(f3, text="XTEA 混淆", variable=self.u_obf).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(f3, text="PIN").grid(row=0, column=1, sticky="w")
        ttk.Entry(f3, textvariable=self.u_pin, width=10).grid(row=0, column=2, sticky="w")
        ttk.Label(f3, text="Schema 风格").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Combobox(f3, textvariable=self.u_style, values=("leaf", "root"), width=8,
                     state="readonly").grid(row=0, column=4, sticky="w")
        ttk.Label(f3, text="输出文件").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(f3, textvariable=self.u_out).grid(row=1, column=1, columnspan=3, sticky="we", padx=4)
        ttk.Button(f3, text="浏览", command=self._wiz_pick_out).grid(row=1, column=4, padx=4)
        ttk.Button(f3, text="一键生成覆盖文件", command=self._wiz_generate).grid(row=2, column=1, sticky="w", padx=4, pady=6)
        f3.columnconfigure(1, weight=1)

        self.u_log = tk.Text(self.tab_update, height=10, wrap="word")
        self.u_log.pack(fill="both", expand=True, padx=8, pady=6)
        self._wiz_refresh_summary()

    def _wiz_pick_old_dkl(self):
        path = filedialog.askopenfilename(filetypes=[("DKL", "*.dkl *.DKL"), ("所有文件", "*.*")])
        if path:
            self.u_old_dkl.set(path)

    def _wiz_pick_out(self):
        path = filedialog.asksaveasfilename(defaultextension=".dkl", filetypes=[("DKL", "*.dkl")])
        if path:
            self.u_out.set(path)

    def _wiz_refresh_summary(self):
        for i in self.u_summary.get_children():
            self.u_summary.delete(i)
        for gi, g in enumerate(self.groups):
            node = self.u_summary.insert("", "end", text="[%d] %s" % (gi, g.name),
                                         values=("%s / %d 把钥匙" % (g.type, len(g.keys)),), open=True)
            for k in g.keys:
                self.u_summary.insert(node, "end", text="  " + k.name,
                                      values=("KeyID=%d" % k.key_id,))

    def _wiz_import(self):
        path = self.u_old_dkl.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("错误", "请选择有效的旧 DKL 文件")
            return
        dkl, err = DKL.from_file(path, from_server=True)
        if err != MXDError.Success:
            messagebox.showerror("错误", "解析旧 DKL 失败: %s" % err.message)
            return
        self.parsed = dkl
        self.groups = _clone_groups(dkl.key_groups)
        self._apply_header_to_form(dkl.header)
        self._refresh_edit_tree()
        self._wiz_refresh_summary()
        self.u_log.insert("end", "已从 %s 导入 %d 个密钥组\n" % (os.path.basename(path), len(self.groups)))
        self.u_log.see("end")

    def _wiz_gen_newkey(self):
        path = filedialog.asksaveasfilename(defaultextension=".key",
                                            filetypes=[("RSA 私钥", "*.key *.pem")],
                                            title="保存新私钥")
        if not path:
            return
        try:
            priv_pem, pub_pem = rsa_sign.generate_keypair(1024)
            with open(path, "wb") as f:
                f.write(priv_pem)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("异常", str(e))
            return
        self.u_new_key.set(path)
        pub_path = ""
        if messagebox.askyesno("保存公钥", "已生成新密钥对并保存私钥。\n是否同时保存公钥文件？"):
            pub_path = path + ".pub"
            with open(pub_path, "wb") as f:
                f.write(pub_pem)
        fp = rsa_sign.fingerprint_der(rsa_sign.public_der(rsa_sign.load_private_key(priv_pem)))
        self.u_log.insert("end", "已生成新密钥对: %s\n新公钥指纹: %s\n" % (path, fp))
        if pub_path:
            self.u_log.insert("end", "公钥: %s\n" % pub_path)
        self.u_log.see("end")

    def _wiz_generate(self):
        if not self.groups:
            messagebox.showerror("错误", "内容为空，请先“从旧 DKL 导入内容”或在“生成”页编辑密钥组")
            return
        if not self.u_old_key.get().strip() or not self.u_new_key.get().strip():
            messagebox.showerror("错误", "请同时选择当前机器私钥（旧）与新私钥")
            return
        out = self.u_out.get().strip()
        if not out:
            messagebox.showerror("错误", "请填写输出文件")
            return
        try:
            header = self._header_from_form()
            prim = self._read_key(self.u_old_key.get().strip())
            sec = self._read_key(self.u_new_key.get().strip())
        except (OSError, ValueError) as e:
            messagebox.showerror("错误", "读取失败: %s" % e)
            return
        machine_pub = rsa_sign.public_der(rsa_sign.load_private_key(prim))
        pin = self.u_pin.get().strip() or None
        try:
            data = DKL().build(header=header, groups=self.groups, obfuscate=self.u_obf.get(),
                               pin=pin, primary_key=prim, secondary_key=sec,
                               pin_digits=int(self.g["pin_digits"].get() or 4),
                               schema_style=self.u_style.get())
            with open(out, "wb") as f:
                f.write(data)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("异常", str(e))
            return
        self.u_log.insert("end", "\n已生成覆盖文件 %s (%d 字节)\n%s\n" %
                          (out, len(data), self._self_check_text(data, machine_pub, pin)))
        self.u_log.see("end")
        self.p_file.set(out)

    # ==================================================================
    # 工具
    # ==================================================================
    def _build_tools(self):
        f = ttk.LabelFrame(self.tab_tools, text="Dallas Key（18位）↔ DKL KeyID（12位）转换")
        f.pack(fill="x", padx=8, pady=8)
        self.t_dallas = tk.StringVar()
        self.t_dkl = tk.StringVar()

        ttk.Label(f, text="Dallas Key（18位）").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(f, textvariable=self.t_dallas, width=32).grid(row=0, column=1, padx=4)
        ttk.Button(f, text="18位 → 12位", command=self._d2k).grid(row=0, column=2, padx=4)

        ttk.Label(f, text="DKL KeyID（12位）").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(f, textvariable=self.t_dkl, width=32).grid(row=1, column=1, padx=4)
        ttk.Button(f, text="12位 → 18位", command=self._k2d).grid(row=1, column=2, padx=4)

        info = ttk.LabelFrame(self.tab_tools, text="说明")
        info.pack(fill="both", expand=True, padx=8, pady=8)
        txt = tk.Text(info, wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0",
                   "Dallas Key：物理钥匙编号，64 位整数（18 位十进制），含 1 个校验和字节。\n"
                   "DKL KeyID：DKL 文件内存储的 KeyID（12 位十进制）。\n\n"
                   "18位 → 12位：把编号按小端展开，清零首字节（校验和），再按大端解释。\n"
                   "12位 → 18位：校验和字节由 Dallas CRC8（poly 0x8C）对剩余 7 字节逆序计算得出，可精确还原。\n\n"
                   "示例：\n"
                   "  87496571729477800  ->  127437190657\n"
                   "  121938773469560946 ->  127426539777\n"
                   "  102365666853519589 ->  111814732545")
        txt.config(state="disabled")

    def _d2k(self):
        try:
            v = int(self.t_dallas.get().strip(), 0)
        except ValueError:
            messagebox.showerror("错误", "请输入整数（支持 0x 前缀）")
            return
        self.t_dkl.set(str(dallas_key_to_dkl_key(v)))

    def _k2d(self):
        try:
            v = int(self.t_dkl.get().strip(), 0)
        except ValueError:
            messagebox.showerror("错误", "请输入整数（支持 0x 前缀）")
            return
        self.t_dallas.set(str(dkl_key_to_dallas_key(v)))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()

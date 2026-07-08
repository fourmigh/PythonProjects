# gui_app.py
# ============================================================
# Windows GUI - 自行车牌照检测工具
# 支持中/英/德三语界面切换
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from pathlib import Path
import threading
import time
import os
import sys
import json
import subprocess
import traceback
from datetime import datetime

if getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(sys.executable))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_client.zhipu_client import ZhipuClient
from bicycle_rule import parse_bicycle_response
from ocr_parser import parse_ocr_result
from config import SUPPORTED_EXTENSIONS


# ============================================================
# 国际化文本（仅UI标签，提示词始终中文）
# ============================================================
TEXTS = {
    'zh': {
        'title': '自行车牌照检测工具',
        'select_folder': '选择文件夹',
        'start': '开始识别',
        'clear': '清除结果',
        'status_ready': '就绪',
        'status_processing': '识别中...',
        'result': '识别结果',
        'elapsed': '耗时',
        'seconds': '秒',
        'filename': '文件名',
        'expected': '期望',
        'total_images': '共 {} 张图片',
        'no_image_folder': '未找到支持的图片文件',
        'no_api_key': '请设置环境变量 ZHIPU_API_KEY',
        'api_error': 'API调用失败',
        'raw_answer': '模型原始回答',
        'parse_result': '解析结果',
        'allowed': '允许',
        'denied': '不允许',
        'match': '匹配',
        'mismatch': '不匹配',
        'unknown': '未知',
        'select_image_first': '请先在左侧选择一张图片',
        'system_prompt': '系统提示词',
        'user_prompt': '用户提示词',
        'reasoning_label': '推理 (glm-4v-plus)',
        'ocr_label': 'OCR (glm-4v-flash)',
        'model_label': '模型',
        'language_label': '语言',
        'drop_here': '选择文件夹后图片显示在此处',
        'api_key': 'API Key',
        'api_key_required': '请输入 API Key',
        'show': '显示',
        'hide': '隐藏',
        'remember': '记住',
        'key_saved': 'API Key 已保存到文件',
        'wsl_intro': '提示: 如果在WSL中配置了Key, 可复制过来直接使用',
        'key_from_env': 'API Key 已从 Windows 环境变量自动读取',
        'key_from_wsl': 'API Key 已从 WSL 环境变量自动读取',
    },
    'en': {
        'title': 'Bicycle License Plate Detector',
        'select_folder': 'Select Folder',
        'start': 'Start',
        'clear': 'Clear',
        'status_ready': 'Ready',
        'status_processing': 'Processing...',
        'result': 'Result',
        'elapsed': 'Elapsed',
        'seconds': 's',
        'filename': 'Filename',
        'expected': 'Expected',
        'total_images': '{} images',
        'no_image_folder': 'No supported images found',
        'no_api_key': 'Please set ZHIPU_API_KEY environment variable',
        'api_error': 'API call failed',
        'raw_answer': 'Model Answer',
        'parse_result': 'Parse Result',
        'allowed': 'Allowed',
        'denied': 'Denied',
        'match': 'Match',
        'mismatch': 'Mismatch',
        'unknown': 'Unknown',
        'select_image_first': 'Please select an image from the left panel',
        'system_prompt': 'System Prompt',
        'user_prompt': 'User Prompt',
        'reasoning_label': 'Reasoning (glm-4v-plus)',
        'ocr_label': 'OCR (glm-4v-flash)',
        'model_label': 'Model',
        'language_label': 'Language',
        'drop_here': 'Select a folder to load images here',
        'api_key': 'API Key',
        'api_key_required': 'Please enter API Key',
        'show': 'Show',
        'hide': 'Hide',
        'remember': 'Remember',
        'key_saved': 'API Key saved to file',
        'wsl_intro': 'Tip: If configured in WSL, copy the key here',
        'key_from_env': 'API Key loaded from Windows environment variable',
        'key_from_wsl': 'API Key loaded from WSL environment variable',
    },
    'de': {
        'title': 'Fahrradkennzeichenerkennung',
        'select_folder': 'Ordner wählen',
        'start': 'Erkennen',
        'clear': 'Löschen',
        'status_ready': 'Bereit',
        'status_processing': 'Verarbeitung...',
        'result': 'Ergebnis',
        'elapsed': 'Dauer',
        'seconds': 's',
        'filename': 'Dateiname',
        'expected': 'Erwartet',
        'total_images': '{} Bilder',
        'no_image_folder': 'Keine unterstützten Bilder gefunden',
        'no_api_key': 'Bitte ZHIPU_API_KEY Umgebungsvariable setzen',
        'api_error': 'API-Aufruf fehlgeschlagen',
        'raw_answer': 'Modellantwort',
        'parse_result': 'Ergebnis',
        'allowed': 'Erlaubt',
        'denied': 'Verboten',
        'match': 'Treffer',
        'mismatch': 'Kein Treffer',
        'unknown': 'Unbekannt',
        'select_image_first': 'Bitte zuerst ein Bild auswählen',
        'system_prompt': 'System-Prompt',
        'user_prompt': 'Benutzer-Prompt',
        'reasoning_label': 'Reasoning (glm-4v-plus)',
        'ocr_label': 'OCR (glm-4v-flash)',
        'model_label': 'Modell',
        'language_label': 'Sprache',
        'drop_here': 'Ordner zum Laden von Bildern auswählen',
        'api_key': 'API-Schlüssel',
        'api_key_required': 'Bitte API-Schlüssel eingeben',
        'show': 'Zeigen',
        'hide': 'Verbergen',
        'remember': 'Merken',
        'key_saved': 'API-Schlüssel in Datei gespeichert',
        'wsl_intro': 'Tipp: Kopieren Sie den Schlüssel aus WSL hierher',
        'key_from_env': 'API-Schlüssel aus Windows-Umgebungsvariable geladen',
        'key_from_wsl': 'API-Schlüssel aus WSL-Umgebungsvariable geladen',
    }
}

# ============================================================
# 模型配置（提示词始终中文）
# ============================================================
MODEL_CONFIGS = {
    'reasoning': {
        'name': 'glm-4v-plus',
        'system_prompt': "判断图片中的自行车是否有牌照。只回答'有牌照'或'没有牌照'，不要输出其他内容。",
        'user_prompt': "这张图片中的自行车有牌照吗？",
    },
    'ocr': {
        'name': 'glm-4v-flash',
        'system_prompt': "你是一个图像识别助手。请仔细观察图片，用一句话描述图片中的主要内容和细节。",
        'user_prompt': "请用一句话描述这张图片的内容",
    }
}

# 语言下拉框映射
LANG_MAP = {'中文': 'zh', 'Deutsch': 'de', 'English': 'en'}
LANG_REVERSE = {'zh': '中文', 'en': 'English', 'de': 'Deutsch'}

# API Key 持久化文件
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.find_bike_config.json')
DEBUG_LOG = os.path.join(os.path.expanduser('~'), '.find_bike_debug.log')


# ============================================================
# 工具函数
# ============================================================
def get_expected_from_filename(filename):
    if not filename:
        return None
    base = Path(filename).name
    if base.startswith('是'):
        return True
    elif base.startswith('否'):
        return False
    return None


def get_supported_images(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        return []
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(folder.glob(f"*{ext}"))
        images.extend(folder.glob(f"*{ext.upper()}"))
    seen = set()
    unique = []
    for img in images:
        key = img.name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(img)
    return sorted(unique)


# ============================================================
# GUI 主类
# ============================================================
class BikeDetectorApp:
    def __init__(self, root):
        self.root = root
        self.lang = 'zh'
        self.current_model_key = 'reasoning'
        self.image_files = []
        self.selected_image = None
        self.thumbnails = []
        self.thumbnail_labels = []
        self._preview_photo = None
        self._lang_updating = False
        self.api_key = ''
        self.remember_key = tk.BooleanVar(value=False)
        self._detect_source = None

        self._load_config()
        if not self.api_key:
            self._auto_detect_api_key()

        self.root.title(self.tr('title'))
        self.root.geometry("1100x760")
        self.root.minsize(900, 620)

        self._build_ui()

        # 加载保存的 API Key
        if self.api_key:
            self.api_key_var.set(self.api_key)
            if self._detect_source == 'env':
                self.lbl_status.config(text=self.tr('key_from_env'), foreground='green')
            elif self._detect_source == 'wsl':
                self.lbl_status.config(text=self.tr('key_from_wsl'), foreground='green')

        self._update_all_text()

    def tr(self, key, *args):
        text = TEXTS[self.lang].get(key, key)
        if args:
            text = text.format(*args)
        return text

    # ============================================================
    # UI 构建
    # ============================================================
    def _build_ui(self):
        root = self.root

        # ---- 顶部工具栏 ----
        toolbar = ttk.Frame(root)
        toolbar.pack(fill=tk.X, padx=8, pady=(6, 2))

        # 语言选择
        self.lang_var = tk.StringVar(value='中文')
        cb_lang = ttk.Combobox(toolbar, textvariable=self.lang_var,
                               values=['中文', 'Deutsch', 'English'],
                               state='readonly', width=8)
        cb_lang.pack(side=tk.LEFT, padx=(0, 16))
        cb_lang.bind('<<ComboboxSelected>>', self._on_lang_change)
        self._cb_lang = cb_lang

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        # 模型选择（RadioButton）
        self.lbl_model_title = ttk.Label(toolbar, font=('', 9, 'bold'))
        self.lbl_model_title.pack(side=tk.LEFT, padx=(4, 4))

        self.model_var = tk.StringVar(value='reasoning')
        self.model_var.trace_add('write', self._on_model_trace)

        self.rb_reasoning = ttk.Radiobutton(toolbar, variable=self.model_var, value='reasoning')
        self.rb_reasoning.pack(side=tk.LEFT, padx=(0, 8))

        self.rb_ocr = ttk.Radiobutton(toolbar, variable=self.model_var, value='ocr')
        self.rb_ocr.pack(side=tk.LEFT, padx=(0, 16))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        # 选择文件夹
        self.btn_folder = ttk.Button(toolbar, command=self._select_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=(4, 8))

        # 图片计数
        self.lbl_count = ttk.Label(toolbar)
        self.lbl_count.pack(side=tk.LEFT, padx=(4, 0))

        # ---- API Key 区（右侧） ----
        # 记住复选框
        self.chk_remember = ttk.Checkbutton(toolbar, variable=self.remember_key,
                                            command=self._on_remember_toggle)
        self.chk_remember.pack(side=tk.RIGHT, padx=(4, 0))

        # 显示/隐藏按钮
        self.btn_show_key = ttk.Button(toolbar, width=4, command=self._toggle_key_visibility)
        self.btn_show_key.pack(side=tk.RIGHT, padx=(2, 0))

        # API Key 输入框
        self.api_key_var = tk.StringVar()
        self.entry_api_key = ttk.Entry(toolbar, textvariable=self.api_key_var,
                                       show='*', width=28)
        self.entry_api_key.pack(side=tk.RIGHT, padx=(2, 0))
        self.entry_api_key.bind('<KeyRelease>', self._on_api_key_changed)

        # API Key 标签
        self.lbl_api_key = ttk.Label(toolbar, font=('', 9, 'bold'))
        self.lbl_api_key.pack(side=tk.RIGHT, padx=(16, 2))

        # ---- 主内容区 ----
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # 左侧 - 图片列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 4))
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(left_frame, bg='#e8e8e8', highlightthickness=0)
        self.scrollbar_v = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.thumb_frame = ttk.Frame(self.canvas)

        self.thumb_frame.bind('<Configure>', self._on_thumb_frame_configure)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.thumb_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar_v.set)

        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.scrollbar_v.grid(row=0, column=1, sticky=tk.NS)

        self.canvas.bind('<Enter>', self._bind_mousewheel)
        self.canvas.bind('<Leave>', self._unbind_mousewheel)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # 空状态提示
        self._show_empty_thumb_frame()

        # 右侧 - 预览区
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=(4, 0))
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=0)
        right_frame.columnconfigure(0, weight=1)

        preview_container = ttk.Frame(right_frame, relief=tk.SUNKEN, borderwidth=1)
        preview_container.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 4))
        preview_container.rowconfigure(0, weight=1)
        preview_container.columnconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_container, anchor=tk.CENTER, background='#f5f5f5')
        self.preview_label.grid(row=0, column=0, sticky=tk.NSEW)

        info_frame = ttk.Frame(right_frame)
        info_frame.grid(row=1, column=0, sticky=tk.EW)

        self.lbl_filename_title = ttk.Label(info_frame, font=('', 9, 'bold'))
        self.lbl_filename_title.pack(anchor=tk.W)
        self.lbl_filename = ttk.Label(info_frame, wraplength=350)
        self.lbl_filename.pack(anchor=tk.W)

        self.lbl_expected_title = ttk.Label(info_frame, font=('', 9, 'bold'))
        self.lbl_expected_title.pack(anchor=tk.W, pady=(6, 0))
        self.lbl_expected = ttk.Label(info_frame)
        self.lbl_expected.pack(anchor=tk.W)

        # ---- 底部 ----
        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(fill=tk.BOTH, padx=8, pady=(6, 6))

        # 系统提示词
        self.lbl_sys_title = ttk.Label(bottom_frame, font=('', 9, 'bold'))
        self.lbl_sys_title.pack(anchor=tk.W)
        self.sys_prompt_text = tk.Text(bottom_frame, height=3, wrap=tk.WORD, font=('', 9))
        self.sys_prompt_text.pack(fill=tk.X, pady=(0, 4))
        self.sys_prompt_text.insert('1.0', MODEL_CONFIGS['reasoning']['system_prompt'])

        # 用户提示词
        self.lbl_usr_title = ttk.Label(bottom_frame, font=('', 9, 'bold'))
        self.lbl_usr_title.pack(anchor=tk.W)
        self.usr_prompt_text = tk.Text(bottom_frame, height=2, wrap=tk.WORD, font=('', 9))
        self.usr_prompt_text.pack(fill=tk.X, pady=(0, 4))
        self.usr_prompt_text.insert('1.0', MODEL_CONFIGS['reasoning']['user_prompt'])

        # 按钮 + 状态行
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X, pady=(2, 4))

        self.btn_start = ttk.Button(btn_frame, command=self._start_recognition)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = ttk.Button(btn_frame, command=self._clear_result)
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 16))

        self.lbl_status = ttk.Label(btn_frame, foreground='gray')
        self.lbl_status.pack(side=tk.LEFT)

        # 结果区
        self.lbl_result_title = ttk.Label(bottom_frame, font=('', 9, 'bold'))
        self.lbl_result_title.pack(anchor=tk.W)

        result_frame = ttk.Frame(bottom_frame)
        result_frame.pack(fill=tk.BOTH, expand=True)
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD,
                                   state=tk.DISABLED, font=('Consolas', 9))
        scrollbar_r = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar_r.set)
        self.result_text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar_r.grid(row=0, column=1, sticky=tk.NS)

    # ============================================================
    # 鼠标滚轮
    # ============================================================
    def _bind_mousewheel(self, event):
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    # ============================================================
    # 缩略图 / Canvas 事件
    # ============================================================
    def _on_canvas_configure(self, event):
        canvas_width = event.width
        if canvas_width > 10 and self.image_files:
            self._relayout_thumbnails(canvas_width)

    def _on_thumb_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        # 设置 canvas 内部frame宽度等于canvas宽度
        canvas_width = self.canvas.winfo_width()
        if canvas_width > 10:
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _show_empty_thumb_frame(self):
        for w in self.thumb_frame.winfo_children():
            w.destroy()
        self.thumbnails.clear()
        self.thumbnail_labels.clear()
        lbl = ttk.Label(self.thumb_frame, foreground='gray', anchor=tk.CENTER)
        lbl.pack(expand=True, fill=tk.BOTH)
        self._empty_label = lbl
        self._update_empty_label()
        # 强制刷新滚动区域
        self.thumb_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _update_empty_label(self):
        if hasattr(self, '_empty_label') and self._empty_label.winfo_exists():
            self._empty_label.config(text=self.tr('drop_here'))

    def _relayout_thumbnails(self, canvas_width):
        if not self.thumbnail_labels:
            return
        thumb_w = 130
        cols = max(1, (canvas_width - 10) // thumb_w)
        for i, lbl in enumerate(self.thumbnail_labels):
            lbl.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky=tk.NSEW)
        self.thumb_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _load_thumbnails(self):
        for w in self.thumb_frame.winfo_children():
            w.destroy()
        self.thumbnails.clear()
        self.thumbnail_labels.clear()

        if not self.image_files:
            self._show_empty_thumb_frame()
            return

        thumb_size = (120, 120)
        canvas_width = max(self.canvas.winfo_width(), 200)
        thumb_w = 130
        cols = max(1, (canvas_width - 10) // thumb_w)

        for i, img_path in enumerate(self.image_files):
            try:
                img = Image.open(img_path)
                img.thumbnail(thumb_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)

                container = ttk.Frame(self.thumb_frame)
                container.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky=tk.NSEW)

                lbl_img = ttk.Label(container, image=photo, relief=tk.RAISED, cursor='hand2')
                lbl_img.pack()
                lbl_img.bind('<Button-1>', lambda e, idx=i: self._on_thumbnail_click(idx))

                # 文件名标签（截断）
                name = img_path.name
                display_name = name if len(name) <= 18 else name[:15] + '...'
                lbl_name = ttk.Label(container, text=display_name, font=('', 7), wraplength=120)
                lbl_name.pack()

                self.thumbnail_labels.append(container)
            except Exception:
                pass

        self.thumb_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    # ============================================================
    # 事件处理
    # ============================================================
    def _on_lang_change(self, event=None):
        lang_display = self.lang_var.get()
        new_lang = LANG_MAP.get(lang_display, 'zh')
        if new_lang != self.lang:
            self.lang = new_lang
            self._update_all_text()

    def _update_all_text(self):
        self._lang_updating = True
        self.root.title(self.tr('title'))
        self.btn_folder.config(text=self.tr('select_folder'))
        self.lbl_sys_title.config(text=self.tr('system_prompt') + ':')
        self.lbl_usr_title.config(text=self.tr('user_prompt') + ':')
        self.btn_start.config(text=self.tr('start'))
        self.btn_clear.config(text=self.tr('clear'))
        self.lbl_status.config(text=self.tr('status_ready'))
        self.lbl_result_title.config(text=self.tr('result') + ':')
        self.lbl_filename_title.config(text=self.tr('filename') + ':')
        self.lbl_expected_title.config(text=self.tr('expected') + ':')
        self.lbl_model_title.config(text=self.tr('model_label') + ':')
        self.rb_reasoning.config(text=self.tr('reasoning_label'))
        self.rb_ocr.config(text=self.tr('ocr_label'))
        self.lbl_api_key.config(text=self.tr('api_key') + ':')
        self.chk_remember.config(text=self.tr('remember'))
        current_show = self.entry_api_key.cget('show')
        self.btn_show_key.config(
            text=self.tr('show') if current_show == '*' else self.tr('hide'))

        if self.image_files:
            self.lbl_count.config(text=self.tr('total_images', len(self.image_files)))
        else:
            self.lbl_count.config(text='')

        # 语言下拉框显示当前语言
        self._cb_lang.set(LANG_REVERSE.get(self.lang, '中文'))

        self._update_empty_label()
        # 刷新预览区文字
        self._refresh_preview_text()
        self._lang_updating = False

    def _on_model_trace(self, *args):
        if self._lang_updating:
            return
        self.current_model_key = self.model_var.get()
        if self.current_model_key not in MODEL_CONFIGS:
            return
        config = MODEL_CONFIGS[self.current_model_key]
        self.sys_prompt_text.delete('1.0', tk.END)
        self.sys_prompt_text.insert('1.0', config['system_prompt'])
        self.usr_prompt_text.delete('1.0', tk.END)
        self.usr_prompt_text.insert('1.0', config['user_prompt'])

    def _select_folder(self):
        folder = filedialog.askdirectory(title=self.tr('select_folder'))
        if not folder:
            return

        image_files = get_supported_images(folder)
        if not image_files:
            messagebox.showinfo(self.tr('title'), self.tr('no_image_folder'))
            return

        self.image_files = image_files
        self.selected_image = None
        self._load_thumbnails()
        self.lbl_count.config(text=self.tr('total_images', len(self.image_files)))
        self._clear_preview()

    def _on_thumbnail_click(self, index):
        if 0 <= index < len(self.image_files):
            self.selected_image = self.image_files[index]
            self._show_preview()

    def _show_preview(self):
        if not self.selected_image:
            self._clear_preview()
            return

        try:
            img = Image.open(self.selected_image)
            max_size = (320, 320)
            img.thumbnail(max_size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._preview_photo = photo

            self.preview_label.config(image=photo, background='#f5f5f5')
            self.lbl_filename.config(text=self.selected_image.name)

            expected = get_expected_from_filename(self.selected_image.name)
            if expected is True:
                self.lbl_expected.config(text=self.tr('allowed'), foreground='green')
            elif expected is False:
                self.lbl_expected.config(text=self.tr('denied'), foreground='red')
            else:
                self.lbl_expected.config(text=self.tr('unknown'), foreground='gray')
        except Exception:
            self._clear_preview()

    def _clear_preview(self):
        self.preview_label.config(image='', background='#f5f5f5')
        self._preview_photo = None
        self.lbl_filename.config(text='')
        self.lbl_expected.config(text='')

    def _refresh_preview_text(self):
        if self.selected_image:
            self._show_preview()

    # ============================================================
    # API Key 管理
    # ============================================================
    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    if cfg.get('remember') and cfg.get('api_key'):
                        self.api_key = cfg['api_key']
                        self.remember_key.set(True)
        except Exception:
            pass

    def _auto_detect_api_key(self):
        key = os.getenv('ZHIPU_API_KEY', '').strip()
        if key:
            self.api_key = key
            self._detect_source = 'env'
            return
        try:
            result = subprocess.run(
                ['wsl.exe', 'bash', '-c', 'echo $ZHIPU_API_KEY'],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            key = result.stdout.strip()
            if key and result.returncode == 0:
                self.api_key = key
                self._detect_source = 'wsl'
        except Exception:
            pass

    def _save_config(self, api_key, remember):
        cfg = {'api_key': api_key if remember else '', 'remember': remember}
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def _on_api_key_changed(self, event=None):
        self.api_key = self.api_key_var.get().strip()
        if self.remember_key.get():
            self._save_config(self.api_key, True)

    def _on_remember_toggle(self):
        remember = self.remember_key.get()
        key = self.api_key_var.get().strip()
        self._save_config(key, remember)

    def _toggle_key_visibility(self):
        current_show = self.entry_api_key.cget('show')
        if current_show == '*':
            self.entry_api_key.config(show='')
            self.btn_show_key.config(text=self.tr('hide'))
        else:
            self.entry_api_key.config(show='*')
            self.btn_show_key.config(text=self.tr('show'))

    # ============================================================
    # 日志与诊断
    # ============================================================
    def _mask_key(self, key):
        if len(key) <= 8:
            return '****'
        return key[:4] + '****' + key[-4:]

    def _log(self, msg):
        ts = datetime.now().strftime('%H:%M:%S')
        line = f"[{ts}] {msg}"
        with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

        def _append():
            try:
                was_disabled = self.result_text.cget('state') == tk.DISABLED
                if was_disabled:
                    self.result_text.config(state=tk.NORMAL)
                self.result_text.insert(tk.END, line + '\n')
                self.result_text.see(tk.END)
                if was_disabled:
                    self.result_text.config(state=tk.DISABLED)
            except Exception:
                pass
        self.root.after(0, _append)

    # ============================================================
    # 识别逻辑
    # ============================================================
    def _start_recognition(self):
        if not self.selected_image:
            messagebox.showwarning(self.tr('title'), self.tr('select_image_first'))
            return

        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning(self.tr('title'), self.tr('api_key_required'))
            return
        self.api_key = api_key

        system_prompt = self.sys_prompt_text.get('1.0', tk.END).strip()
        user_prompt = self.usr_prompt_text.get('1.0', tk.END).strip()
        model_name = MODEL_CONFIGS[self.current_model_key]['name']
        image_path = str(self.selected_image)

        self.btn_start.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        self.lbl_status.config(text=self.tr('status_processing'), foreground='blue')
        self._clear_result()

        def _run():
            self._log("=" * 50)
            self._log(f"  模型: {model_name}")
            self._log(f"  API Key: {self._mask_key(api_key)}")
            self._log(f"  图片: {os.path.basename(image_path)}")
            self._log(f"  系统提示词: {system_prompt[:60]}...")
            self._log(f"  用户提示词: {user_prompt}")
            self._log(f"  开始调用 API...")

            start_time = time.time()
            try:
                client = ZhipuClient(api_key=api_key, model_name=model_name, timeout=120)
                success, answer, reasoning, elapsed = client.chat_with_image(
                    image_path, system_prompt, user_prompt
                )

                if not success:
                    err_msg = reasoning if reasoning else answer
                    self._log(f"  API 调用失败, 耗时 {elapsed:.2f}s")
                    self._log(f"  错误: {err_msg}")
                    self.root.after(0, lambda: self._finish_recognition(
                        error=err_msg, elapsed=elapsed))
                    return

                self._log(f"  API 调用成功, 耗时 {elapsed:.2f}s")
                self._log(f"  原始回答 ({len(answer)}字): {answer[:300]}")

                if self.current_model_key == 'ocr':
                    is_allowed, reasoning_text = parse_ocr_result(answer)
                else:
                    is_allowed, reasoning_text = parse_bicycle_response(answer)

                self._log(f"  解析结果: {'允许' if is_allowed else '不允许'}")

                expected = get_expected_from_filename(self.selected_image.name)
                if expected is not None:
                    exp_str = '允许' if expected else '不允许'
                    match = '匹配' if is_allowed == expected else '不匹配'
                    self._log(f"  期望: {exp_str} -> {match}")

                self.root.after(0, lambda: self._finish_recognition(
                    answer=answer, is_allowed=is_allowed,
                    elapsed=elapsed, expected=expected))
            except Exception as e:
                elapsed = time.time() - start_time
                tb = traceback.format_exc()
                self._log(f"  异常, 耗时 {elapsed:.2f}s")
                self._log(f"  错误: {e}")
                self.root.after(0, lambda: self._finish_recognition(
                    error=str(e), elapsed=elapsed, traceback_text=tb))

        threading.Thread(target=_run, daemon=True).start()

    def _finish_recognition(self, answer=None, is_allowed=None, elapsed=0,
                            expected=None, error=None, traceback_text=None):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        self.lbl_status.config(
            text=f"{self.tr('elapsed')}: {elapsed:.2f}{self.tr('seconds')}",
            foreground='black')

        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)

        if error:
            self.result_text.insert(tk.END, f"[{self.tr('api_error')}] {error}\n",
                                    'error')
            self.result_text.tag_config('error', foreground='red')
            if traceback_text:
                self.result_text.insert(tk.END, f"\n{traceback_text}\n")
            self.result_text.config(state=tk.DISABLED)
            return

        self.result_text.insert(tk.END,
            f"{self.tr('elapsed')}: {elapsed:.2f} {self.tr('seconds')}\n\n")

        self.result_text.insert(tk.END,
            f"━━━ {self.tr('raw_answer')} ━━━\n")
        self.result_text.insert(tk.END, f"{answer}\n\n")

        result_str = self.tr('allowed') if is_allowed else self.tr('denied')
        result_color = 'green' if is_allowed else 'red'
        self.result_text.insert(tk.END,
            f"━━━ {self.tr('parse_result')} ━━━\n", 'header')
        self.result_text.insert(tk.END, f"{result_str}\n", result_color)
        self.result_text.tag_config('header', font=('Consolas', 9, 'bold'))
        self.result_text.tag_config('green', foreground='green')
        self.result_text.tag_config('red', foreground='red')

        if expected is not None:
            match_str = self.tr('match') if is_allowed == expected else self.tr('mismatch')
            match_color = 'green' if is_allowed == expected else 'red'
            self.result_text.insert(tk.END, f"\n{match_str}\n", match_color)

        self.result_text.config(state=tk.DISABLED)

    def _clear_result(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.lbl_status.config(text=self.tr('status_ready'), foreground='gray')


# ============================================================
# 入口
# ============================================================
def main():
    root = tk.Tk()
    BikeDetectorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

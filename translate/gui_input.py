import os
import queue
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from fetcher import read_file, fetch_url
from translator import (LANGUAGES, GOOGLE_CODES, ARGOS_CODES, TranslationError,
                        make_translator, translate_lines, download_argos_model,
                        argos_installed_pairs, argos_has_engine)


class InputPage(ttk.Frame):
    def __init__(self, parent, app, fixed_engine=None):
        super().__init__(parent)
        self.app = app
        self.fixed_engine = fixed_engine
        self.input_var = tk.StringVar()
        self.src_lang = tk.StringVar(value='自动')
        self.tgt_lang = tk.StringVar(value='中文')
        self.engine = tk.StringVar(value=fixed_engine or 'online')
        self.status_var = tk.StringVar(value='就绪')
        self._cancel = None
        self._build()
        self.engine.trace_add('write', lambda *a: self._on_engine_change())
        self._on_engine_change()
        self._refresh_offline_status()

    def _build(self):
        pad = {'padx': 14, 'pady': 6}

        src_frame = ttk.LabelFrame(self, text='输入来源（自动识别本地文件或网页链接）')
        src_frame.pack(fill='x', **pad)
        src_frame.columnconfigure(0, weight=1)
        self.input_entry = ttk.Entry(src_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=0, columnspan=2, sticky='ew',
                              padx=5, pady=3)
        self.browse_btn = ttk.Button(src_frame, text='浏览...',
                                     command=self._browse)
        self.browse_btn.grid(row=0, column=2, padx=5, pady=3)
        ttk.Label(src_frame, text='支持本地文件路径或 http(s) 链接，自动识别',
                  foreground='#777').grid(row=1, column=0, columnspan=3,
                                          sticky='w', padx=6, pady=(0, 4))

        lang_frame = ttk.LabelFrame(self, text='翻译设置')
        lang_frame.pack(fill='x', **pad)
        lang_frame.columnconfigure(3, weight=1)
        ttk.Label(lang_frame, text='原文语言').grid(row=0, column=0,
                                                   sticky='w', padx=6, pady=4)
        self.src_menu = ttk.OptionMenu(lang_frame, self.src_lang, '自动',
                                       *(['自动'] + LANGUAGES))
        self.src_menu.grid(row=0, column=1, sticky='w', pady=4)
        ttk.Label(lang_frame, text='目标语言').grid(row=0, column=2,
                                                   sticky='w', padx=16, pady=4)
        self.tgt_menu = ttk.OptionMenu(lang_frame, self.tgt_lang, '中文',
                                       *LANGUAGES)
        self.tgt_menu.grid(row=0, column=3, sticky='w', pady=4)
        ttk.Label(lang_frame,
                  text='（原文语言用于离线翻译；在线翻译自动检测）',
                  foreground='#777').grid(row=1, column=0, columnspan=4,
                                          sticky='w', padx=6, pady=(0, 4))

        eng_frame = ttk.LabelFrame(self, text='翻译引擎')
        eng_frame.pack(fill='x', **pad)
        eng_frame.columnconfigure(0, weight=1)
        self.online_radio = ttk.Radiobutton(
            eng_frame, text='在线翻译（Google，免费，需联网）',
            variable=self.engine, value='online')
        self.online_radio.grid(row=0, column=0, sticky='w', padx=6, pady=4)
        self.offline_radio = ttk.Radiobutton(
            eng_frame, text='本地离线翻译（无需联网，首次需下载模型）',
            variable=self.engine, value='offline')
        self.offline_radio.grid(row=1, column=0, sticky='w', padx=6, pady=4)
        self.offline_status = ttk.Label(eng_frame, text='', foreground='#555')
        self.offline_status.grid(row=2, column=0, sticky='w', padx=6, pady=2)
        self.dl_btn = ttk.Button(eng_frame, text='下载离线语言模型...',
                                 command=self._open_model_dialog)
        self.dl_btn.grid(row=3, column=0, sticky='w', padx=6, pady=(2, 6))

        bottom = ttk.Frame(self)
        bottom.pack(fill='x', **pad)
        self.start_btn = ttk.Button(bottom, text='开始翻译', command=self._start)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(bottom, text='取消', command=self._cancel_now,
                                     state='disabled')
        self.cancel_btn.pack(side='left', padx=8)
        self.progress = ttk.Progressbar(bottom, mode='determinate')
        self.progress.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Label(self, textvariable=self.status_var, foreground='#333').pack(
            fill='x', **pad)

    def _browse(self):
        path = filedialog.askopenfilename(
            title='选择要翻译的文件',
            filetypes=[('文本文件', '*.txt'), ('Word 文档', '*.docx'),
                       ('PDF 文档', '*.pdf'), ('所有文件', '*.*')])
        if path:
            self.input_var.set(path)

    def _detect_source(self, text):
        if re.match(r'^(https?://|www\.)', text, re.IGNORECASE):
            return 'url'
        return 'file'

    def _on_engine_change(self):
        if self.engine.get() == 'offline':
            self.dl_btn.grid()
            self.offline_status.grid()
        else:
            self.dl_btn.grid_remove()
            self.offline_status.grid_remove()
        if self.fixed_engine:
            self.online_radio.grid_remove()
            self.offline_radio.grid_remove()

    def _refresh_offline_status(self):
        q = queue.Queue()
        self._offline_q = q

        def work():
            try:
                q.put(('ok', argos_installed_pairs()))
            except Exception:
                q.put(('err', None))

        threading.Thread(target=work, daemon=True).start()
        self.after(100, self._poll_offline)

    def _poll_offline(self):
        q = getattr(self, '_offline_q', None)
        if q is None:
            return
        try:
            kind, payload = q.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_offline)
            return
        self._offline_q = None
        if kind != 'ok':
            self.offline_status.config(text='离线引擎不可用')
            return
        pairs = payload
        if pairs is None:
            text = '离线引擎未安装'
        elif not pairs:
            text = '已安装模型：无（请先下载）'
        else:
            text = '已安装模型：' + ', '.join(pairs)
        self.offline_status.config(text=text)

    def _codes(self, engine):
        if engine == 'online':
            src = None if self.src_lang.get() == '自动' \
                else GOOGLE_CODES.get(self.src_lang.get())
            tgt = GOOGLE_CODES.get(self.tgt_lang.get())
            return src, tgt
        src = ARGOS_CODES.get(self.src_lang.get())
        tgt = ARGOS_CODES.get(self.tgt_lang.get())
        return src, tgt

    def _start(self):
        source = self.input_var.get().strip()
        if not source:
            messagebox.showwarning('未输入内容', '请输入本地文件路径或网页链接')
            return
        engine = self.fixed_engine or self.engine.get()
        src_code, tgt_code = self._codes(engine)
        if engine == 'offline':
            if not argos_has_engine():
                messagebox.showerror('离线引擎不可用',
                                     '未安装 argostranslate，请先 pip install argostranslate，'
                                     '或改用在线翻译')
                return
            if not src_code:
                messagebox.showwarning('原文语言',
                                       '离线翻译需要指定原文语言，请选择具体的原文语言')
                return
        is_url = self._detect_source(source) == 'url'
        self._run_worker(source, is_url, engine, src_code, tgt_code)

    def _set_running(self, running):
        state = 'disabled' if running else 'normal'
        for w in (self.input_entry, self.browse_btn, self.src_menu,
                  self.tgt_menu, self.online_radio, self.offline_radio,
                  self.dl_btn, self.start_btn):
            try:
                w.config(state=state)
            except tk.TclError:
                pass
        self.cancel_btn.config(state='normal' if running else 'disabled')

    def _run_worker(self, source, is_url, engine, src_code, tgt_code):
        self._cancel = threading.Event()
        self._q = queue.Queue()
        self._set_running(True)
        self.progress.config(mode='indeterminate')
        self.progress.start(12)
        self.status_var.set('正在读取...')

        def reader():
            try:
                if self._cancel.is_set():
                    self._q.put(('fail', TranslationError('已取消')))
                    return
                if is_url:
                    text = fetch_url(source)
                else:
                    text = read_file(source)
                lines = text.split('\n')
                if not any(l.strip() for l in lines):
                    self._q.put(('fail', TranslationError('未能从输入中获取可翻译的文本')))
                    return
                if self._cancel.is_set():
                    self._q.put(('fail', TranslationError('已取消')))
                    return
                self._q.put(('read_ok', (lines, engine, src_code, tgt_code)))
            except Exception as e:
                self._q.put(('fail', e))

        threading.Thread(target=reader, daemon=True).start()
        self.after(100, self._poll_read)

    def _poll_read(self):
        if self._cancel is None:
            return
        try:
            while True:
                kind, payload = self._q.get_nowait()
                if kind == 'fail':
                    self._fail(payload)
                    return
                if kind == 'read_ok':
                    self._start_translate(payload)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_read)

    def _start_translate(self, payload):
        lines, engine, src_code, tgt_code = payload
        try:
            self.progress.stop()
        except Exception:
            pass
        self.progress.config(mode='determinate', maximum=1, value=0)
        self.status_var.set('正在翻译...')
        self._q2 = queue.Queue()

        def on_progress(done, total):
            self._q2.put(('progress', (done, total)))

        def worker():
            try:
                translator = make_translator(engine, src_code, tgt_code)
                result = translate_lines(lines, translator, on_progress, self._cancel)
                self._q2.put(('done', (lines, result)))
            except Exception as e:
                self._q2.put(('fail', e))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll_translate)

    def _poll_translate(self):
        if self._cancel is None:
            return
        try:
            while True:
                kind, payload = self._q2.get_nowait()
                if kind == 'progress':
                    done, total = payload
                    self._tick(done, total)
                elif kind == 'done':
                    lines, result = payload
                    self._done(lines, result)
                    return
                elif kind == 'fail':
                    self._fail(payload)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_translate)

    def _tick(self, done, total):
        self.progress['maximum'] = max(total, 1)
        self.progress['value'] = done
        self.status_var.set(f'正在翻译... {done}/{total}')

    def _done(self, lines, result):
        self._reset_ui()
        self.status_var.set(f'翻译完成，共 {len(result)} 行')
        self.app.open_editor(lines, result)

    def _fail(self, e):
        self._reset_ui()
        self.status_var.set('翻译失败')
        messagebox.showerror('翻译失败', str(e))

    def _cancel_now(self):
        if self._cancel:
            self._cancel.set()
        self.status_var.set('正在取消...')

    def _reset_ui(self):
        self._cancel = None
        self._set_running(False)
        try:
            self.progress.stop()
            self.progress.config(mode='determinate', maximum=1, value=0)
        except Exception:
            pass

    def _open_model_dialog(self):
        win = tk.Toplevel(self)
        win.title('下载离线语言模型')
        win.geometry('380x260')
        win.transient(self)
        win.resizable(False, False)
        from_var = tk.StringVar(value='中文')
        to_var = tk.StringVar(value='英文')
        body = ttk.Frame(win, padding=16)
        body.pack(fill='both', expand=True)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text='原文语言').grid(row=0, column=0, sticky='w', pady=4)
        ttk.OptionMenu(body, from_var, '中文', *LANGUAGES).grid(
            row=0, column=1, sticky='ew', pady=4)
        ttk.Label(body, text='目标语言').grid(row=1, column=0, sticky='w', pady=4)
        ttk.OptionMenu(body, to_var, '英文', *LANGUAGES).grid(
            row=1, column=1, sticky='ew', pady=4)
        status = ttk.Label(body, text='', foreground='#555', wraplength=320)
        status.grid(row=3, column=0, columnspan=2, sticky='w', pady=(8, 0))
        bar = ttk.Progressbar(body, mode='indeterminate')
        dl_btn = ttk.Button(body, text='开始下载')

        def _poll(q):
            last = None
            try:
                while True:
                    item = q.get_nowait()
                    if item[0] == 'progress':
                        last = item[1]
                    else:
                        _finish(item[1])
                        return
            except queue.Empty:
                pass
            if last is not None:
                done, total = last
                try:
                    if total:
                        if bar['mode'] != 'determinate':
                            bar.stop()
                            bar.config(mode='determinate',
                                       maximum=total, value=done)
                        bar.config(value=done)
                        status.config(
                            text=f'正在下载... {done / 1048576:.1f} / '
                                 f'{total / 1048576:.1f} MB')
                    else:
                        status.config(text=f'正在下载... {done / 1048576:.1f} MB')
                except tk.TclError:
                    pass
            self.after(100, lambda: _poll(q))

        def _finish(result):
            ok, msg = result
            try:
                bar.stop()
                bar.config(mode='indeterminate', value=0)
                bar.grid_remove()
                status.config(text=msg)
                dl_btn.config(state='normal')
            except tk.TclError:
                pass
            self._set_running(False)
            if ok:
                self._refresh_offline_status()
            elif win.winfo_exists():
                messagebox.showerror('下载失败', msg, parent=win)

        def go():
            fc = ARGOS_CODES.get(from_var.get())
            tc = ARGOS_CODES.get(to_var.get())
            if not fc or not tc:
                messagebox.showerror('错误', '无效的语言选择', parent=win)
                return
            bar.grid(row=2, column=0, columnspan=2, sticky='ew', pady=6)
            bar.start(12)
            dl_btn.config(state='disabled')
            self._set_running(True)
            status.config(text=f'正在下载 {from_var.get()}→{to_var.get()} 模型，'
                               '可能耗时数分钟...')
            q = queue.Queue()

            def worker():
                try:
                    def on_progress(done, total):
                        q.put(('progress', (done, total)))
                    result = download_argos_model(fc, tc, on_progress)
                    if result == 'already':
                        q.put(('done', (True,
                                        f'{from_var.get()}→{to_var.get()} '
                                        '模型已安装，无需重复下载')))
                    else:
                        q.put(('done', (True, '下载并安装完成')))
                except Exception as e:
                    q.put(('done', (False, f'下载失败: {e}')))

            threading.Thread(target=worker, daemon=True).start()
            self.after(100, lambda: _poll(q))

        dl_btn.config(command=go)
        dl_btn.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        win.wait_visibility()
        win.grab_set()

    def on_show(self):
        self._refresh_offline_status()

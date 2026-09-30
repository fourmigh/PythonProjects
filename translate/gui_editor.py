import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from aligner import AlignPair, token_at
from output import export_lines


class EditorPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pairs = []
        self.status_var = tk.StringVar(value='')
        self._hover_job = None
        self._edit_job = None
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill='x', padx=8, pady=6)
        ttk.Button(top, text='← 返回', command=self.app.show_input).pack(side='left')
        ttk.Label(top, text='悬停单词可联动高亮，左右两栏均可手动编辑').pack(
            side='left', padx=12)
        ttk.Label(top, textvariable=self.status_var, foreground='#777').pack(
            side='left', padx=4)
        ttk.Button(top, text='导出对照文件', command=self._export).pack(side='right')

        main = ttk.Frame(self)
        main.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        main.rowconfigure(1, weight=1)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text='原文（可编辑）').grid(row=0, column=0, sticky='w')
        ttk.Label(main, text='译文（可编辑）').grid(row=0, column=1, sticky='w')

        src_frame = ttk.Frame(main)
        src_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 4))
        tgt_frame = ttk.Frame(main)
        tgt_frame.grid(row=1, column=1, sticky='nsew', padx=(4, 0))
        src_frame.rowconfigure(0, weight=1)
        src_frame.columnconfigure(0, weight=1)
        tgt_frame.rowconfigure(0, weight=1)
        tgt_frame.columnconfigure(0, weight=1)

        font = ('Microsoft YaHei UI', 11)
        self.src_text = tk.Text(src_frame, wrap='none', undo=True, font=font)
        self.tgt_text = tk.Text(tgt_frame, wrap='none', undo=True, font=font)
        self.src_text.grid(row=0, column=0, sticky='nsew')
        self.tgt_text.grid(row=0, column=0, sticky='nsew')

        src_xsb = ttk.Scrollbar(src_frame, orient='horizontal',
                                command=self.src_text.xview)
        src_xsb.grid(row=1, column=0, sticky='ew')
        tgt_xsb = ttk.Scrollbar(tgt_frame, orient='horizontal',
                                command=self.tgt_text.xview)
        tgt_xsb.grid(row=1, column=0, sticky='ew')
        self.src_text.config(xscrollcommand=src_xsb.set)
        self.tgt_text.config(xscrollcommand=tgt_xsb.set)

        sb = ttk.Scrollbar(main, orient='vertical', command=self._scroll_both)
        sb.grid(row=1, column=2, sticky='ns')
        self._sb = sb
        self.src_text.config(yscrollcommand=self._update_sb)
        self.tgt_text.config(yscrollcommand=self._update_sb)

        for w in (self.src_text, self.tgt_text):
            w.tag_configure('self_hit', background='#ffe08a')
            w.tag_configure('peer_hit', background='#8ec6ff')
            w.tag_configure('zebra', background='#f4f6f8')

        self.src_text.bind('<Motion>', lambda e: self._on_motion('src', e))
        self.tgt_text.bind('<Motion>', lambda e: self._on_motion('tgt', e))
        self.src_text.bind('<Leave>', lambda e: self._clear_hover())
        self.tgt_text.bind('<Leave>', lambda e: self._clear_hover())
        for w in (self.src_text, self.tgt_text):
            w.bind('<KeyRelease>', lambda e: self._on_edit())
            w.bind('<MouseWheel>', self._on_wheel)

    def on_show(self):
        self.src_text.mark_set('insert', '1.0')
        self.src_text.see('1.0')
        self.src_text.focus_set()

    def set_content(self, src_lines, tgt_lines):
        self.src_text.delete('1.0', 'end')
        self.tgt_text.delete('1.0', 'end')
        self.src_text.insert('1.0', '\n'.join(src_lines))
        self.tgt_text.insert('1.0', '\n'.join(tgt_lines))
        self._apply_zebra()
        self.pairs = []
        self._clear_hover()
        self.status_var.set('正在建立词对齐...')
        self._pair_q = queue.Queue()

        def worker():
            n = max(len(src_lines), len(tgt_lines))
            pairs = []
            for i in range(n):
                s = src_lines[i] if i < len(src_lines) else ''
                t = tgt_lines[i] if i < len(tgt_lines) else ''
                pairs.append(AlignPair(s, t))
            self._pair_q.put(pairs)

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll_pairs)

    def _poll_pairs(self):
        q = getattr(self, '_pair_q', None)
        if q is None:
            return
        try:
            pairs = q.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_pairs)
            return
        self._pair_q = None
        self.pairs = pairs
        self.status_var.set('')

    # ---------- zebra striping ----------

    def _apply_zebra(self):
        for w in (self.src_text, self.tgt_text):
            w.tag_remove('zebra', '1.0', 'end')
            n = int(w.index('end-1c').split('.')[0])
            for ln in range(2, n + 1, 2):
                w.tag_add('zebra', '{}.0'.format(ln), '{}.end'.format(ln))
            w.tag_raise('sel')
            w.tag_raise('peer_hit')
            w.tag_raise('self_hit')

    # ---------- scrolling ----------

    def _scroll_both(self, *args):
        self.src_text.yview(*args)
        self.tgt_text.yview(*args)

    def _update_sb(self, *args):
        self._sb.set(*args)

    def _on_wheel(self, event):
        delta = int(-1 * (event.delta / 120))
        self.src_text.yview_scroll(delta, 'units')
        self.tgt_text.yview_scroll(delta, 'units')
        return 'break'

    # ---------- hover highlight ----------

    def _on_motion(self, which, event):
        if self._hover_job:
            self.after_cancel(self._hover_job)
        self._hover_job = self.after(60, self._process_hover, which, event.x, event.y)

    def _process_hover(self, which, x, y):
        self._hover_job = None
        widget = self.src_text if which == 'src' else self.tgt_text
        idx = widget.index('@{},{}'.format(x, y))
        line_str, col_str = idx.split('.')
        line = int(line_str)
        col = int(col_str)
        if line < 1 or line > len(self.pairs):
            self._clear_hover()
            return
        pair = self.pairs[line - 1]
        if which == 'src':
            ti = token_at(pair.src_tokens, col)
            if ti is None:
                self._clear_hover()
                return
            self._apply_hover(line, 'src', ti, pair.src_to_tgt.get(ti, []), pair)
        else:
            ti = token_at(pair.tgt_tokens, col)
            if ti is None:
                self._clear_hover()
                return
            self._apply_hover(line, 'tgt', ti, pair.tgt_to_src.get(ti, []), pair)

    def _apply_hover(self, line, which, tok, peers, pair):
        self._clear_hover()
        if which == 'src':
            s, e = pair.src_tokens[tok][0], pair.src_tokens[tok][1]
            self.src_text.tag_add('self_hit', '{}.{}'.format(line, s),
                                  '{}.{}'.format(line, e))
            for pt in peers:
                if pt >= len(pair.tgt_tokens):
                    continue
                s, e = pair.tgt_tokens[pt][0], pair.tgt_tokens[pt][1]
                self.tgt_text.tag_add('peer_hit', '{}.{}'.format(line, s),
                                      '{}.{}'.format(line, e))
        else:
            s, e = pair.tgt_tokens[tok][0], pair.tgt_tokens[tok][1]
            self.tgt_text.tag_add('self_hit', '{}.{}'.format(line, s),
                                  '{}.{}'.format(line, e))
            for pt in peers:
                if pt >= len(pair.src_tokens):
                    continue
                s, e = pair.src_tokens[pt][0], pair.src_tokens[pt][1]
                self.src_text.tag_add('peer_hit', '{}.{}'.format(line, s),
                                      '{}.{}'.format(line, e))

    def _clear_hover(self):
        for w in (self.src_text, self.tgt_text):
            w.tag_remove('self_hit', '1.0', 'end')
            w.tag_remove('peer_hit', '1.0', 'end')

    # ---------- editing ----------

    def _on_edit(self):
        if self._edit_job:
            self.after_cancel(self._edit_job)
        self._edit_job = self.after(300, self._recompute_current)

    def _recompute_current(self):
        self._edit_job = None
        self._clear_hover()
        n_src = int(self.src_text.index('end-1c').split('.')[0])
        n_tgt = int(self.tgt_text.index('end-1c').split('.')[0])
        n = max(n_src, n_tgt)
        while len(self.pairs) < n:
            self.pairs.append(AlignPair('', ''))
        if len(self.pairs) > n:
            self.pairs = self.pairs[:n]
        for ln in {int(self.src_text.index('insert').split('.')[0]),
                   int(self.tgt_text.index('insert').split('.')[0])}:
            if 1 <= ln <= n:
                src = self.src_text.get('{}.0'.format(ln), '{}.end'.format(ln))
                tgt = self.tgt_text.get('{}.0'.format(ln), '{}.end'.format(ln))
                self.pairs[ln - 1] = AlignPair(src, tgt)
        self._apply_zebra()

    # ---------- export ----------

    def _export(self):
        src = self.src_text.get('1.0', 'end-1c').split('\n')
        tgt = self.tgt_text.get('1.0', 'end-1c').split('\n')
        path = filedialog.asksaveasfilename(
            title='保存对照文件', defaultextension='.txt',
            initialfile='对照译文.txt', filetypes=[('文本文件', '*.txt')])
        if not path:
            return
        try:
            export_lines(src, tgt, path)
            messagebox.showinfo('导出成功', '已保存到:\n' + path)
        except Exception as e:
            messagebox.showerror('导出失败', str(e))

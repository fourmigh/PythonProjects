from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from queue import Empty
from tkinter import filedialog, messagebox, ttk

from lemo.config import AppConfig
from lemo.environment import Check, Environment, PrepareCancelled, PrepareError
from lemo.events import Event, event_queue
from lemo.prompt import (
    FilmRequest,
    default_project,
    normalize_project,
    valid_project,
)
from lemo.runner import FilmRunner
from lemo.styles import STYLES, Style, find, find_label

GALLERY_URL = "https://lemomo-ai.github.io/lemo-opuscar/"
FONT = "Microsoft YaHei UI"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.config = AppConfig.load()
        self.config.ensure_dirs()
        self.env = Environment(self.config)
        self.events = event_queue()
        self.checks: dict[str, Check] = {}
        self.env_labels: dict[str, tk.Label] = {}
        self.style_map: dict[str, Style] = {}
        self.runner: FilmRunner | None = None
        self.cancel_event: threading.Event | None = None
        self.busy = False
        self._models_loading = False
        self._models_requested = False
        self._started_at = 0.0
        self.last_output: str | None = None
        self.settings_window: tk.Toplevel | None = None

        self._setup_window()
        self._build_ui()
        self._load_into_ui()
        self._append_log(
            "Lemo-Opuscar 影片生成器\n"
            "提示：Lemo 的风格为 Claude Opus 5.5 调优，使用其他模型时风格还原可能下降。\n"
            "CLI 使用独立数据库 data/opencode.db，避免与桌面版数据库锁冲突。\n"
            "首次使用请先点击“一键准备”。"
        )
        self.root.after(100, self._poll_events)
        self.root.after(300, self.check_async)
        self.root.after(1000, self._tick)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ window
    def _setup_window(self) -> None:
        self.root.title("Lemo-Opuscar 影片生成器")
        self.root.geometry("1060x820")
        self.root.minsize(940, 700)
        self.root.option_add("*Font", (FONT, 10))

        style = ttk.Style(self.root)
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        style.configure("Title.TLabel", font=(FONT, 18, "bold"))
        style.configure("Sub.TLabel", foreground="#666666")
        style.configure("Hint.TLabel", foreground="#666666", font=(FONT, 9))
        style.configure("Error.TLabel", foreground="#c62828")
        style.configure("Ok.TLabel", foreground="#1a7f37")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Lemo-Opuscar 影片生成器", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="选择风格，写一个主题，剩下的交给 opencode。",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        header_buttons = ttk.Frame(header)
        header_buttons.grid(row=0, column=1, rowspan=2, sticky="e")
        self.gallery_btn = ttk.Button(header_buttons, text="风格画廊", command=self._open_gallery)
        self.gallery_btn.pack(side="left", padx=4)
        self.repo_btn = ttk.Button(header_buttons, text="打开仓库", command=self._open_repo)
        self.repo_btn.pack(side="left", padx=4)
        self.settings_btn = ttk.Button(header_buttons, text="设置", command=self._open_settings)
        self.settings_btn.pack(side="left", padx=4)

        self._build_env_panel(outer)
        self._build_form_panel(outer)
        self._build_log_panel(outer)
        self._build_status_bar(outer)

    def _build_env_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="环境", padding=10)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)

        grid = ttk.Frame(frame)
        grid.grid(row=0, column=0, sticky="ew")
        keys = [
            ("git", "Git"),
            ("git_bash", "Git Bash"),
            ("node", "Node.js"),
            ("npm", "npm"),
            ("uv", "uv"),
            ("ffmpeg", "ffmpeg"),
            ("opencode", "OpenCode CLI"),
            ("repo", "Lemo 仓库"),
            ("deps", "Lemo 依赖"),
        ]
        for index, (key, label) in enumerate(keys):
            widget = tk.Label(
                grid,
                text=f"… {label}",
                anchor="w",
                fg="#666666",
                cursor="hand2",
            )
            widget.grid(row=index // 3, column=index % 3, sticky="w", padx=(0, 22), pady=1)
            widget.bind("<Button-1>", lambda _event, k=key: self._show_check_detail(k))
            self.env_labels[key] = widget
        for column in range(3):
            grid.columnconfigure(column, weight=1)

        row = ttk.Frame(frame)
        row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        row.columnconfigure(1, weight=1)
        self.prepare_btn = ttk.Button(row, text="一键准备", command=self.prepare_async)
        self.prepare_btn.grid(row=0, column=0, padx=(0, 8))
        self.check_btn = ttk.Button(row, text="重新检测", command=self.check_async)
        self.check_btn.grid(row=0, column=1, sticky="w")
        self.progress = ttk.Progressbar(row, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=2, sticky="ew", padx=(12, 8))
        self.progress_label = ttk.Label(row, text="", style="Hint.TLabel", width=38)
        self.progress_label.grid(row=0, column=3, sticky="e")

    def _build_form_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="影片", padding=10)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="风格").grid(row=0, column=0, sticky="nw", pady=4)
        for style in STYLES:
            display = f"{style.category_zh} | {style.label}"
            self.style_map[display] = style
        self.style_var = tk.StringVar()
        self.style_combo = ttk.Combobox(
            frame,
            textvariable=self.style_var,
            values=list(self.style_map),
            state="readonly",
            height=24,
        )
        self.style_combo.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=4)

        ttk.Label(frame, text="主题 / 故事").grid(row=1, column=0, sticky="nw", pady=4)
        topic_frame = ttk.Frame(frame)
        topic_frame.grid(row=1, column=1, columnspan=3, sticky="nsew", padx=(8, 0), pady=4)
        topic_frame.columnconfigure(0, weight=1)
        self.topic_text = tk.Text(topic_frame, height=5, wrap="word", undo=True, font=(FONT, 10))
        self.topic_text.grid(row=0, column=0, sticky="nsew")
        topic_scroll = ttk.Scrollbar(topic_frame, orient="vertical", command=self.topic_text.yview)
        topic_scroll.grid(row=0, column=1, sticky="ns")
        self.topic_text.configure(yscrollcommand=topic_scroll.set)

        options = ttk.Frame(frame)
        options.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 2))
        ttk.Label(options, text="时长").pack(side="left")
        self.duration_var = tk.IntVar(value=40)
        self.duration_spin = ttk.Spinbox(options, from_=15, to=90, increment=5, width=6, textvariable=self.duration_var)
        self.duration_spin.pack(side="left", padx=(4, 16))
        ttk.Label(options, text="秒").pack(side="left", padx=(0, 14))

        ttk.Label(options, text="画幅").pack(side="left")
        self.aspect_var = tk.StringVar(value="16:9")
        self.aspect_combo = ttk.Combobox(
            options, textvariable=self.aspect_var, values=["16:9", "9:16", "1:1"], state="readonly", width=7
        )
        self.aspect_combo.pack(side="left", padx=(4, 16))

        ttk.Label(options, text="语言").pack(side="left")
        self.language_var = tk.StringVar(value="中文")
        self.language_combo = ttk.Combobox(
            options, textvariable=self.language_var, values=["中文", "English"], state="readonly", width=9
        )
        self.language_combo.pack(side="left", padx=(4, 16))

        self.voice_var = tk.BooleanVar(value=True)
        self.voice_check = ttk.Checkbutton(options, text="中文旁白", variable=self.voice_var)
        self.voice_check.pack(side="left")

        ttk.Label(frame, text="项目名").grid(row=3, column=0, sticky="w", pady=4)
        project_row = ttk.Frame(frame)
        project_row.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)
        project_row.columnconfigure(0, weight=1)
        self.project_var = tk.StringVar(value=default_project())
        self.project_entry = ttk.Entry(project_row, textvariable=self.project_var)
        self.project_entry.grid(row=0, column=0, sticky="ew")
        self.new_project_btn = ttk.Button(project_row, text="新项目名", command=self._new_project)
        self.new_project_btn.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(project_row, text="仅小写字母、数字、连字符", style="Hint.TLabel").grid(
            row=0, column=2, padx=(8, 0)
        )

        ttk.Label(frame, text="模型").grid(row=4, column=0, sticky="w", pady=4)
        model_row = ttk.Frame(frame)
        model_row.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)
        model_row.columnconfigure(0, weight=1)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(model_row, textvariable=self.model_var, values=[], state="readonly")
        self.model_combo.grid(row=0, column=0, sticky="ew")
        self.refresh_models_btn = ttk.Button(model_row, text="刷新模型", command=self.refresh_models_async)
        self.refresh_models_btn.grid(row=0, column=1, padx=(8, 0))
        self.model_hint = ttk.Label(model_row, text="环境就绪后加载模型；每次生成需手动选择", style="Hint.TLabel")
        self.model_hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        self.start_btn = ttk.Button(actions, text="开始生成", command=self.start_generation)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions, text="停止", command=self.stop_clicked, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Label(
            actions,
            text="单支影片通常需要 30–60 分钟，并消耗较多 token。",
            style="Hint.TLabel",
        ).pack(side="left", padx=(16, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="日志", padding=8)
        frame.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(frame, wrap="word", state="disabled", height=18, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.tag_configure("error", foreground="#c62828")
        self.log_text.tag_configure("ok", foreground="#1a7f37")

    def _build_status_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(bar, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky="w")
        self.elapsed_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.elapsed_var, style="Hint.TLabel").grid(
            row=0, column=1, padx=(8, 16)
        )
        self.open_folder_btn = ttk.Button(
            bar, text="打开成片文件夹", command=self._open_output_folder, state="disabled"
        )
        self.open_folder_btn.grid(row=0, column=2, padx=4)
        self.play_btn = ttk.Button(bar, text="播放成片", command=self._play_output, state="disabled")
        self.play_btn.grid(row=0, column=3, padx=4)

    # ------------------------------------------------------------------ config/ui
    def _load_into_ui(self) -> None:
        try:
            duration = int(self.config.duration)
        except (TypeError, ValueError):
            duration = 40
        self.duration_var.set(max(15, min(90, duration)))
        self.aspect_var.set(self.config.aspect if self.config.aspect in ("16:9", "9:16", "1:1") else "16:9")
        self.language_var.set(self.config.language if self.config.language in ("中文", "English") else "中文")
        self.voice_var.set(self.config.default_voice)
        if self.config.last_style:
            style = find(self.config.last_style)
            if style:
                self.style_var.set(f"{style.category_zh} | {style.label}")
        if self.config.last_topic:
            self.topic_text.insert("1.0", self.config.last_topic)

    def _save_config_from_ui(self) -> None:
        style = self._selected_style()
        self.config.last_style = style.slug if style else self.config.last_style
        self.config.last_topic = self.topic_text.get("1.0", "end").strip()
        self.config.language = self.language_var.get()
        self.config.aspect = self.aspect_var.get()
        try:
            self.config.duration = max(15, min(90, int(self.duration_var.get())))
        except (tk.TclError, ValueError):
            self.config.duration = 40
        self.config.default_voice = bool(self.voice_var.get())
        model = self.model_var.get().strip()
        if model:
            self.config.model = model
        self.config.save()

    def _selected_style(self) -> Style | None:
        return self.style_map.get(self.style_var.get()) or find_label(self.style_var.get())

    def _new_project(self) -> None:
        self.project_var.set(default_project())

    # ------------------------------------------------------------------ checks
    def check_async(self) -> None:
        if self.busy:
            return
        self._set_status("正在检测环境 ...")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            checks = self.env.check()
            self.events.put(Event("env_status", data={"checks": checks}))
        except Exception as exc:
            self.events.put(Event("error", f"环境检测失败: {exc}"))

    def _apply_checks(self, checks: list[Check]) -> None:
        self.checks = {check.key: check for check in checks}
        for key, label in self.env_labels.items():
            check = self.checks.get(key)
            if check is None:
                continue
            mark = "✓" if check.ok else "✗"
            detail = self._short(check.detail) if check.detail else ""
            text = f"{mark} {check.label}"
            if detail and check.ok:
                text += f"  {detail}"
            label.configure(text=text, fg="#1a7f37" if check.ok else "#c62828")
        if all(check.ok for check in checks):
            self._set_status("环境就绪")
            if not self._models_requested:
                self._models_requested = True
                self.refresh_models_async()
        else:
            self._set_status("环境未就绪：点击“一键准备”自动安装缺失项")

    def _show_check_detail(self, key: str) -> None:
        check = self.checks.get(key)
        if check is None:
            return
        detail = check.detail or "无详情"
        if check.path:
            detail += f"\n{check.path}"
        self._set_status(detail.replace("\n", "  "))

    # ------------------------------------------------------------------ prepare
    def prepare_async(self) -> None:
        if self.busy:
            return
        if not messagebox.askyesno(
            "一键准备",
            "将自动下载 OpenCode CLI、ffmpeg，clone Lemo-Opuscar 仓库，并安装 "
            "Node/Python/语音/音乐依赖。\n\n首次下载量约数百 MB，可能需要几分钟。是否继续？",
        ):
            return
        self.busy = True
        self._set_busy(True)
        self.cancel_event = threading.Event()
        self.progress.configure(value=0)
        self._set_status("准备环境 ...")

        def worker() -> None:
            try:
                self.env.prepare(
                    lambda text: self.events.put(Event("log", text)),
                    lambda fraction, text: self.events.put(Event("progress", text, fraction)),
                    self.cancel_event,
                )
                self.events.put(Event("prepare_done"))
            except PrepareCancelled:
                self.events.put(Event("log", "已取消环境准备。"))
                self.events.put(Event("status", "已取消"))
            except PrepareError as exc:
                self.events.put(Event("error", str(exc)))
            except Exception as exc:
                self.events.put(Event("error", f"环境准备失败: {exc}"))
            finally:
                self.events.put(Event("finished"))
                self.events.put(Event("check_request"))
                self.cancel_event = None

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ models
    def refresh_models_async(self) -> None:
        if self.busy or self._models_loading:
            return
        if not self.env.detect_opencode():
            self._set_status("未找到 opencode CLI，请先完成“一键准备”")
            return
        self._models_loading = True
        self.model_hint.configure(text="正在加载模型 ...")
        threading.Thread(target=self._models_worker, daemon=True).start()

    def _models_worker(self) -> None:
        try:
            models = self.env.opencode_models()
            self.events.put(Event("models", data={"models": models}))
        except Exception as exc:
            self.events.put(Event("error", f"加载模型失败: {exc}"))

    def _apply_models(self, models: list[str]) -> None:
        self._models_loading = False
        self._models_requested = True
        self.model_combo.configure(values=models)
        if self.model_var.get() not in models:
            self.model_var.set("")
        if models:
            last = f"；上次使用：{self.config.model}" if self.config.model else ""
            suffix = ""
            if not any(model.startswith("opencode-go/") for model in models):
                suffix = "；独立 CLI 未列出 opencode-go 订阅模型"
            self.model_hint.configure(text=f"可用 {len(models)} 个模型，请手动选择{last}{suffix}")
        else:
            self.model_hint.configure(text="未加载到模型，请检查 opencode 登录状态或网络")

    # ------------------------------------------------------------------ generate
    def start_generation(self) -> None:
        if self.busy:
            return
        style = self._selected_style()
        if style is None:
            messagebox.showwarning("缺少风格", "请先选择一种影片风格。")
            return
        topic = self.topic_text.get("1.0", "end").strip()
        if len(topic) < 2:
            messagebox.showwarning("缺少主题", "请填写影片主题或故事。")
            return
        if len(topic) > 6000:
            messagebox.showwarning("主题过长", "请将主题控制在 6000 字以内，避免命令行过长。")
            return
        model = self.model_var.get().strip()
        if not model:
            messagebox.showwarning("缺少模型", "请先选择模型。模型列表在环境就绪后加载。")
            return
        project = normalize_project(self.project_var.get())
        if not valid_project(project):
            messagebox.showwarning("项目名无效", "项目名只能包含小写字母、数字和连字符。")
            return
        self.project_var.set(project)
        try:
            duration = int(self.duration_var.get())
        except (tk.TclError, ValueError):
            duration = 40
        duration = max(15, min(90, duration))
        self.duration_var.set(duration)

        if not messagebox.askyesno(
            "开始生成",
            f"风格：{style.zh} / {style.en}\n"
            f"时长：{duration} 秒\n"
            f"模型：{model}\n\n"
            "单支影片通常需要 30–60 分钟，并消耗较多 token。\n"
            "生成期间请保持程序和网络连接。是否开始？",
        ):
            return

        self._save_config_from_ui()
        request = FilmRequest(
            style=style,
            topic=topic,
            duration=duration,
            aspect=self.aspect_var.get(),
            language=self.language_var.get(),
            voice=bool(self.voice_var.get()),
            project=project,
            model=model,
        )
        self.runner = FilmRunner(self.config, self.env, request, self.events)
        self.busy = True
        self._started_at = time.time()
        self._set_busy(True)
        self._set_output(None)
        self.progress.configure(value=0)
        self.elapsed_var.set("已运行 00:00:00")
        self._set_status("正在生成影片 ...")
        threading.Thread(target=self.runner.run, daemon=True).start()

    def stop_clicked(self) -> None:
        if self.cancel_event is not None:
            self.cancel_event.set()
            self.env.terminate_all()
            self._set_status("正在取消环境准备 ...")
            return
        if self.runner is not None and self.runner.running:
            if messagebox.askyesno("停止生成", "确定停止当前影片生成？未完成的文件会保留。"):
                self.runner.stop()
        else:
            self._set_status("当前没有正在运行的任务")

    def _set_output(self, path: str | None) -> None:
        self.last_output = path
        state = "normal" if path and Path(path).exists() else "disabled"
        self.play_btn.configure(state=state)
        self.open_folder_btn.configure(state=state)

    # ------------------------------------------------------------------ events
    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_event(self, event: Event) -> None:
        kind = event.kind
        if kind == "log":
            self._append_log(event.text)
        elif kind == "status":
            self._set_status(event.text)
        elif kind == "progress":
            value = max(0.0, min(1.0, event.value or 0.0))
            self.progress.configure(value=value * 100)
            self.progress_label.configure(text=event.text)
        elif kind == "env_status":
            checks = event.data.get("checks")
            if isinstance(checks, list):
                self._apply_checks(checks)
        elif kind == "models":
            models = event.data.get("models") or []
            self._apply_models(list(models))
        elif kind == "prepare_done":
            self.progress.configure(value=100)
            self.progress_label.configure(text="环境准备完成")
            self._set_status("环境准备完成")
            messagebox.showinfo("完成", "环境准备完成，可以开始生成影片。")
            self.check_async()
        elif kind == "output":
            self._set_output(event.text)
        elif kind == "done":
            self._set_output(event.text)
            self._set_status("影片生成完成")
            self.progress.configure(value=100)
            self.progress_label.configure(text="完成")
        elif kind == "error":
            self._append_log(f"错误: {event.text}", "error")
            first_line = event.text.splitlines()[0] if event.text else "未知错误"
            self._set_status(f"错误: {first_line[:120]}")
            messagebox.showerror("出错了", event.text or "未知错误")
        elif kind == "check_request":
            self.check_async()
        elif kind == "finished":
            self.busy = False
            self._set_busy(False)
            if self.runner is not None:
                self.runner = None
        elif kind == "repo_updated":
            messagebox.showinfo("完成", "仓库已更新。")
            self.check_async()

    def _tick(self) -> None:
        if self.runner is not None and self.runner.running:
            elapsed = int(self.runner.elapsed)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.elapsed_var.set(f"已运行 {hours:02d}:{minutes:02d}:{seconds:02d}")
        self.root.after(1000, self._tick)

    # ------------------------------------------------------------------ helpers
    def _append_log(self, text: str, tag: str = "") -> None:
        self.log_text.configure(state="normal")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 6000:
            self.log_text.delete("1.0", "1500.0")
        self.log_text.insert("end", text.rstrip("\n") + "\n", tag or ())
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _set_busy(self, busy: bool) -> None:
        widgets: list[tuple[tk.Widget, str]] = [
            (self.prepare_btn, "normal"),
            (self.check_btn, "normal"),
            (self.start_btn, "normal"),
            (self.refresh_models_btn, "normal"),
            (self.gallery_btn, "normal"),
            (self.repo_btn, "normal"),
            (self.settings_btn, "normal"),
            (self.style_combo, "readonly"),
            (self.duration_spin, "normal"),
            (self.aspect_combo, "readonly"),
            (self.language_combo, "readonly"),
            (self.voice_check, "normal"),
            (self.project_entry, "normal"),
            (self.new_project_btn, "normal"),
            (self.model_combo, "readonly"),
            (self.topic_text, "normal"),
        ]
        for widget, state in widgets:
            try:
                widget.configure(state="disabled" if busy else state)
            except tk.TclError:
                pass
        self.stop_btn.configure(state="normal" if busy else "disabled")

    @staticmethod
    def _short(text: str, limit: int = 34) -> str:
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _open_gallery(self) -> None:
        webbrowser.open(GALLERY_URL)

    def _open_repo(self) -> None:
        target = self.config.repo
        if target.exists():
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("仓库未准备", "请先点击“一键准备”。")

    def _open_output_folder(self) -> None:
        target = Path(self.last_output).parent if self.last_output else self.config.repo / "films"
        if target.exists():
            os.startfile(str(target))  # type: ignore[attr-defined]

    def _play_output(self) -> None:
        if self.last_output and Path(self.last_output).exists():
            os.startfile(self.last_output)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ settings
    def _open_settings(self) -> None:
        try:
            if self.settings_window is not None and self.settings_window.winfo_exists():
                self.settings_window.lift()
                return
        except tk.TclError:
            self.settings_window = None
        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("设置")
        window.geometry("760x430")
        window.transient(self.root)
        window.columnconfigure(1, weight=1)

        variables: dict[str, tk.StringVar] = {}
        rows = [
            ("repo_dir", "仓库目录", "dir"),
            ("tools_dir", "工具目录", "dir"),
            ("opencode_exe", "opencode 可执行文件", "file"),
            ("ffmpeg_dir", "ffmpeg 目录", "dir"),
            ("git_bash", "Git Bash", "file"),
            ("uv_exe", "uv 可执行文件", "file"),
        ]
        for index, (attr, label, kind) in enumerate(rows):
            ttk.Label(window, text=label).grid(row=index, column=0, sticky="w", padx=12, pady=6)
            variable = tk.StringVar(value=getattr(self.config, attr))
            variables[attr] = variable
            entry = ttk.Entry(window, textvariable=variable)
            entry.grid(row=index, column=1, sticky="ew", pady=6)
            button = ttk.Button(
                window,
                text="浏览",
                command=lambda var=variable, k=kind: self._browse(var, k),
            )
            button.grid(row=index, column=2, padx=12, pady=6)

        info = ttk.Label(
            window,
            text="路径留空时自动检测。修改后点击“保存并重新检测”。",
            style="Hint.TLabel",
        )
        info.grid(row=len(rows), column=0, columnspan=3, sticky="w", padx=12, pady=(4, 8))

        actions = ttk.Frame(window)
        actions.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="ew", padx=12, pady=8)
        ttk.Button(actions, text="保存并重新检测", command=lambda: self._save_settings(variables)).pack(side="left")
        ttk.Button(actions, text="更新仓库", command=self._update_repo_async).pack(side="left", padx=8)
        ttk.Button(actions, text="关闭", command=window.destroy).pack(side="right")

        ttk.Label(
            window,
            text="模型不在这里设置；每次生成时在主界面手动选择。",
            style="Hint.TLabel",
        ).grid(row=len(rows) + 2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))

    def _browse(self, variable: tk.StringVar, kind: str) -> None:
        if kind == "dir":
            value = filedialog.askdirectory(parent=self.settings_window)
        else:
            value = filedialog.askopenfilename(parent=self.settings_window)
        if value:
            variable.set(value)

    def _save_settings(self, variables: dict[str, tk.StringVar]) -> None:
        for attr, variable in variables.items():
            setattr(self.config, attr, variable.get().strip())
        self.config.save()
        self._append_log("设置已保存，重新检测环境 ...")
        self.check_async()

    def _update_repo_async(self) -> None:
        if self.busy:
            messagebox.showinfo("请稍候", "当前有任务在运行。")
            return
        if not messagebox.askyesno("更新仓库", "将执行 git fetch + reset，更新 Lemo-Opuscar 仓库。是否继续？"):
            return
        self.busy = True
        self._set_busy(True)
        cancel = threading.Event()
        self.cancel_event = cancel

        def worker() -> None:
            try:
                self.env.update_repo(
                    lambda text: self.events.put(Event("log", text)),
                    lambda fraction, text: self.events.put(Event("progress", text, fraction)),
                    cancel,
                )
                self.events.put(Event("repo_updated"))
            except PrepareCancelled:
                self.events.put(Event("status", "仓库更新已取消"))
            except Exception as exc:
                self.events.put(Event("error", f"更新仓库失败: {exc}"))
            finally:
                self.cancel_event = None
                self.events.put(Event("finished"))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ close
    def _on_close(self) -> None:
        if self.busy:
            if not messagebox.askyesno("退出", "任务仍在运行，确定停止并退出？"):
                return
            if self.cancel_event is not None:
                self.cancel_event.set()
            if self.runner is not None and self.runner.running:
                self.runner.stop()
            self.env.terminate_all()
            time.sleep(0.3)
        self._save_config_from_ui()
        self.root.destroy()


# ---------------------------------------------------------------------- headless
def _enable_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def headless_check() -> int:
    config = AppConfig.load()
    environment = Environment(config)
    checks = environment.check()
    for check in checks:
        mark = "OK  " if check.ok else "MISS"
        print(f"[{mark}] {check.label}: {check.detail}")
        if check.path:
            print(f"       {check.path}")
    return 0 if all(check.ok for check in checks) else 1


def headless_bootstrap() -> int:
    config = AppConfig.load()
    environment = Environment(config)

    def log(text: str) -> None:
        print(text, flush=True)

    def progress(fraction: float, text: str) -> None:
        print(f"[{fraction * 100:5.1f}%] {text}", flush=True)

    try:
        environment.prepare(log, progress)
    except PrepareError as exc:
        print(f"\n失败: {exc}", file=sys.stderr)
        return 1
    except PrepareCancelled:
        print("\n已取消", file=sys.stderr)
        return 130
    return 0


def headless_smoke(model: str) -> int:
    config = AppConfig.load()
    environment = Environment(config)
    ok, output = environment.smoke_test(model or config.model, print)
    print("\nSMOKE: " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def run_gui() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


def main() -> int:
    _enable_utf8()
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(
            "用法:\n"
            "  python main.py              启动 UI\n"
            "  python main.py --check      只检测环境\n"
            "  python main.py --bootstrap  无 UI 准备环境\n"
            "  python main.py --smoke --model opencode/deepseek-v4.1-flash-free\n"
        )
        return 0
    if "--check" in args:
        return headless_check()
    if "--bootstrap" in args:
        return headless_bootstrap()
    if "--smoke" in args:
        model = ""
        if "--model" in args:
            index = args.index("--model")
            if index + 1 < len(args):
                model = args[index + 1]
        return headless_smoke(model)
    run_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

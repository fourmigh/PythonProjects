from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QStyle,
    QTextEdit,
    QToolBar,
)

from psapp.config import AppConfig, load_config, save_config
from psapp.core.composite import compose_background, load_image, save_image
from psapp.core.cutout import available as cutout_available
from psapp.core.erase import inpaint
from psapp.core.history import SessionHistory
from psapp.core.mask import has_mask
from psapp.providers.base import EditRequest
from psapp.providers.siliconflow import SiliconFlowProvider
from psapp.providers.zhipu import PromptRewriter

from .batch_dialog import BatchDialog
from .canvas import ImageCanvas
from .chat_panel import ChatPanel
from .clipboard import extract_clipboard, has_clipboard_image
from .dialogs import BackgroundDialog, CompareDialog
from .settings_dialog import SettingsDialog
from .workers import CutoutWorker, EditWorker

IMAGE_FILTER = "图片 (*.png *.jpg *.jpeg *.webp *.bmp);;所有文件 (*.*)"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config: AppConfig = load_config()
        self.provider: SiliconFlowProvider | None = None
        self.rewriter = PromptRewriter(self.config)
        self.history: SessionHistory | None = None
        self.original_image: Image.Image | None = None
        self.current_image: Image.Image | None = None
        self.total_cost = 0.0
        self.edit_worker: EditWorker | None = None
        self.cutout_worker: CutoutWorker | None = None
        self.source_path: Path | None = None

        self.setWindowTitle("PS Studio")
        self.resize(1320, 860)
        self.setAcceptDrops(True)

        self._build_actions()
        self._build_toolbar()
        self._build_menu()
        self._build_central()
        self._build_status()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            app.clipboard().dataChanged.connect(self._update_clipboard_hint)
        self._update_clipboard_hint()

        self._rebuild_services()
        QTimer.singleShot(500, self._first_run_hint)

    def _build_actions(self) -> None:
        style = self.style()

        self.open_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "打开",
            self,
        )
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_image)

        self.paste_action = QAction("粘贴", self)
        self.paste_action.setToolTip("从剪贴板粘贴图片（Ctrl+V）")
        self.paste_action.triggered.connect(self.paste_clipboard)

        self.save_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "保存",
            self,
        )
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_current)

        self.save_as_action = QAction("另存为", self)
        self.save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.save_as_action.triggered.connect(self.save_as)

        self.brush_action = QAction("画笔", self)
        self.rect_action = QAction("矩形", self)
        self.erase_action = QAction("橡皮", self)
        self.view_action = QAction("浏览", self)
        for action in (
            self.brush_action,
            self.rect_action,
            self.erase_action,
            self.view_action,
        ):
            action.setCheckable(True)
        self.view_action.setChecked(True)

        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        for action in (
            self.view_action,
            self.brush_action,
            self.rect_action,
            self.erase_action,
        ):
            self.mode_group.addAction(action)

        self.brush_action.triggered.connect(
            lambda checked: self._set_mode(ImageCanvas.MODE_BRUSH, checked)
        )
        self.rect_action.triggered.connect(
            lambda checked: self._set_mode(ImageCanvas.MODE_RECT, checked)
        )
        self.erase_action.triggered.connect(
            lambda checked: self._set_mode(ImageCanvas.MODE_ERASE, checked)
        )
        self.view_action.triggered.connect(
            lambda checked: self._set_mode(ImageCanvas.MODE_VIEW, checked)
        )

        self.clear_action = QAction("清除选区", self)
        self.clear_action.setShortcut(QKeySequence("Ctrl+Delete"))
        self.clear_action.triggered.connect(self._clear_mask)

        self.fit_action = QAction("适应窗口", self)
        self.fit_action.setShortcut(QKeySequence("Ctrl+0"))
        self.fit_action.triggered.connect(self._fit_view)

        self.compare_action = QAction("原图对比", self)
        self.compare_action.setShortcut(QKeySequence("Ctrl+D"))
        self.compare_action.triggered.connect(self.compare)

        self.undo_action = QAction("上一版", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Alt+Z"))
        self.undo_action.triggered.connect(self.undo_version)

        self.cutout_action = QAction("抠图换背景", self)
        self.cutout_action.triggered.connect(self.cutout)

        self.ai_erase_action = QAction("AI 消除选区", self)
        self.ai_erase_action.triggered.connect(self.ai_erase)

        self.inpaint_action = QAction("本地修补选区", self)
        self.inpaint_action.triggered.connect(self.local_inpaint)

        self.settings_action = QAction("参数设置", self)
        self.settings_action.triggered.connect(self.open_settings)

        self.batch_action = QAction("批量处理", self)
        self.batch_action.triggered.connect(self.open_batch)

        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("关于", self)
        self.about_action.triggered.connect(self.show_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("工具")
        toolbar.setMovable(False)
        toolbar.setOrientation(Qt.Orientation.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, toolbar)

        toolbar.addAction(self.open_action)
        toolbar.addAction(self.paste_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.save_as_action)
        toolbar.addSeparator()
        for action in (
            self.view_action,
            self.brush_action,
            self.rect_action,
            self.erase_action,
        ):
            toolbar.addAction(action)

        toolbar.addSeparator()
        brush_label = QLabel("笔刷")
        brush_label.setObjectName("SectionTitle")
        toolbar.addWidget(brush_label)
        self.brush_spin = QSpinBox()
        self.brush_spin.setRange(4, 220)
        self.brush_spin.setValue(36)
        self.brush_spin.setSuffix(" px")
        self.brush_spin.setFixedWidth(82)
        self.brush_spin.valueChanged.connect(self._on_brush_size)
        toolbar.addWidget(self.brush_spin)

        toolbar.addSeparator()
        toolbar.addAction(self.clear_action)
        toolbar.addAction(self.fit_action)
        toolbar.addAction(self.compare_action)
        toolbar.addAction(self.undo_action)
        toolbar.addSeparator()
        toolbar.addAction(self.cutout_action)
        toolbar.addAction(self.ai_erase_action)
        toolbar.addAction(self.inpaint_action)
        toolbar.addSeparator()
        toolbar.addAction(self.batch_action)
        toolbar.addAction(self.settings_action)

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("文件")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.paste_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.batch_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = menu.addMenu("编辑")
        edit_menu.addAction(self.undo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.view_action)
        edit_menu.addAction(self.brush_action)
        edit_menu.addAction(self.rect_action)
        edit_menu.addAction(self.erase_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.clear_action)

        tool_menu = menu.addMenu("工具")
        tool_menu.addAction(self.fit_action)
        tool_menu.addAction(self.compare_action)
        tool_menu.addSeparator()
        tool_menu.addAction(self.cutout_action)
        tool_menu.addAction(self.ai_erase_action)
        tool_menu.addAction(self.inpaint_action)

        settings_menu = menu.addMenu("设置")
        settings_menu.addAction(self.settings_action)

        help_menu = menu.addMenu("帮助")
        help_menu.addAction(self.about_action)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.canvas = ImageCanvas()
        self.chat = ChatPanel(self.config)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.chat)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([920, 390])
        self.setCentralWidget(splitter)

        self.canvas.zoom_changed.connect(self._on_zoom)
        self.chat.send_requested.connect(self._on_send)
        self.chat.candidate_selected.connect(self._on_candidate)
        self.chat.params_changed.connect(self._sync_params)

    def _build_status(self) -> None:
        self.status_label = QLabel("未打开图片")
        self.statusBar().addWidget(self.status_label, 1)
        self.clipboard_status = QLabel("")
        self.clipboard_status.setObjectName("SectionTitle")
        self.clipboard_status.hide()
        self.zoom_status = QLabel("100%")
        self.model_status = QLabel("")
        self.cost_status = QLabel("累计 ¥0.00")
        self.statusBar().addPermanentWidget(self.clipboard_status)
        self.statusBar().addPermanentWidget(self.zoom_status)
        self.statusBar().addPermanentWidget(self.model_status)
        self.statusBar().addPermanentWidget(self.cost_status)

    def _rebuild_services(self) -> None:
        self.provider = (
            SiliconFlowProvider(self.config) if self.config.provider_ready else None
        )
        self.rewriter = PromptRewriter(self.config)
        model_name = self.config.model.split("/")[-1]
        self.model_status.setText(model_name)
        if self.provider is None:
            self.model_status.setText(f"{model_name}（未配置 Key）")

    def _sync_params(self) -> None:
        params = self.chat.params()
        self.config.candidates = params["candidates"]
        self.config.steps = params["steps"]
        self.config.cfg = params["cfg"]

    def _update_clipboard_hint(self) -> None:
        clipboard = QApplication.clipboard()
        if has_clipboard_image(clipboard):
            self.clipboard_status.setText("剪贴板中有图片，按 Ctrl+V 粘贴")
            self.clipboard_status.show()
        else:
            self.clipboard_status.clear()
            self.clipboard_status.hide()

    def _first_run_hint(self) -> None:
        if not self.config.provider_ready:
            self.chat.append_message(
                "每次启动都需要输入硅基流动 API Key（只保存在内存，不会写入磁盘）。"
                "请到菜单「设置 → 参数设置」填写，或先使用抠图、本地修补等离线功能。",
                "error",
            )
            self.open_settings()

    def _is_busy(self) -> bool:
        return bool(
            (self.edit_worker is not None and self.edit_worker.isRunning())
            or (self.cutout_worker is not None and self.cutout_worker.isRunning())
        )

    def _guard_busy(self) -> bool:
        if self._is_busy():
            QMessageBox.information(self, "请稍候", "当前任务还未完成，请稍后再操作。")
            return True
        return False

    def open_image(self) -> None:
        if self._guard_busy():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开图片", "", IMAGE_FILTER)
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        if self._guard_busy():
            return
        path = Path(path)
        try:
            image = load_image(path)
        except Exception as exc:
            QMessageBox.warning(self, "打开失败", f"无法打开图片：{exc}")
            return
        self.open_pil_image(image, path.name, path)

    def open_pil_image(
        self,
        image: Image.Image,
        name: str,
        source_path: Path | None = None,
    ) -> None:
        if self._guard_busy():
            return
        self.source_path = source_path
        self.original_image = image.convert("RGB")
        self.current_image = self.original_image.copy()
        self.canvas.set_image(self.current_image)
        try:
            self.history = SessionHistory(self.config.output_dir, self.original_image)
        except Exception as exc:
            self.history = None
            QMessageBox.warning(
                self,
                "输出目录",
                f"无法创建历史目录：{exc}\n请到设置中修改输出目录。",
            )
        self.total_cost = 0.0
        self.chat.set_cost(0.0)
        self.chat.clear_candidates()
        self.chat.append_message(
            f"已载入：{name}（{self.current_image.width}×{self.current_image.height}）",
            "success",
        )
        self.setWindowTitle(f"PS Studio - {name}")
        self._update_status()

    def paste_clipboard(self) -> None:
        if self._guard_busy():
            return
        clipboard = QApplication.clipboard()
        image, path = extract_clipboard(clipboard)
        if image is None and path is None:
            self.chat.append_message("剪贴板里没有图片。", "info")
            self.status_label.setText("剪贴板里没有图片")
            return

        if self.current_image is not None:
            answer = QMessageBox.question(
                self,
                "替换当前图片",
                "从剪贴板载入会替换当前工作区，之前的结果仍保存在 outputs 目录。\n"
                "是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        if path is not None:
            self.open_path(path)
        elif image is not None:
            self.open_pil_image(image, "剪贴板图片")

    def save_current(self) -> None:
        if self.current_image is None:
            QMessageBox.information(self, "保存", "还没有打开图片。")
            return
        if self.history is not None:
            default = str(self.history.session_dir / "edited.png")
        else:
            default = str(Path(self.config.output_dir) / "edited.png")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", default, "PNG (*.png);;JPEG (*.jpg);;WEBP (*.webp)"
        )
        if path:
            self._save_to(Path(path))

    def save_as(self) -> None:
        self.save_current()

    def _save_to(self, path: Path) -> None:
        try:
            save_image(self.current_image, path)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self.chat.append_message(f"已保存：{path}", "success")
        self.status_label.setText(f"已保存到 {path.name}")

    def _on_send(self, prompt: str) -> None:
        self._start_edit(prompt, require_mask=False)

    def _restore_prompt(self, prompt: str) -> None:
        if prompt and not self.chat.input.toPlainText().strip():
            self.chat.input.setPlainText(prompt)

    def _start_edit(self, prompt: str, require_mask: bool) -> None:
        if self._guard_busy():
            self._restore_prompt(prompt)
            return
        if self.current_image is None:
            self._restore_prompt(prompt)
            QMessageBox.information(self, "提示", "请先打开一张图片。")
            return
        if self.provider is None or not self.config.provider_ready:
            self._restore_prompt(prompt)
            QMessageBox.warning(self, "提示", "请先在设置中配置硅基流动 API Key。")
            self.open_settings()
            return

        mask = self.canvas.get_mask_pil()
        if mask is not None and not has_mask(mask):
            mask = None
        if require_mask and mask is None:
            self._restore_prompt(prompt)
            QMessageBox.information(self, "提示", "请先用画笔或矩形选中要处理区域。")
            return

        self._sync_params()
        params = self.chat.params()
        request = EditRequest(
            image=self.current_image,
            prompt=prompt,
            seed=params["seed"],
            steps=params["steps"],
            cfg=params["cfg"],
            candidates=params["candidates"],
        )

        self.edit_worker = EditWorker(
            self.provider,
            self.rewriter,
            request,
            mask=mask,
            do_paste_back=self.config.paste_back,
            feather=self.config.feather,
        )
        self.edit_worker.succeeded.connect(self._on_edit_succeeded)
        self.edit_worker.failed.connect(self._on_edit_failed)
        self.edit_worker.finished.connect(self._on_edit_thread_finished)
        self.chat.set_busy(True)
        self.chat.append_message(f"你：{prompt}", "user")
        if mask is not None:
            self.chat.append_message("局部编辑：只处理红色高亮区域", "system")
        self.status_label.setText("生成中…")
        self.edit_worker.start()

    def _on_edit_succeeded(self, payload: dict) -> None:
        try:
            images = payload["images"]
            mask = payload.get("mask")
            if self.history is None:
                if self.original_image is None:
                    raise RuntimeError("缺少原图，无法保存版本")
                self.history = SessionHistory(
                    self.config.output_dir, self.original_image
                )
            version = self.history.add_version(
                images,
                prompt=payload["original_prompt"],
                rewritten_prompt=payload["prompt"],
                model=self.config.model,
                seed=payload["seeds"][0] if payload["seeds"] else None,
                steps=payload["steps"],
                cfg=payload["cfg"],
                mask=mask,
                cost=payload["cost"],
            )
            self.current_image = images[0].convert("RGB")
            self.canvas.set_image(self.current_image)
            self.chat.set_candidates(images)

            if payload["prompt"] and payload["prompt"] != payload["original_prompt"]:
                self.chat.append_message(
                    f"已优化指令：{payload['prompt']}", "system"
                )
            if payload.get("rewrite_error"):
                self.chat.append_message(
                    f"指令改写失败，已使用原指令：{payload['rewrite_error']}", "info"
                )
            for warning in payload.get("warnings", []):
                self.chat.append_message(warning, "error")

            seed_text = payload["seeds"][0] if payload["seeds"] else "-"
            self.chat.append_message(
                f"已生成 {len(images)} 张 · 本次 ¥{payload['cost']:.2f} · "
                f"{version.id} · seed {seed_text}",
                "success",
            )
            self.total_cost = self.history.total_cost
            self.chat.set_cost(self.total_cost)
            self.status_label.setText(
                f"生成完成 · {len(images)} 张 · 本次 ¥{payload['cost']:.2f}"
            )
            self._update_status()
        except Exception as exc:
            self.chat.append_message(f"保存结果失败：{exc}", "error")
            self.status_label.setText("保存结果失败")
        finally:
            self.chat.set_busy(False)

    def _on_edit_failed(self, message: str) -> None:
        self.chat.set_busy(False)
        self.chat.append_message(f"生成失败：{message}", "error")
        self.status_label.setText("生成失败")
        self._update_status()

    def _on_edit_thread_finished(self) -> None:
        worker = self.edit_worker
        self.edit_worker = None
        if worker is not None:
            worker.deleteLater()

    def _on_candidate(self, index: int) -> None:
        if self.history is None:
            return
        version = self.history.current
        if version is None or index >= len(version.files):
            return
        self.history.select(version.id, index)
        image = self.history.current_image().convert("RGB")
        self.current_image = image
        self.canvas.set_image(image)
        self.status_label.setText(
            f"已选择 {version.id} 候选 {index + 1}/{len(version.files)}"
        )

    def undo_version(self) -> None:
        if self.history is None or len(self.history.versions) < 2:
            return
        versions = self.history.versions
        current_id = self.history.current_id
        index = next(
            (i for i, version in enumerate(versions) if version.id == current_id),
            len(versions) - 1,
        )
        if index <= 0:
            self.chat.append_message("已经是第一版了。", "info")
            return
        previous = versions[index - 1]
        self.history.select(previous.id, previous.selected)
        images = [
            Image.open(self.history.image_path(previous, i))
            for i in range(len(previous.files))
        ]
        self.current_image = images[previous.selected].convert("RGB")
        self.canvas.set_image(self.current_image)
        self.chat.set_candidates(images)
        self.chat.append_message(f"已回退到 {previous.id}", "system")
        self._update_status()

    def _set_mode(self, mode: str, checked: bool) -> None:
        if checked:
            self.canvas.set_mode(mode)

    def _on_brush_size(self, value: int) -> None:
        self.canvas.set_brush_size(value)

    def _clear_mask(self) -> None:
        self.canvas.clear_mask()
        self.chat.append_message("已清除选区", "info")

    def _fit_view(self) -> None:
        self.canvas.fit_to_view()

    def compare(self) -> None:
        if self.original_image is None or self.current_image is None:
            QMessageBox.information(self, "对比", "还没有打开图片。")
            return
        CompareDialog(self.original_image, self.current_image, self).exec()

    def cutout(self) -> None:
        if self._guard_busy():
            return
        if self.current_image is None:
            QMessageBox.information(self, "抠图", "请先打开一张图片。")
            return
        if not cutout_available():
            QMessageBox.information(
                self,
                "抠图",
                "未安装 rembg，请先在终端运行：\n\npip install rembg onnxruntime",
            )
            return
        source = self.current_image.copy()
        self.cutout_worker = CutoutWorker(source)
        self.cutout_worker.progress.connect(self._on_cutout_progress)
        self.cutout_worker.succeeded.connect(self._on_cutout_succeeded)
        self.cutout_worker.failed.connect(self._on_cutout_failed)
        self.cutout_worker.finished.connect(self._on_cutout_thread_finished)
        self.chat.append_message("正在抠图，请稍候…", "info")
        self.status_label.setText("正在抠图…")
        self.cutout_worker.start()

    def _on_cutout_progress(self, message: str) -> None:
        self.status_label.setText(message)

    def _on_cutout_succeeded(self, foreground: Image.Image) -> None:
        self.status_label.setText("抠图完成")
        dialog = BackgroundDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._update_status()
            return
        try:
            background = (
                dialog.background_image()
                if dialog.is_image()
                else dialog.background_color()
            )
            result = compose_background(foreground, background)
        except Exception as exc:
            QMessageBox.warning(self, "抠图", f"合成背景失败：{exc}")
            return
        if self.history is None and self.original_image is not None:
            self.history = SessionHistory(self.config.output_dir, self.original_image)
        version = self.history.add_version(
            [result],
            prompt="抠图换背景",
            model="rembg",
            cost=0.0,
        )
        self.current_image = result
        self.canvas.set_image(result)
        self.chat.set_candidates([result])
        self.chat.append_message(f"抠图换背景完成 · {version.id}", "success")
        self._update_status()

    def _on_cutout_failed(self, message: str) -> None:
        self.chat.append_message(f"抠图失败：{message}", "error")
        self.status_label.setText("抠图失败")

    def _on_cutout_thread_finished(self) -> None:
        worker = self.cutout_worker
        self.cutout_worker = None
        if worker is not None:
            worker.deleteLater()

    def local_inpaint(self) -> None:
        if self._guard_busy():
            return
        if self.current_image is None:
            QMessageBox.information(self, "本地修补", "请先打开一张图片。")
            return
        mask = self.canvas.get_mask_pil()
        if mask is None or not has_mask(mask):
            QMessageBox.information(self, "本地修补", "请先用画笔或矩形选中区域。")
            return
        try:
            result = inpaint(self.current_image, mask)
        except Exception as exc:
            QMessageBox.warning(self, "本地修补", f"处理失败：{exc}")
            return
        if self.history is None and self.original_image is not None:
            self.history = SessionHistory(self.config.output_dir, self.original_image)
        version = self.history.add_version(
            [result], prompt="本地修补", model="OpenCV", mask=mask, cost=0.0
        )
        self.current_image = result
        self.canvas.set_image(result)
        self.chat.set_candidates([result])
        self.chat.append_message(f"本地修补完成 · {version.id}", "success")
        self._update_status()

    def ai_erase(self) -> None:
        self._start_edit(
            "移除红色高亮区域中的物体或人物，并用周围环境自然填补，"
            "其他区域保持完全不变，边缘过渡自然。",
            require_mask=True,
        )

    def open_settings(self) -> None:
        if self._guard_busy():
            return
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._rebuild_services()
            self.chat.candidates_spin.setValue(self.config.candidates)
            self.chat.steps_spin.setValue(self.config.steps)
            self.chat.cfg_spin.setValue(self.config.cfg)
            self.chat.append_message("设置已保存", "system")
            if self.config.provider_ready:
                self.status_label.setText("已配置 API Key")
            self._update_status()

    def open_batch(self) -> None:
        if self._guard_busy():
            return
        if not self.config.provider_ready:
            QMessageBox.warning(self, "批量处理", "请先在设置中配置硅基流动 API Key。")
            self.open_settings()
            return
        dialog = BatchDialog(self.config, self.provider, self)
        dialog.exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于 PS Studio",
            "PS Studio 0.1.0\n\n"
            "基于 PySide6 的桌面图像编辑工具。\n"
            "AI 改图：硅基流动 Qwen-Image-Edit-2509\n"
            "本地能力：rembg 抠图、OpenCV 修补\n\n"
            "生成图片包含 AI 隐式水印，公开发布请标注 AI 生成。",
        )

    def _on_zoom(self, zoom: float) -> None:
        self.zoom_status.setText(f"{zoom * 100:.0f}%")

    def _update_status(self) -> None:
        if self.current_image is None:
            self.status_label.setText("未打开图片")
        else:
            self.status_label.setText(
                f"{self.current_image.width} × {self.current_image.height} · "
                f"{self.config.model.split('/')[-1]}"
            )
        self.model_status.setText(self.config.model.split("/")[-1])
        self.cost_status.setText(f"累计 ¥{self.total_cost:.2f}")
        self.chat.set_cost(self.total_cost)

    def eventFilter(self, obj, event) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and self.isActiveWindow()
            and event.key() == Qt.Key.Key_V
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            focus = QApplication.focusWidget()
            if isinstance(focus, (QLineEdit, QPlainTextEdit, QTextEdit)):
                return False
            self.paste_clipboard()
            return True
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".bmp",
                }:
                    self.open_path(path)
                    break

    def closeEvent(self, event) -> None:
        if self._is_busy():
            QMessageBox.information(
                self, "请稍候", "当前任务还没完成，请等待生成结束后再关闭。"
            )
            event.ignore()
            return
        self.config.total_cost = self.total_cost
        save_config(self.config)
        event.accept()

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from psapp.config import AppConfig
from psapp.core.batch import BatchJob
from psapp.providers.base import ImageEditProvider

from .workers import BatchWorker

IMAGE_FILTER = "图片 (*.png *.jpg *.jpeg *.webp *.bmp)"


class BatchDialog(QDialog):
    def __init__(
        self,
        config: AppConfig,
        provider: ImageEditProvider | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.provider = provider
        self.worker: BatchWorker | None = None
        self.files: list[Path] = []

        self.setWindowTitle("批量处理")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        add_button = QPushButton("添加图片")
        add_button.clicked.connect(self._add_files)
        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self._clear_files)
        top.addWidget(add_button)
        top.addWidget(clear_button)
        top.addStretch(1)
        self.count_label = QLabel("0 张")
        self.count_label.setObjectName("SectionTitle")
        top.addWidget(self.count_label)
        layout.addLayout(top)

        self.file_list = QListWidget()
        self.file_list.setFixedHeight(170)
        layout.addWidget(self.file_list)

        prompt_label = QLabel("统一指令")
        prompt_label.setObjectName("SectionTitle")
        layout.addWidget(prompt_label)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "应用到所有图片的修改指令，例如：把背景换成纯白色，保持主体不变"
        )
        self.prompt_edit.setFixedHeight(90)
        layout.addWidget(self.prompt_edit)

        output_row = QHBoxLayout()
        self.output_edit = QLineEdit(
            str(Path(config.output_dir) / f"batch-{datetime.now():%Y%m%d-%H%M%S}")
        )
        browse = QPushButton("输出目录")
        browse.clicked.connect(self._browse_output)
        output_row.addWidget(QLabel("输出到"))
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(browse)
        layout.addLayout(output_row)

        self.cost_label = QLabel("")
        self.cost_label.setObjectName("SectionTitle")
        layout.addWidget(self.cost_label)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("开始处理")
        self.start_button.setObjectName("PrimaryButton")
        self.start_button.clicked.connect(self._start)
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self._close)
        buttons.addStretch(1)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", IMAGE_FILTER)
        for raw in paths:
            path = Path(raw)
            if path not in self.files:
                self.files.append(path)
                self.file_list.addItem(str(path))
        self._refresh_count()

    def _clear_files(self) -> None:
        self.files.clear()
        self.file_list.clear()
        self._refresh_count()

    def _refresh_count(self) -> None:
        self.count_label.setText(f"{len(self.files)} 张")
        cost = len(self.files) * (self.provider.cost_per_image if self.provider else 0)
        self.cost_label.setText(f"预计费用约 ¥{cost:.2f}（失败不计费）")

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_edit.text()
        )
        if path:
            self.output_edit.setText(path)

    def _start(self) -> None:
        if self.provider is None or not self.config.provider_ready:
            QMessageBox.warning(self, "批量处理", "请先在设置中配置硅基流动 API Key")
            return
        if not self.files:
            QMessageBox.warning(self, "批量处理", "请先添加图片")
            return
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "批量处理", "请输入统一指令")
            return

        output_dir = Path(self.output_edit.text().strip())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.warning(self, "批量处理", f"无法创建输出目录：{exc}")
            return

        jobs: list[BatchJob] = []
        for path in self.files:
            target = output_dir / f"{path.stem}_edited.png"
            counter = 1
            while target.exists():
                counter += 1
                target = output_dir / f"{path.stem}_edited_{counter}.png"
            jobs.append(BatchJob(input_path=path, prompt=prompt, output_path=target))

        self.log.clear()
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self._set_running(True)

        self.worker = BatchWorker(
            jobs, self.provider, self.config.steps, self.config.cfg
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_succeeded)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_thread_finished)
        self.worker.start()

    def _set_running(self, running: bool) -> None:
        self.start_button.setDisabled(running)
        self.file_list.setDisabled(running)
        self.prompt_edit.setDisabled(running)
        self.output_edit.setDisabled(running)
        self.close_button.setText("停止" if running else "关闭")

    def _on_progress(self, index: int, total: int, message: str, ok: bool) -> None:
        self.progress.setValue(index)
        self.log.appendPlainText(("成功  " if ok else "失败  ") + message)

    def _on_succeeded(self, results: list) -> None:
        success = sum(1 for _, ok, _ in results if ok)
        failed = len(results) - success
        cost = success * self.provider.estimate_cost(1)
        self.log.appendPlainText(
            f"\n完成：成功 {success} 张，失败 {failed} 张，费用约 ¥{cost:.2f}"
        )
        QMessageBox.information(
            self,
            "批量处理",
            f"成功 {success} 张，失败 {failed} 张\n输出目录：{self.output_edit.text()}",
        )
        self._set_running(False)

    def _on_failed(self, message: str) -> None:
        self.log.appendPlainText(f"\n批量处理失败：{message}")
        QMessageBox.warning(self, "批量处理", message)
        self._set_running(False)

    def _on_thread_finished(self) -> None:
        worker = self.worker
        self.worker = None
        self.close_button.setText("关闭")
        if worker is not None:
            worker.deleteLater()

    def _close(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.close_button.setText("正在停止…")
            self.log.appendPlainText("已请求停止，等待当前图片处理完成…")
            return
        self.reject()

    def closeEvent(self, event) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.close_button.setText("正在停止…")
            self.log.appendPlainText("已请求停止，等待当前图片处理完成…")
            event.ignore()
            return
        super().closeEvent(event)

import sys
import time

from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QColor, QTextCharFormat


class OutputSignal(QObject):
    written = Signal(str)
    cleared = Signal()


class StreamRedirect:
    def __init__(self, signal, original=None):
        self._signal = signal
        self._original = original
        self._buffer = ""

    def write(self, text):
        self._buffer += text
        if "\n" in text:
            lines = self._buffer.split("\n")
            for line in lines[:-1]:
                self._signal.written.emit(line)
            self._buffer = lines[-1] if lines[-1] else ""

    def flush(self):
        if self._buffer:
            self._signal.written.emit(self._buffer)
            self._buffer = ""
        if self._original:
            self._original.flush()


class OutputPanel(QPlainTextEdit):
    COLORS = {
        "OK": QColor("#27ae60"),
        "FAIL": QColor("#e74c3c"),
        "SKIP": QColor("#f39c12"),
        "info": QColor("#2980b9"),
        "debug": QColor("#7f8c8d"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(10000)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._signal = OutputSignal()
        self._signal.written.connect(self.append_text)
        self._redirect = None
        self._saved_streams = {}

    def redirect_stdout(self):
        self._saved_streams["stdout"] = sys.stdout
        self._saved_streams["stderr"] = sys.stderr
        self._redirect = StreamRedirect(self._signal)
        sys.stdout = self._redirect
        sys.stderr = self._redirect

    def restore_stdout(self):
        if "stdout" in self._saved_streams:
            sys.stdout = self._saved_streams["stdout"]
        if "stderr" in self._saved_streams:
            sys.stderr = self._saved_streams["stderr"]
        self._saved_streams.clear()

    def clear_output(self):
        self.clear()

    def append_text(self, text):
        timestamp = time.strftime("[%H:%M:%S] ")
        text = timestamp + text
        fmt = QTextCharFormat()
        inner = text.split("] ", 2)[-1] if "] " in text else text
        if inner.startswith("[OK]"):
            fmt.setForeground(self.COLORS["OK"])
        elif inner.startswith("[FAIL]") or inner.startswith("[ERROR]"):
            fmt.setForeground(self.COLORS["FAIL"])
        elif inner.startswith("[SKIP]"):
            fmt.setForeground(self.COLORS["SKIP"])
        elif inner.startswith("  ") or inner.startswith("    ") or inner.startswith("     "):
            fmt.setForeground(self.COLORS["debug"])
        else:
            fmt.setForeground(QColor("#d4d4d4"))
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text + "\n", fmt)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

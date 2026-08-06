import asyncio
import sys

from PySide6.QtCore import QThread, Signal

from _shared import load_module


class DemoWorker(QThread):
    demo_finished = Signal(bool, str)

    def __init__(self, category, name, parent=None):
        super().__init__(parent)
        self._category = category
        self._name = name

    def run(self):
        try:
            module = load_module(self._category, self._name)
            fn = getattr(module, "run", None)
            if fn is None:
                raise AttributeError(f"{self._name}.py 中没有 run() 函数")
            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
            self.demo_finished.emit(True, "")
        except Exception as e:
            self.demo_finished.emit(False, str(e))

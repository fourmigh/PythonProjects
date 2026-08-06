from PySide6.QtCore import QObject, QTimer, Signal

from _shared import detect_opencode_binary, start_opencode, stop_opencode, _ping


class ServiceManager(QObject):
    status_changed = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ready = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._heartbeat)
        self._timer.setInterval(5000)

    @property
    def ready(self):
        return self._ready

    def start(self):
        if self._ready:
            self.status_changed.emit(True, "服务已就绪")
            return True

        def _print(msg):
            self.status_changed.emit(False, msg)

        candidates = detect_opencode_binary()
        if not candidates:
            self.status_changed.emit(False, "未找到 opencode 可执行文件")
            return False

        success = start_opencode(print_fn=_print)
        if success:
            self._ready = True
            self._timer.start()
        else:
            self.status_changed.emit(False, "启动失败，请手动运行 opencode serve")
        return success

    def stop(self):
        self._timer.stop()
        stop_opencode()
        self._ready = False
        self.status_changed.emit(False, "服务已停止")

    def _heartbeat(self):
        alive = _ping()
        if alive != self._ready:
            self._ready = alive
            self.status_changed.emit(alive, "服务已就绪" if alive else "服务连接丢失")

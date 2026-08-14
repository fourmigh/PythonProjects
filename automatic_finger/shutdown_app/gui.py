import argparse
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("缺少依赖 pyautogui，请先运行: pip install pyautogui pillow")
    sys.exit(1)

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shutdown_app.engine import (
    DEFAULT_PARAMS,
    compute_anchors,
    detect_env,
    ensure_elevated,
    run_shutdown_flow,
)

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

LOG_PATH = BASE_DIR / "电源助手.log"

COUNTDOWN_SECONDS = 5

TARGET_OPTIONS = ["睡眠", "关机", "重启"]


class ShutdownApp:
    def __init__(self, root, auto_dry=False, target="关机"):
        self.root = root
        self.log_queue = queue.Queue()
        self.running = False
        self.countdown_active = False
        self.countdown_value = 0
        self.countdown_after = None
        self.target_var = tk.StringVar(value=target)
        self.env = detect_env()
        self.anchors = compute_anchors(self.env)
        self.build_ui()
        self.drain_log()
        self._log("引擎状态：OCR 识别将在首次执行时加载")
        if auto_dry:
            self.root.after(600, lambda: self.start_countdown("dry"))

    def build_ui(self):
        root = self.root
        root.title("电源助手")
        root.resizable(False, False)
        self.center_window(560, 600)

        info = tk.Frame(root)
        info.pack(fill=tk.X, padx=12, pady=6)
        os_name = "Windows 11" if self.env["win11"] else "Windows 10"
        tk.Label(info, text=f"系统: {os_name} (build {self.env['build']})",
                 font=("Microsoft YaHei UI", 10)).pack(anchor="w")
        tk.Label(info, text=f"屏幕: {self.env['size'][0]}x{self.env['size'][1]}  "
                            f"任务栏: {self.env['orient']}",
                 font=("Microsoft YaHei UI", 10)).pack(anchor="w")
        self.status_label = tk.Label(
            info,
            text="引擎状态：等待执行",
            fg="#0070c0",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.status_label.pack(anchor="w", pady=(2, 0))

        tgt = tk.Frame(root)
        tgt.pack(fill=tk.X, padx=12, pady=6)
        tk.Label(tgt, text="目标操作:", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT)
        for name in TARGET_OPTIONS:
            tk.Radiobutton(tgt, text=name, variable=self.target_var, value=name,
                           font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT, padx=6)

        ops = tk.Frame(root)
        ops.pack(fill=tk.X, padx=12, pady=6)
        self.btn_dry = tk.Button(ops, text="干跑测试", command=lambda: self.start_countdown("dry"),
                                 width=14, font=("Microsoft YaHei UI", 11))
        self.btn_dry.pack(side=tk.LEFT, padx=6)
        self.btn_run = tk.Button(ops, text="开始执行", command=lambda: self.start_countdown("real"),
                                 width=18, bg="#ff4444", fg="white",
                                 font=("Microsoft YaHei UI", 11, "bold"))
        self.btn_run.pack(side=tk.LEFT, padx=6)

        cdown = tk.Frame(root)
        cdown.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(cdown, text="倒计时:", font=("Microsoft YaHei UI", 12)).pack(side=tk.LEFT)
        self.countdown_label = tk.Label(cdown, text="", fg="red", width=6,
                                        font=("Consolas", 20, "bold"))
        self.countdown_label.pack(side=tk.LEFT, padx=8)
        tk.Label(cdown, text="(想急停：把鼠标甩到屏幕左上角)",
                 fg="#666666", font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)

        logf = tk.LabelFrame(root, text="运行日志", font=("Microsoft YaHei UI", 10))
        logf.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self.log_text = tk.Text(logf, height=16, state=tk.DISABLED,
                                font=("Consolas", 10), wrap=tk.WORD)
        scroll = tk.Scrollbar(logf, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def center_window(self, w, h):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def start_countdown(self, kind):
        if self.running:
            return
        self.kind = kind
        self.countdown_active = True
        self.countdown_value = COUNTDOWN_SECONDS
        self._log(f"{'开始执行前' if kind == 'real' else '干跑测试前'}倒计时 {COUNTDOWN_SECONDS} 秒"
                  f"（目标：{self.target_var.get()}）")
        self.tick_countdown()

    def tick_countdown(self):
        if not self.countdown_active:
            return
        if self.countdown_after:
            self.root.after_cancel(self.countdown_after)
            self.countdown_after = None
        if self.countdown_value <= 0:
            self.countdown_active = False
            self.countdown_label.config(text="执行中")
            self.run_action(self.kind)
            return
        self.countdown_label.config(text=str(self.countdown_value))
        self.countdown_value -= 1
        self.countdown_after = self.root.after(1000, self.tick_countdown)

    def run_action(self, kind):
        self.running = True
        self.btn_dry.config(state=tk.DISABLED)
        self.btn_run.config(state=tk.DISABLED)
        self.status_label.config(text="引擎状态：执行中...")
        threading.Thread(target=self._worker, args=(kind,), daemon=True).start()

    def _worker(self, kind):
        try:
            tgt = self.target_var.get()
            self._log("正在加载 OCR 识别引擎（首次约需几秒）...")
            ok = run_shutdown_flow(
                dry_run=(kind == "dry"),
                log=self._log,
                params=dict(DEFAULT_PARAMS),
                target=tgt,
            )
            self._log("流程结束：" + (f"干跑完成，未点击{tgt}。" if kind == "dry" else f"已点击{tgt}。"))
        except pyautogui.FailSafeException:
            self._log("已触发急停(左上角)，操作取消。")
        except Exception as e:
            self._log(f"执行异常: {type(e).__name__}: {e}")
        finally:
            self.log_queue.put(("_DONE", kind))

    def _log(self, msg):
        self.log_queue.put(("log", msg))

    def drain_log(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self.append_log(payload)
                elif kind == "_DONE":
                    self.running = False
                    self.btn_dry.config(state=tk.NORMAL)
                    self.btn_run.config(state=tk.NORMAL)
                    self.status_label.config(text="引擎状态：空闲")
        except queue.Empty:
            pass
        except Exception as e:
            self.append_log(f"内部错误(drain_log): {type(e).__name__}: {e}")
        finally:
            self.root.after(80, self.drain_log)

    def append_log(self, msg):
        line = time.strftime("[%H:%M:%S] ") + msg
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="电源助手 (GUI)")
    parser.add_argument("--auto-dry", action="store_true",
                        help="启动后自动执行一次干跑测试（用于自动化验证）")
    parser.add_argument("--target", choices=["睡眠", "关机", "重启"], default="关机",
                        help="目标操作（默认关机；--auto-dry 时使用该目标）")
    args = parser.parse_args()
    if ensure_elevated():
        sys.exit(0)
    root = tk.Tk()
    app = ShutdownApp(root, auto_dry=args.auto_dry, target=args.target)

    def on_callback_error(exc, val, tb):
        import traceback
        try:
            app.append_log(f"界面错误: {type(exc).__name__}: {val}")
        except Exception:
            pass

    root.report_callback_exception = on_callback_error
    root.mainloop()


if __name__ == "__main__":
    main()
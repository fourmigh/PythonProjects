from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue

from .config import AppConfig
from .environment import CREATE_NO_WINDOW, Environment
from .events import Event
from .prompt import FilmRequest, build_prompt
from .util import strip_ansi


def _exe_args(path: str | Path, args: list[str]) -> list[str]:
    text = str(path)
    if text.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", text, *args]
    return [text, *args]


class FilmRunner:
    def __init__(
        self,
        config: AppConfig,
        environment: Environment,
        request: FilmRequest,
        events: "Queue[Event]",
    ) -> None:
        self.config = config
        self.environment = environment
        self.request = request
        self.events = events
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = threading.Event()
        self._started_at = 0.0
        self._log_handle = None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def elapsed(self) -> float:
        return max(0.0, time.time() - self._started_at) if self._started_at else 0.0

    def stop(self) -> None:
        self._stop_requested.set()
        process = self._process
        if process is not None and process.poll() is None:
            self.emit("status", "正在停止 ...")
            Environment.kill_tree(process.pid)

    def emit(self, kind: str, text: str = "", value: float | None = None, **data: object) -> None:
        self.events.put(Event(kind=kind, text=text, value=value, data=dict(data)))

    def log(self, text: str) -> None:
        text = strip_ansi(text)
        self.emit("log", text)
        if self._log_handle is not None:
            try:
                self._log_handle.write(text + "\n")
                self._log_handle.flush()
            except OSError:
                pass

    def run(self) -> None:
        self._started_at = time.time()
        self.config.logs.mkdir(parents=True, exist_ok=True)
        log_path = self.config.logs / f"{self.request.project}.log"
        try:
            self._log_handle = log_path.open("w", encoding="utf-8")
        except OSError:
            self._log_handle = None

        try:
            self._run_inner()
        except Exception as exc:
            self.log(f"运行失败: {exc}")
            self.emit("error", f"运行失败: {exc}")
        finally:
            if self._log_handle is not None:
                self._log_handle.close()
                self._log_handle = None
            self._process = None
            self.emit("finished")

    def _run_inner(self) -> None:
        exe = self.environment.detect_opencode()
        if not exe:
            raise RuntimeError("未找到 opencode CLI，请先点击“一键准备”")

        repo = self.config.repo
        if not (repo / "AGENTS.md").exists():
            raise RuntimeError("Lemo-Opuscar 仓库未准备好，请先点击“一键准备”")

        project_dir = repo / "films" / self.request.project
        project_dir.mkdir(parents=True, exist_ok=True)

        prompt = build_prompt(self.request)
        self.log("=" * 70)
        self.log(f"风格: {self.request.style.zh} / {self.request.style.en} ({self.request.style.slug})")
        self.log(f"主题: {self.request.topic.strip()}")
        self.log(f"时长: {self.request.duration}s  画幅: {self.request.aspect}  语言: {self.request.language}")
        self.log(f"旁白: {'开启' if self.request.voice else '关闭'}  模型: {self.request.model}")
        self.log(f"项目: films/{self.request.project}")
        self.log("=" * 70)
        self.log(prompt)

        help_text = self.environment.opencode_help()
        supports_model = "--model" in help_text or not help_text
        supports_auto = "--auto" in help_text or not help_text

        args = ["run"]
        if "--standalone" in help_text:
            args.append("--standalone")
        if supports_model:
            args.extend(["--model", self.request.model])
        if supports_auto:
            args.append("--auto")
        if "--dir" in help_text:
            args.extend(["--dir", str(repo)])
        args.append(prompt)

        env = self.environment.base_env()
        if not supports_model:
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"model": self.request.model})
        if not supports_auto:
            env["OPENCODE_PERMISSION"] = json.dumps(
                {
                    "bash": "allow",
                    "edit": "allow",
                    "webfetch": "allow",
                    "read": "allow",
                    "glob": "allow",
                    "grep": "allow",
                    "task": "allow",
                    "todowrite": "allow",
                    "skill": "allow",
                }
            )

        command = _exe_args(exe, args)
        self.log("$ " + " ".join(str(part) for part in command[:6]) + (" ..." if len(command) > 6 else ""))
        self.emit("status", "opencode 正在制作影片 ...")

        self._process = subprocess.Popen(
            command,
            cwd=str(repo),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )

        return_code = -1
        try:
            if self._process.stdout is not None:
                for raw_line in self._process.stdout:
                    if self._stop_requested.is_set():
                        Environment.kill_tree(self._process.pid)
                        break
                    line = strip_ansi(raw_line.rstrip("\r\n"))
                    if line:
                        self.log(line)
            return_code = self._process.wait()
        finally:
            if self._process.poll() is None:
                Environment.kill_tree(self._process.pid)
                return_code = self._process.wait()

        output = self._find_output(project_dir)
        if output is not None:
            self.emit("output", str(output), path=str(output))
            self.log(f"成片: {output}")

        if self._stop_requested.is_set():
            self.emit("status", "已停止")
            return
        if return_code != 0:
            raise RuntimeError(f"opencode 退出码 {return_code}，请查看日志或改用其他模型重试")
        if output is None:
            self.log("未找到 mp4 成片；agent 可能把文件放在了其他位置，请打开项目目录检查。")
            self.emit("status", "已完成，但未自动找到 mp4")
        else:
            self.emit("status", "完成")
            self.emit("done", str(output), path=str(output))

    def _find_output(self, project_dir: Path) -> Path | None:
        candidates: list[Path] = []
        if project_dir.exists():
            candidates = [path for path in project_dir.rglob("*.mp4") if path.is_file()]
        if not candidates:
            films = self.config.repo / "films"
            if films.exists():
                cutoff = self._started_at - 5
                candidates = [
                    path
                    for path in films.rglob("*.mp4")
                    if path.is_file() and path.stat().st_mtime >= cutoff
                ]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def open_output(self, path: str) -> None:
        target = Path(path)
        if target.exists():
            os.startfile(str(target))  # type: ignore[attr-defined]

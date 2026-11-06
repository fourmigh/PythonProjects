from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .config import AppConfig
from .util import strip_ansi

REPO_URL = "https://github.com/lemomo-ai/lemo-opuscar.git"
OPENCODE_URL = "https://opencode.ai/update/api/latest/cli/opencode/opencode-windows-x64.zip"
FFMPEG_URLS = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
]
SPARSE_PATTERNS = [
    "/*",
    "!/styles/*/demo/",
    "!/styleboard/",
    "!/docs/frames/",
    "!/docs/cover.jpg",
    "!/docs/opuscar98.jpg",
    "!/styles/*/poster.jpg",
]
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

LogFn = Callable[[str], None]
ProgressFn = Callable[[float, str], None]


class PrepareError(RuntimeError):
    pass


class PrepareCancelled(RuntimeError):
    pass


@dataclass
class Check:
    key: str
    label: str
    ok: bool
    detail: str = ""
    path: str = ""


def _command(path: str | Path, args: Sequence[str]) -> list[str]:
    text = str(path)
    if text.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", text, *args]
    return [text, *args]


class Environment:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._git_bash_ok: dict[str, bool] = {}
        self._opencode_help: str | None = None
        self._active_pids: set[int] = set()

    # ------------------------------------------------------------------ paths
    def detect_git_bash(self) -> str:
        candidates: list[str] = []
        if self.config.git_bash:
            candidates.append(self.config.git_bash)

        git = shutil.which("git")
        if git:
            rc, out = self._run_capture([git, "--exec-path"], timeout=20)
            if rc == 0 and out.strip():
                current = Path(out.strip())
                for parent in [current, *current.parents]:
                    candidates.append(str(parent / "bin" / "bash.exe"))
            git_path = Path(git)
            candidates.extend(
                [
                    str(git_path.parent / "bash.exe"),
                    str(git_path.parent.parent / "bin" / "bash.exe"),
                ]
            )

        candidates.extend(
            [
                r"F:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files (x86)\Git\bin\bash.exe",
            ]
        )
        bash = shutil.which("bash")
        if bash:
            candidates.append(bash)

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if Path(candidate).exists() and self._is_git_bash(candidate):
                return candidate
        return ""

    def _is_git_bash(self, path: str) -> bool:
        if path in self._git_bash_ok:
            return self._git_bash_ok[path]
        try:
            result = subprocess.run(
                [path, "-lc", "uname -s"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                creationflags=CREATE_NO_WINDOW,
            )
            name = (result.stdout or "") + (result.stderr or "")
            ok = "MINGW" in name or "MSYS" in name
        except (OSError, subprocess.SubprocessError):
            ok = False
        self._git_bash_ok[path] = ok
        return ok

    def detect_uv(self) -> str:
        candidates = [
            self.config.uv_exe,
            shutil.which("uv") or "",
            str(Path.home() / ".local" / "bin" / "uv.exe"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "uv" / "uv.exe"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def detect_opencode(self) -> str:
        candidates = [
            self.config.opencode_exe,
            str(self.config.tools / "opencode" / "opencode.exe"),
            shutil.which("opencode") or "",
            str(Path.home() / ".local" / "bin" / "opencode.exe"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def detect_ffmpeg(self) -> str:
        if self.config.ffmpeg_dir:
            base = Path(self.config.ffmpeg_dir)
            for candidate in (base, base / "bin"):
                if (candidate / "ffmpeg.exe").exists():
                    return str(candidate)
        found = shutil.which("ffmpeg")
        if found:
            return str(Path(found).parent)
        tools = self.config.tools
        if tools.exists():
            for exe in tools.rglob("ffmpeg.exe"):
                return str(exe.parent)
        return ""

    def refresh_detected_paths(self) -> None:
        changed = False
        values = [
            ("git_bash", self.detect_git_bash()),
            ("uv_exe", self.detect_uv()),
            ("opencode_exe", self.detect_opencode()),
            ("ffmpeg_dir", self.detect_ffmpeg()),
        ]
        for attr, value in values:
            if value and getattr(self.config, attr) != value:
                setattr(self.config, attr, value)
                changed = True
        if changed:
            self.config.save()

    def base_env(self) -> dict[str, str]:
        env = os.environ.copy()
        path_parts: list[str] = []
        opencode = self.detect_opencode()
        if opencode:
            path_parts.append(str(Path(opencode).parent))
        ffmpeg = self.detect_ffmpeg()
        if ffmpeg:
            path_parts.append(ffmpeg)
        git_bash = self.detect_git_bash()
        if git_bash:
            path_parts.append(str(Path(git_bash).parent))
        shims = self.config.tools / "shims"
        if shims.exists():
            path_parts.append(str(shims))
        path_parts.append(env.get("PATH", ""))
        env["PATH"] = os.pathsep.join(part for part in path_parts if part)
        try:
            env["LEMO_OPUSCAR_HOME"] = self._posix_path(self.config.repo)
            self.config.data.mkdir(parents=True, exist_ok=True)
            env["OPENCODE_DB"] = str(self.config.data / "opencode.db")
        except OSError:
            pass
        if git_bash:
            env["OPENCODE_GIT_BASH_PATH"] = git_bash
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    # ------------------------------------------------------------------ checks
    def check(self) -> list[Check]:
        self.refresh_detected_paths()
        checks: list[Check] = []

        git = shutil.which("git") or ""
        if git:
            rc, out = self._run_capture([git, "--version"], timeout=20)
            checks.append(Check("git", "Git", rc == 0, out.strip().splitlines()[0] if out.strip() else "", git))
        else:
            checks.append(Check("git", "Git", False, "未找到 git", ""))

        git_bash = self.detect_git_bash()
        detail = ""
        ok = False
        if git_bash:
            rc, out = self._run_capture([git_bash, "-lc", "uname -s"], timeout=20)
            detail = out.strip().splitlines()[-1] if out.strip() else "Git Bash"
            ok = rc == 0
        checks.append(Check("git_bash", "Git Bash", ok, detail or "未找到 Git Bash", git_bash))

        node = shutil.which("node") or ""
        node_ok = False
        node_detail = "未找到 node"
        if node:
            rc, out = self._run_capture([node, "--version"], timeout=20)
            version = out.strip()
            node_detail = version
            try:
                node_ok = rc == 0 and int(version.lstrip("v").split(".")[0]) >= 20
            except (ValueError, IndexError):
                node_ok = False
        checks.append(Check("node", "Node.js", node_ok, node_detail, node))

        npm = shutil.which("npm") or ""
        npm_ok = False
        npm_detail = "未找到 npm"
        if npm:
            rc, out = self._run_capture(_command(npm, ["--version"]), timeout=30)
            npm_ok = rc == 0
            npm_detail = out.strip().splitlines()[-1] if out.strip() else ""
        checks.append(Check("npm", "npm", npm_ok, npm_detail, npm))

        uv = self.detect_uv()
        uv_ok = False
        uv_detail = "未找到 uv"
        if uv:
            rc, out = self._run_capture(_command(uv, ["--version"]), timeout=20)
            uv_ok = rc == 0
            uv_detail = out.strip()
        checks.append(Check("uv", "uv", uv_ok, uv_detail, uv))

        ffmpeg = self.detect_ffmpeg()
        ffmpeg_ok = False
        ffmpeg_detail = "未找到 ffmpeg"
        if ffmpeg:
            rc, out = self._run_capture([str(Path(ffmpeg) / "ffmpeg.exe"), "-version"], timeout=30)
            ffmpeg_ok = rc == 0
            ffmpeg_detail = out.strip().splitlines()[0] if out.strip() else ""
        checks.append(Check("ffmpeg", "ffmpeg", ffmpeg_ok, ffmpeg_detail, ffmpeg))

        opencode = self.detect_opencode()
        opencode_ok = False
        opencode_detail = "未找到 opencode CLI"
        if opencode:
            rc, out = self._run_capture(_command(opencode, ["--version"]), timeout=40)
            opencode_ok = rc == 0
            opencode_detail = out.strip().splitlines()[-1] if out.strip() else ""
        checks.append(Check("opencode", "OpenCode CLI", opencode_ok, opencode_detail, opencode))

        repo = self.config.repo
        repo_ok = (repo / "AGENTS.md").exists() and (repo / "core" / "render").exists()
        style_count = 0
        if repo_ok:
            from .styles import STYLES

            style_count = sum(1 for style in STYLES if (repo / "styles" / style.slug / "STYLE.md").exists())
        checks.append(
            Check(
                "repo",
                "Lemo-Opuscar 仓库",
                repo_ok,
                f"{style_count} 个风格" if repo_ok else "未 clone 或文件不完整",
                str(repo),
            )
        )

        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        deps_ok = venv_python.exists() and (repo / "node_modules" / "playwright-core").exists()
        deps_detail = "已安装" if deps_ok else "未安装（运行“一键准备”）"
        checks.append(Check("deps", "Lemo 依赖", deps_ok, deps_detail, str(venv_python)))

        return checks

    # ------------------------------------------------------------------ prepare
    def prepare(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None = None) -> None:
        steps: list[tuple[str, Callable[[LogFn, ProgressFn, threading.Event | None], None]]] = [
            ("创建目录", self._step_dirs),
            ("检测 Git Bash", self._step_git_bash),
            ("下载 OpenCode CLI", self._step_opencode),
            ("下载 ffmpeg", self._step_ffmpeg),
            ("获取 Lemo-Opuscar 仓库", self._step_clone),
            ("创建 Python 3.12 环境", self._step_venv),
            ("安装 Lemo 依赖", self._step_deps),
            ("验证环境", self._step_verify),
        ]
        total = len(steps)
        for index, (label, func) in enumerate(steps):
            self._raise_if_cancelled(cancel)
            log(f"\n==> [{index + 1}/{total}] {label}")
            progress(index / total, label)

            def step_progress(fraction: float, text: str, i: int = index, name: str = label) -> None:
                fraction = max(0.0, min(1.0, fraction))
                progress((i + fraction) / total, f"{name}: {text}")

            func(log, step_progress, cancel)
            progress((index + 1) / total, f"{label} 完成")

        self.refresh_detected_paths()
        self.config.save()
        log("\n环境准备完成。")

    def _step_dirs(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        progress(0.5, "创建目录")
        self.config.ensure_dirs()
        self._create_path_shims()
        progress(1.0, "完成")

    def _step_git_bash(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        path = self.detect_git_bash()
        if not path:
            raise PrepareError(
                "未找到 Git Bash。请安装 Git for Windows 并确保存在 "
                r"F:\Program Files\Git\bin\bash.exe 或 C:\Program Files\Git\bin\bash.exe。"
            )
        self.config.git_bash = path
        log(f"Git Bash: {path}")
        progress(1.0, path)

    def _step_opencode(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._ensure_opencode(log, progress, cancel)

    def _step_ffmpeg(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._ensure_ffmpeg(log, progress, cancel)

    def _step_clone(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._ensure_repo(log, progress, cancel)

    def _step_venv(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._ensure_venv(log, progress, cancel)

    def _step_deps(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._ensure_deps(log, progress, cancel)

    def _step_verify(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        self._verify(log, progress, cancel)

    # ------------------------------------------------------------------ tools
    def _ensure_opencode(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        existing = self.detect_opencode()
        if existing:
            rc, out = self._run_capture(_command(existing, ["--version"]), timeout=40)
            if rc == 0:
                log(f"OpenCode CLI 已存在: {existing} ({out.strip().splitlines()[-1] if out.strip() else ''})")
                self.config.opencode_exe = existing
                progress(1.0, "已存在")
                return
            log(f"现有 OpenCode CLI 无法运行，重新下载: {existing}")

        zip_path = self.config.tools / "_downloads" / "opencode.zip"
        try:
            self._download(OPENCODE_URL, zip_path, "OpenCode CLI", log, progress, cancel)
            tmp_dir = self.config.tools / "_downloads" / "opencode_extract"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            tmp_dir.mkdir(parents=True, exist_ok=True)
            progress(0.85, "解压")
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(tmp_dir)
            found = next(tmp_dir.rglob("opencode.exe"), None)
            if found is None:
                raise PrepareError("OpenCode 压缩包中未找到 opencode.exe")
            target_dir = self.config.tools / "opencode"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "opencode.exe"
            shutil.copy2(found, target)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
            self.config.opencode_exe = str(target)
            rc, out = self._run_capture([str(target), "--version"], timeout=40)
            if rc != 0:
                raise PrepareError(f"opencode 无法运行: {out.strip()[-300:]}")
            log(f"OpenCode CLI 安装完成: {target}")
            progress(1.0, "完成")
        except PrepareCancelled:
            raise
        except Exception as exc:
            log(f"独立 CLI 安装失败: {exc}")
            log("尝试通过 npm 安装 @opencode/cli ...")
            npm = shutil.which("npm")
            if not npm:
                raise PrepareError("OpenCode CLI 下载失败，且未找到 npm 作为后备方案") from exc
            rc = self._run_streaming(
                _command(npm, ["install", "-g", "@opencode/cli"]),
                cwd=self.config.app_dir,
                log=log,
                cancel=cancel,
                env=self.base_env(),
            )
            if rc != 0:
                raise PrepareError("OpenCode CLI 安装失败，请检查网络后重试") from exc
            found = self._find_installed_opencode()
            if not found:
                raise PrepareError("npm 安装完成，但未找到 opencode 可执行文件") from exc
            self.config.opencode_exe = found
            log(f"OpenCode CLI 安装完成: {found}")
            progress(1.0, "完成")

    def _find_installed_opencode(self) -> str:
        candidates = [
            shutil.which("opencode") or "",
            str(Path(os.environ.get("APPDATA", "")) / "npm" / "opencode.cmd"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "pnpm" / "opencode.cmd"),
            str(Path.home() / ".local" / "bin" / "opencode.exe"),
        ]
        npm = shutil.which("npm")
        if npm:
            rc, out = self._run_capture(_command(npm, ["root", "-g"]), timeout=30)
            if rc == 0:
                root = Path(out.strip().splitlines()[-1]) if out.strip() else None
                if root:
                    candidates.extend(str(p) for p in root.rglob("opencode.exe"))
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def _ensure_ffmpeg(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        existing = self.detect_ffmpeg()
        if existing:
            rc, out = self._run_capture([str(Path(existing) / "ffmpeg.exe"), "-version"], timeout=30)
            if rc == 0:
                log(f"ffmpeg 已存在: {existing}")
                self.config.ffmpeg_dir = existing
                progress(1.0, "已存在")
                return

        last_error: Exception | None = None
        for url in FFMPEG_URLS:
            try:
                zip_path = self.config.tools / "_downloads" / "ffmpeg.zip"
                self._download(url, zip_path, "ffmpeg", log, progress, cancel)
                target_dir = self.config.tools / "ffmpeg"
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
                progress(0.85, "解压")
                with zipfile.ZipFile(zip_path) as archive:
                    archive.extractall(target_dir)
                found = next(target_dir.rglob("ffmpeg.exe"), None)
                if found is None:
                    raise PrepareError("ffmpeg 压缩包中未找到 ffmpeg.exe")
                self.config.ffmpeg_dir = str(found.parent)
                rc, out = self._run_capture([str(found), "-version"], timeout=30)
                if rc != 0:
                    raise PrepareError(f"ffmpeg 无法运行: {out.strip()[-300:]}")
                zip_path.unlink(missing_ok=True)
                log(f"ffmpeg 安装完成: {found.parent}")
                progress(1.0, "完成")
                return
            except PrepareCancelled:
                raise
            except Exception as exc:
                last_error = exc
                log(f"ffmpeg 下载失败，尝试下一个源: {exc}")
        raise PrepareError(f"ffmpeg 安装失败: {last_error}")

    def _ensure_repo(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        repo = self.config.repo
        if (repo / "AGENTS.md").exists() and (repo / "core" / "render").exists():
            log(f"仓库已存在，跳过 clone: {repo}")
            progress(1.0, "已存在")
            return
        if repo.exists() and any(repo.iterdir()):
            raise PrepareError(f"目录已存在但不是 Lemo-Opuscar 仓库: {repo}")

        git = shutil.which("git")
        if not git:
            raise PrepareError("未找到 git，无法 clone 仓库")
        repo.parent.mkdir(parents=True, exist_ok=True)
        progress(0.1, "clone 仓库")
        rc = self._run_streaming(
            [
                git,
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                "main",
                REPO_URL,
                str(repo),
            ],
            cwd=self.config.app_dir,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("git clone 失败，请检查网络或代理设置")
        progress(0.8, "配置稀疏检出")
        self._apply_sparse(log, cancel)
        if not (repo / "AGENTS.md").exists():
            raise PrepareError("仓库 clone 完成，但缺少 AGENTS.md")
        log(f"仓库准备完成: {repo}")
        progress(1.0, "完成")

    def _apply_sparse(self, log: LogFn, cancel: threading.Event | None) -> None:
        git = shutil.which("git")
        if not git:
            return
        rc = self._run_streaming(
            [git, "-C", str(self.config.repo), "sparse-checkout", "set", "--no-cone", *SPARSE_PATTERNS],
            cwd=self.config.repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            log("稀疏检出未生效，继续使用完整仓库。")

    def _ensure_venv(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        repo = self.config.repo
        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            self._create_venv_shims()
            log(f"Python 虚拟环境已存在: {venv_python}")
            progress(1.0, "已存在")
            return

        if (repo / ".venv").exists() and not venv_python.exists():
            log("现有 .venv 不完整，重新创建 ...")
            shutil.rmtree(repo / ".venv", ignore_errors=True)

        uv = self.detect_uv()
        if not uv:
            log("未找到 uv，尝试通过 pip 安装 ...")
            self._run_streaming(
                [sys.executable, "-m", "pip", "install", "--user", "uv"],
                cwd=self.config.app_dir,
                log=log,
                cancel=cancel,
                env=self.base_env(),
            )
            uv = self.detect_uv()
        if not uv:
            raise PrepareError("未找到 uv。请先安装 uv：https://docs.astral.sh/uv/")

        self.config.uv_exe = uv
        progress(0.2, "创建 Python 3.12 环境")
        rc = self._run_streaming(
            _command(uv, ["venv", "--python", "3.12", ".venv"]),
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0 or not venv_python.exists():
            raise PrepareError("创建 Python 3.12 虚拟环境失败。请检查 uv 是否能下载 Python 3.12。")
        self._create_venv_shims()
        log(f"Python 虚拟环境创建完成: {venv_python}")
        progress(1.0, "完成")

    def _create_venv_shims(self) -> None:
        repo = self.config.repo
        bin_dir = repo / ".venv" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        scripts = {
            "python": "python.exe",
            "python3": "python.exe",
            "pip": "pip.exe",
            "pip3": "pip.exe",
        }
        for name, target in scripts.items():
            path = bin_dir / name
            content = f'#!/bin/sh\nexec "$(dirname "$0")/../Scripts/{target}" "$@"\n'
            path.write_text(content, encoding="utf-8", newline="\n")
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass

        shim_dir = self.config.tools / "shims"
        shim_dir.mkdir(parents=True, exist_ok=True)
        venv_python = self._posix_path(repo / ".venv" / "Scripts" / "python.exe")
        for name in ("python", "python3"):
            path = shim_dir / name
            path.write_text(f'#!/bin/sh\nexec "{venv_python}" "$@"\n', encoding="utf-8", newline="\n")
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass

    def _create_path_shims(self) -> None:
        shim_dir = self.config.tools / "shims"
        shim_dir.mkdir(parents=True, exist_ok=True)
        for name, command in (("python3", "python"), ("pip3", "python -m pip")):
            path = shim_dir / name
            path.write_text(f'#!/bin/sh\nexec {command} "$@"\n', encoding="utf-8", newline="\n")
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass

    def _ensure_deps(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        repo = self.config.repo
        bash = self.detect_git_bash()
        if not bash:
            raise PrepareError("未找到 Git Bash，无法执行 Lemo 安装脚本")

        progress(0.1, "运行官方安装脚本")
        script_env = self.base_env()
        script_env["LEMO_OPUSCAR_HOME"] = self._posix_path(repo)
        rc = self._run_streaming(
            [bash, "-lc", "sh plugin/skills/lemo-opuscar/scripts/setup.sh deps voice music"],
            cwd=repo,
            log=log,
            cancel=cancel,
            env=script_env,
        )
        if rc != 0:
            log("\n官方安装脚本未成功，改用逐项安装 ...")
            self._install_deps_direct(log, progress, cancel)
        else:
            progress(0.9, "写入兼容标记")
            self._write_markers(log)
        self._ensure_voice_model(log, cancel)
        progress(1.0, "完成")

    def _install_deps_direct(
        self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None
    ) -> None:
        repo = self.config.repo
        npm = shutil.which("npm")
        node = shutil.which("node")
        uv = self.detect_uv()
        if not npm or not node or not uv:
            raise PrepareError("缺少 npm、node 或 uv，无法安装依赖")

        progress(0.2, "npm install")
        rc = self._run_streaming(
            _command(npm, ["install", "--no-audit", "--no-fund", "--loglevel=error"]),
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("npm install 失败")

        progress(0.45, "安装 Playwright Chromium")
        rc = self._run_streaming(
            [node, "node_modules/playwright-core/cli.js", "install", "chromium-headless-shell"],
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("Playwright Chromium 安装失败")

        progress(0.65, "安装 Python 依赖")
        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        requirements = [repo / "requirements.txt", repo / "requirements-voice.txt", repo / "requirements-music.txt"]
        args = _command(uv, ["pip", "install", "--python", str(venv_python)])
        for requirement in requirements:
            if requirement.exists():
                args.extend(["-r", str(requirement)])
        rc = self._run_streaming(
            args,
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("Python 依赖安装失败")
        self._write_markers(log)

    @staticmethod
    def _posix_path(path: Path) -> str:
        text = str(path.resolve()).replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", text):
            text = f"/{text[0].lower()}{text[2:]}"
        return text

    def _ensure_voice_model(self, log: LogFn, cancel: threading.Event | None) -> None:
        repo = self.config.repo
        model = repo / "core" / "tts" / "kokoro-v1.0.onnx"
        voices = repo / "core" / "tts" / "voices-v1.0.bin"
        if model.exists() and voices.exists():
            return
        bash = self.detect_git_bash()
        if not bash:
            log("! 未找到 Git Bash，跳过 Kokoro 语音模型下载")
            return
        log("下载 Kokoro 语音模型 ...")
        rc = self._run_streaming(
            [bash, "-lc", "sh tools/fetch.sh voice"],
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            log("! Kokoro 语音模型下载失败；中文旁白仍可尝试使用 edge-tts（需要联网）。")

    def _write_markers(self, log: LogFn) -> None:
        repo = self.config.repo
        bash = self.detect_git_bash()
        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        if not bash or not venv_python.exists():
            return
        rc, output = self._run_capture(
            [str(venv_python), "-c", "import sys;print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"],
            timeout=20,
        )
        if rc != 0:
            return
        python_signature = output.strip().splitlines()[-1]
        for tier, filename in (
            ("core", "requirements.txt"),
            ("voice", "requirements-voice.txt"),
            ("music", "requirements-music.txt"),
        ):
            requirement = repo / filename
            if not requirement.exists():
                continue
            rc, output = self._run_capture([bash, "-lc", f"cksum {filename}"], cwd=repo, env=self.base_env())
            parts = output.strip().split()
            if rc != 0 or not parts:
                continue
            marker = repo / ".venv" / f".lemo-{tier}"
            marker.write_text(f"{parts[0]}-{python_signature}\n", encoding="utf-8")
        log("已写入 Lemo 兼容标记。")

    def _verify(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None) -> None:
        progress(0.2, "检查文件")
        errors: list[str] = []
        repo = self.config.repo
        venv_python = repo / ".venv" / "Scripts" / "python.exe"
        if not (repo / "AGENTS.md").exists():
            errors.append("缺少 repo/AGENTS.md")
        if not venv_python.exists():
            errors.append("缺少 .venv/Scripts/python.exe")
        else:
            rc, out = self._run_capture(
                [str(venv_python), "-c", "import numpy, scipy, soundfile, soxr, PIL; print('ok')"],
                timeout=60,
            )
            if rc != 0:
                errors.append(f"Python 依赖导入失败: {out.strip()[-300:]}")
        if not (repo / "node_modules" / "playwright-core").exists():
            errors.append("缺少 node_modules/playwright-core")
        if not self.detect_opencode():
            errors.append("未找到 opencode CLI")
        if not self.detect_ffmpeg():
            errors.append("未找到 ffmpeg")

        progress(0.8, "检查完成")
        if errors:
            raise PrepareError("环境验证失败：\n- " + "\n- ".join(errors))
        log("环境验证通过。")
        progress(1.0, "通过")

    def update_repo(self, log: LogFn, progress: ProgressFn, cancel: threading.Event | None = None) -> None:
        repo = self.config.repo
        if not (repo / "AGENTS.md").exists():
            raise PrepareError("仓库尚未准备，无法更新")
        git = shutil.which("git")
        if not git:
            raise PrepareError("未找到 git")
        progress(0.1, "fetch")
        rc = self._run_streaming(
            [git, "fetch", "--depth", "1", "origin", "main"],
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("git fetch 失败")
        progress(0.6, "reset")
        rc = self._run_streaming(
            [git, "reset", "--hard", "FETCH_HEAD"],
            cwd=repo,
            log=log,
            cancel=cancel,
            env=self.base_env(),
        )
        if rc != 0:
            raise PrepareError("git reset 失败")
        progress(0.8, "稀疏检出")
        self._apply_sparse(log, cancel)
        self._create_venv_shims()
        progress(1.0, "完成")
        log("仓库已更新。")

    # ------------------------------------------------------------------ models
    def opencode_models(self) -> list[str]:
        exe = self.detect_opencode()
        if exe:
            args = ["models"]
            if "--standalone" in self.opencode_help():
                args.append("--standalone")
            rc, output = self._run_capture(
                _command(exe, args),
                cwd=self.config.repo,
                env=self.base_env(),
                timeout=180,
            )
            if rc == 0:
                models = self._parse_models(strip_ansi(output))
                if models:
                    return models
        return self._models_from_cache()

    @staticmethod
    def _parse_models(text: str) -> list[str]:
        found: set[str] = set()
        for line in text.splitlines():
            line = line.strip()
            if re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._:-]+", line):
                found.add(line)
        priority = {"opencode": 0, "opencode-go": 0, "zai-coding-plan": 1, "zhipuai": 2}
        return sorted(found, key=lambda item: (priority.get(item.split("/", 1)[0], 9), item))

    def _models_from_cache(self) -> list[str]:
        cache = Path.home() / ".cache" / "opencode" / "models.json"
        if not cache.exists():
            return []
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            for provider_name in ("opencode", "opencode-go"):
                provider = data.get(provider_name) or {}
                models = provider.get("models") or {}
                if isinstance(models, dict) and models:
                    return sorted(f"{provider_name}/{name}" for name in models)
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def opencode_help(self) -> str:
        if self._opencode_help is not None:
            return self._opencode_help
        exe = self.detect_opencode()
        if not exe:
            self._opencode_help = ""
            return ""
        rc, output = self._run_capture(_command(exe, ["run", "--help"]), timeout=60)
        self._opencode_help = output if rc == 0 else ""
        return self._opencode_help

    # ------------------------------------------------------------------ run helpers
    def _run_capture(
        self,
        command: Sequence[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = 60,
    ) -> tuple[int, str]:
        try:
            result = subprocess.run(
                list(command),
                cwd=str(cwd) if cwd else None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        except FileNotFoundError:
            return 127, f"command not found: {command[0]}"
        except subprocess.TimeoutExpired:
            return 124, f"timeout: {command[0]}"
        except OSError as exc:
            return 126, str(exc)

    def _run_streaming(
        self,
        command: Sequence[str],
        cwd: str | Path | None,
        log: LogFn,
        cancel: threading.Event | None = None,
        env: dict[str, str] | None = None,
        check: bool = False,
    ) -> int:
        log("$ " + " ".join(str(part) for part in command))
        try:
            process = subprocess.Popen(
                list(command),
                cwd=str(cwd) if cwd else None,
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
        except FileNotFoundError as exc:
            raise PrepareError(f"找不到命令: {command[0]}") from exc

        self._active_pids.add(process.pid)
        return_code = -1
        try:
            if process.stdout is not None:
                for raw_line in process.stdout:
                    if cancel is not None and cancel.is_set():
                        self.kill_tree(process.pid)
                        raise PrepareCancelled()
                    line = strip_ansi(raw_line.rstrip("\r\n"))
                    if line:
                        log(line)
            return_code = process.wait()
        finally:
            if process.poll() is None:
                self.kill_tree(process.pid)
            self._active_pids.discard(process.pid)
        if check and return_code != 0:
            raise PrepareError(f"命令失败 (exit {return_code}): {command[0]}")
        return return_code

    def _download(
        self,
        url: str,
        destination: Path,
        label: str,
        log: LogFn,
        progress: ProgressFn,
        cancel: threading.Event | None,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".part")
        temp.unlink(missing_ok=True)
        log(f"下载 {label}: {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "Lemo-Opuscar-UI/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                last_percent = -1
                while True:
                    if cancel is not None and cancel.is_set():
                        raise PrepareCancelled()
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    if total:
                        percent = int(done * 100 / total)
                        if percent >= last_percent + 5 or percent == 100:
                            last_percent = percent
                            progress(done / total, f"{label} {percent}%")
                            log(f"  {label}: {percent}% ({done // 1048576} MB / {total // 1048576} MB)")
                    else:
                        progress(0.5, f"{label} {done // 1048576} MB")
        except PrepareCancelled:
            temp.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temp.unlink(missing_ok=True)
            raise PrepareError(f"下载失败：{label}: {exc}") from exc

        if not temp.exists() or temp.stat().st_size == 0:
            temp.unlink(missing_ok=True)
            raise PrepareError(f"下载失败：{label} 文件为空")
        temp.replace(destination)
        log(f"已下载 {label}: {destination}")

    def terminate_all(self) -> None:
        for pid in list(self._active_pids):
            self.kill_tree(pid)
        self._active_pids.clear()

    @staticmethod
    def kill_tree(pid: int) -> None:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=CREATE_NO_WINDOW,
                )
            except OSError:
                pass
        else:
            try:
                os.kill(pid, 9)
            except OSError:
                pass

    @staticmethod
    def _raise_if_cancelled(cancel: threading.Event | None) -> None:
        if cancel is not None and cancel.is_set():
            raise PrepareCancelled()

    def smoke_test(self, model: str, log: LogFn) -> tuple[bool, str]:
        exe = self.detect_opencode()
        if not exe:
            return False, "未找到 opencode CLI"
        if not model:
            return False, "未选择模型"
        args = ["run", "--model", model]
        help_text = self.opencode_help()
        if "--standalone" in help_text:
            args.append("--standalone")
        if "--auto" in help_text:
            args.append("--auto")
        args.append("只回复 OK")
        rc, output = self._run_capture(
            _command(exe, args),
            cwd=self.config.repo,
            env=self.base_env(),
            timeout=180,
        )
        log(f"smoke test exit={rc}")
        if output.strip():
            log(output.strip()[-4000:])
        return rc == 0, output

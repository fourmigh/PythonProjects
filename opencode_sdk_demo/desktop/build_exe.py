"""PyInstaller 构建脚本 — 打包为单 exe

用法:
    python desktop/build_exe.py

输出: dist/OpenCodeDemo.exe (~70MB)

说明:
    - 桌面应用代码 (desktop/) 会打包进 exe
    - Demo 示例文件 (*.py) 保持原路径，随 exe 一起分发
"""
import os
import pathlib
import subprocess
import sys


def build():
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    dist_dir = repo_root / "dist"
    entry_point = repo_root / "desktop" / "main.py"
    icon_path = repo_root / "desktop" / "resources" / "icon.ico"
    work_dir = repo_root / "build" / "pyinstaller"

    os.chdir(repo_root)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "OpenCodeDemo",
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(repo_root),
        "--hidden-import", "desktop",
        "--hidden-import", "desktop.service_manager",
        "--hidden-import", "desktop.output_panel",
        "--hidden-import", "desktop.demo_tree",
        "--hidden-import", "desktop.demo_worker",
        "--hidden-import", "desktop.main_window",
        "--hidden-import", "opencode_ai",
        "--hidden-import", "httpx",
        "--hidden-import", "pydantic",
        "--hidden-import", "anyio",
        "--collect-all", "opencode_ai",
    ]

    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.append(str(entry_point))

    print("=" * 60)
    print("  OpenCode Demo - PyInstaller 打包")
    print("=" * 60)
    print()
    print(f"  入口:      {entry_point}")
    print(f"  输出:      {dist_dir}/OpenCodeDemo.exe")
    print(f"  模式:      --onefile / --windowed")
    print(f"  Python:    {sys.version}")
    print()

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        print()
        print("[OK] 构建成功")
        exe_path = dist_dir / "OpenCodeDemo.exe"
        size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
        print(f"     输出: {exe_path} ({size_mb:.1f} MB)")
    else:
        print()
        print(f"[FAIL] 构建失败 (返回码 {result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    build()

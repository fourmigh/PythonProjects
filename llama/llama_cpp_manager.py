#!/usr/bin/env python3
"""
llama.cpp 管理模块
提供安装、更新、卸载、状态检查等功能
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List


class LLaMACppManager:
    """llama.cpp 管理器 - 编译安装/更新/卸载"""

    LLAMA_CPP_REPO = "https://github.com/ggerganov/llama.cpp.git"
    MIRROR_REPOS = [
        ("GitHub 官方",     "https://github.com/ggerganov/llama.cpp.git"),
        ("KJHhub 镜像",     "https://hub.kjj.xyz/https://github.com/ggerganov/llama.cpp.git"),
        ("GhProxy 镜像",    "https://ghproxy.net/https://github.com/ggerganov/llama.cpp.git"),
        ("GitClone 镜像",   "https://gitclone.com/github.com/ggerganov/llama.cpp.git"),
    ]
    BUILD_DIR = "build"

    def __init__(self, llama_path: Path):
        """
        :param llama_path: 项目根目录
        """
        self.root_path = Path(llama_path).resolve()
        self.src_path = self.root_path / "llama.cpp"
        self.build_path = self.src_path / self.BUILD_DIR

    def check_prerequisites(self) -> bool:
        """检查编译工具链是否可用，缺失时询问是否自动安装"""
        missing = []

        if not self._check_command("git", "--version"):
            missing.append("git")

        if not self._check_command("cmake", "--version"):
            missing.append("cmake")

        if not missing:
            print("[OK] 编译工具链完整")
            return True

        print("[X] 缺少以下工具:")
        for tool in missing:
            print(f"   - {tool}")

        pm = self._detect_package_manager()
        if pm:
            print(f"\n[INFO] 检测到包管理器: {pm}")
            confirm = input("是否自动安装缺失的依赖? (Y/n): ").strip().lower()
            if confirm != 'n':
                if self._install_missing(pm, missing):
                    return True
                print("\n[WARN] 自动安装未完全成功，请尝试手动安装")

        self._show_manual_install_help()
        return False

    def _detect_package_manager(self) -> Optional[str]:
        """检测系统包管理器"""
        if sys.platform == "win32":
            return None
        for pm in ["apt-get", "dnf", "yum", "pacman", "brew", "zypper"]:
            if shutil.which(pm):
                return pm
        return None

    def _install_missing(self, pm: str, missing_tools: List[str]) -> bool:
        """自动安装缺失的依赖"""
        package_map = {
            "git":   {"apt-get": "git", "dnf": "git", "yum": "git", "pacman": "git", "brew": "git", "zypper": "git"},
            "cmake": {"apt-get": "cmake", "dnf": "cmake", "yum": "cmake", "pacman": "cmake", "brew": "cmake", "zypper": "cmake"},
        }
        extra_map = {
            "apt-get": ["build-essential"],
            "dnf":     ["gcc-c++", "make"],
            "yum":     ["gcc-c++", "make"],
            "pacman":  ["gcc", "make"],
            "brew":    [],
            "zypper":  ["gcc-c++", "make"],
        }

        packages = []
        for tool in missing_tools:
            pkg = package_map.get(tool, {}).get(pm)
            if pkg:
                packages.append(pkg)

        extra = extra_map.get(pm, [])
        packages.extend(pkg for pkg in extra if pkg not in packages)

        if not packages:
            print("[X] 未知的工具配置")
            return False

        print(f"\n[INSTALL] 即将安装: {' '.join(packages)}")

        if pm == "apt-get":
            cmds = [
                ["sudo", "apt-get", "update", "-qq"],
                ["sudo", "apt-get", "install", "-y"] + packages,
            ]
        elif pm in ("dnf", "yum"):
            cmds = [["sudo", pm, "install", "-y"] + packages]
        elif pm == "pacman":
            cmds = [["sudo", "pacman", "-S", "--noconfirm"] + packages]
        elif pm == "brew":
            cmds = [["brew", "install"] + packages]
        elif pm == "zypper":
            cmds = [["sudo", "zypper", "install", "-y"] + packages]
        else:
            print(f"[X] 不支持的包管理器: {pm}")
            return False

        for cmd in cmds:
            print(f"\n> {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"[X] 命令执行失败: {e}")
                return False

        print("\n[INFO] 验证安装结果...")
        still_missing = [t for t in missing_tools if not self._check_command(t, "--version")]
        if still_missing:
            print(f"[X] 以下工具仍未安装: {', '.join(still_missing)}")
            return False

        print("[OK] 所有依赖安装完成")
        return True

    def _show_manual_install_help(self):
        """显示手动安装提示"""
        print()
        if sys.platform == "win32":
            print("   请手动安装:")
            print("   - git: https://git-scm.com")
            print("   - cmake: https://cmake.org")
            print("   - Visual Studio (含 C++ 开发工具)")
        else:
            print("   请手动安装 (Ubuntu/Debian):")
            print("   sudo apt update")
            print("   sudo apt install git cmake build-essential")
            print()
            print("   或 (Fedora/RHEL/CentOS):")
            print("   sudo dnf install git cmake gcc-c++ make")
            print()
            print("   或 (Arch Linux):")
            print("   sudo pacman -S git cmake gcc make")
            print()
            print("   或 (macOS):")
            print("   brew install git cmake gcc make")

    def _check_command(self, cmd: str, arg: str) -> bool:
        try:
            subprocess.run([cmd, arg], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_exe_names(self) -> tuple:
        if sys.platform == "win32":
            return "llama-cli.exe", "llama-server.exe"
        return "llama-cli", "llama-server"

    def _find_built_exe(self, name: str) -> Optional[Path]:
        candidates = [
            self.build_path / "bin" / name,
            self.build_path / "bin" / "Release" / name,
            self.build_path / "bin" / "Debug" / name,
            self.src_path / name,
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def _clone_with_mirrors(self) -> bool:
        """使用多个镜像源依次尝试克隆"""
        for i, (name, url) in enumerate(self.MIRROR_REPOS, 1):
            # 删除失败残留目录
            if self.src_path.exists():
                shutil.rmtree(self.src_path)

            total = len(self.MIRROR_REPOS)
            print(f"  尝试 ({i}/{total}): {name} ...")
            try:
                subprocess.run(
                    ["git", "clone", url, str(self.src_path),
                     "--depth", "1"],
                    check=True, capture_output=True, text=True
                )
                print(f"  [OK] 通过 {name} 克隆成功")
                return True
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.strip() if e.stderr else str(e)
                print(f"  [X] {name} 失败: {err_msg.split(chr(10))[0]}")
                continue

        return False

    def status(self):
        """显示 llama.cpp 安装状态"""
        print("\n" + "=" * 50)
        print("[STATUS] llama.cpp 状态检查")
        print("=" * 50)

        cli_name, server_name = self._get_exe_names()
        cli_path = self.root_path / cli_name
        server_path = self.root_path / server_name

        print(f"  源码目录: {self.src_path}")
        print(f"  构建目录: {self.build_path}")
        print()

        if self.src_path.exists():
            print(f"  [YES] 源码已克隆")
            if (self.src_path / ".git").exists():
                try:
                    result = subprocess.run(
                        ["git", "-C", str(self.src_path), "log", "--oneline", "-1"],
                        capture_output=True, text=True, check=True
                    )
                    print(f"  最新提交: {result.stdout.strip()}")
                except Exception:
                    pass
        else:
            print(f"  [NO]  源码未克隆")

        if self.build_path.exists():
            print(f"  [YES] CMake 已配置")
        else:
            print(f"  [NO]  CMake 未配置")

        cli_exists = cli_path.exists()
        server_exists = server_path.exists()

        if cli_exists:
            cli_size = cli_path.stat().st_size / (1024 ** 2)
            print(f"  [YES] {cli_name} ({cli_size:.1f} MB)")
        else:
            print(f"  [NO]  {cli_name} (未安装)")

        if server_exists:
            server_size = server_path.stat().st_size / (1024 ** 2)
            print(f"  [YES] {server_name} ({server_size:.1f} MB)")
        else:
            print(f"  [NO]  {server_name} (未安装)")

        print()
        if cli_exists and server_exists:
            print("[INFO] 状态: 已安装，可直接使用")
        elif self.src_path.exists():
            print("[INFO] 状态: 已克隆但未编译，请执行安装")
        else:
            print("[INFO] 状态: 未安装")
        print("=" * 50)

    def install(self) -> bool:
        """安装 llama.cpp（clone + cmake build）"""
        print("\n" + "=" * 50)
        print("[INSTALL] 安装 llama.cpp")
        print("=" * 50)

        if not self.check_prerequisites():
            return False

        cli_name, server_name = self._get_exe_names()

        if (self.root_path / cli_name).exists() and (self.root_path / server_name).exists():
            print("[WARN] llama.cpp 已安装")
            confirm = input("重新安装? (y/N): ").strip().lower()
            if confirm != 'y':
                print("[OK] 取消安装")
                return False

        if not self.src_path.exists():
            print("\n[1/4] 克隆源码...")
            if not self._clone_with_mirrors():
                print("\n[X] 所有镜像均克隆失败")
                print("   你可以尝试:")
                print("   1. 检查网络连接后重试")
                print("   2. 使用代理: export https_proxy=http://127.0.0.1:7890")
                print("   3. 手动克隆后重新运行安装:")
                print(f"      git clone --depth 1 {self.LLAMA_CPP_REPO} {self.src_path}")
                return False
        else:
            print("\n[1/4] 源码已存在，跳过克隆")

        print("\n[2/4] CMake 配置...")
        try:
            subprocess.run(
                ["cmake", "-B", str(self.build_path), "-S", str(self.src_path)],
                check=True
            )
            print("[OK] CMake 配置完成")
        except subprocess.CalledProcessError as e:
            print(f"[X] CMake 配置失败: {e}")
            return False

        print("\n[3/4] 编译中（可能需要数分钟）...")
        try:
            subprocess.run(
                ["cmake", "--build", str(self.build_path), "--config", "Release"],
                check=True
            )
            print("[OK] 编译完成")
        except subprocess.CalledProcessError as e:
            print(f"[X] 编译失败: {e}")
            return False

        print("\n[4/4] 复制可执行文件...")
        for name in [cli_name, server_name]:
            built = self._find_built_exe(name)
            if built:
                dest = self.root_path / name
                shutil.copy2(built, dest)
                dest_size = dest.stat().st_size / (1024 ** 2)
                print(f"  [OK] {name} ({dest_size:.1f} MB)")
            else:
                print(f"  [X] 未找到编译产物: {name}")

        print(f"\n[OK] 安装完成!")
        return True

    def update(self) -> bool:
        """更新 llama.cpp（git pull + rebuild）"""
        print("\n" + "=" * 50)
        print("[UPDATE] 更新 llama.cpp")
        print("=" * 50)

        if not self.src_path.exists():
            print("[X] 源码未克隆，请先安装")
            return False

        if not self.build_path.exists():
            print("[X] CMake 未配置，请先安装")
            return False

        cli_name, server_name = self._get_exe_names()

        print("\n[1/3] 拉取最新源码...")
        try:
            result = subprocess.run(
                ["git", "-C", str(self.src_path), "pull"],
                check=True, capture_output=True, text=True
            )
            output = result.stdout.strip()
            if output:
                print(output)
            print("[OK] 拉取完成")
        except subprocess.CalledProcessError as e:
            print(f"[X] 拉取失败: {e}")
            return False

        print("\n[2/3] 重新编译...")
        try:
            subprocess.run(
                ["cmake", "--build", str(self.build_path), "--config", "Release"],
                check=True
            )
            print("[OK] 编译完成")
        except subprocess.CalledProcessError as e:
            print(f"[X] 编译失败: {e}")
            return False

        print("\n[3/3] 更新可执行文件...")
        for name in [cli_name, server_name]:
            built = self._find_built_exe(name)
            if built:
                dest = self.root_path / name
                shutil.copy2(built, dest)
                dest_size = dest.stat().st_size / (1024 ** 2)
                print(f"  [OK] {name} ({dest_size:.1f} MB)")

        print(f"\n[OK] 更新完成!")
        return True

    def uninstall(self) -> bool:
        """卸载 llama.cpp"""
        print("\n" + "=" * 50)
        print("[UNINSTALL] 卸载 llama.cpp")
        print("=" * 50)

        cli_name, server_name = self._get_exe_names()

        to_delete = []

        if self.src_path.exists():
            to_delete.append(("源码目录", self.src_path))
        if (self.root_path / cli_name).exists():
            to_delete.append((cli_name, self.root_path / cli_name))
        if (self.root_path / server_name).exists():
            to_delete.append((server_name, self.root_path / server_name))

        if not to_delete:
            print("[INFO] 未检测到 llama.cpp 相关文件")
            return False

        print("\n即将删除以下内容:")
        for desc, path in to_delete:
            size = ""
            if path.is_file():
                size = f" ({path.stat().st_size / 1024 ** 2:.1f} MB)"
            print(f"  - {desc}: {path}{size}")

        confirm = input("\n确认卸载? 此操作不可恢复! (y/N): ").strip().lower()
        if confirm != 'y':
            print("[OK] 取消卸载")
            return False

        for desc, path in to_delete:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"  [OK] 已删除: {desc}")
            except Exception as e:
                print(f"  [X] 删除失败 {desc}: {e}")

        print(f"\n[OK] 卸载完成")
        return True

    def interactive_menu(self):
        """交互式子菜单"""
        while True:
            print("\n" + "=" * 50)
            print("[LLAMA] llama.cpp 管理")
            print("=" * 50)
            print("1. [INSTALL]   安装")
            print("2. [UPDATE]    更新")
            print("3. [UNINSTALL] 卸载")
            print("4. [STATUS]    查看状态")
            print("0. [BACK]     返回主菜单")
            print("=" * 50)

            choice = input("\n请选择操作: ").strip()

            if choice == '1':
                self.install()
            elif choice == '2':
                self.update()
            elif choice == '3':
                self.uninstall()
            elif choice == '4':
                self.status()
            elif choice == '0':
                break
            else:
                print("[X] 无效的选择")

        return True


if __name__ == "__main__":
    manager = LLaMACppManager(Path.cwd())
    manager.interactive_menu()

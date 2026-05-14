#!/usr/bin/env python3
"""
DeepSeek TUI 安装脚本 - 修复版本
解决 dbus 依赖和 Windows 挂载目录问题
"""

import os
import sys
import subprocess
import shutil

def run_cmd(cmd, desc=None):
    """执行命令"""
    if desc:
        print(f"\n[任务] {desc}...")
    print(f"命令: {cmd}")
    
    result = subprocess.run(cmd, shell=True, text=True)
    if result.returncode == 0:
        print(f"[成功] 完成")
        return True
    else:
        print(f"[失败] 返回码: {result.returncode}")
        return False

def main():
    print("=" * 60)
    print("DeepSeek TUI 安装脚本")
    print("=" * 60)
    
    # 1. 安装系统依赖
    print("\n[步骤1] 安装系统依赖")
    deps = [
        "build-essential",
        "pkg-config", 
        "libssl-dev",
        "libdbus-1-dev",  # 关键依赖
        "curl",
        "git"
    ]
    
    cmd = f"sudo apt update && sudo apt install -y {' '.join(deps)}"
    if not run_cmd(cmd, "安装编译依赖"):
        print("依赖安装失败")
        sys.exit(1)
    
    # 2. 检查/安装 Rust
    print("\n[步骤2] 检查 Rust")
    result = subprocess.run("cargo --version", shell=True, capture_output=True)
    if result.returncode != 0:
        print("安装 Rust...")
        cmd = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
        if not run_cmd(cmd, "安装 Rust"):
            sys.exit(1)
        
        # 加载环境
        cargo_home = os.path.expanduser("~/.cargo/env")
        if os.path.exists(cargo_home):
            subprocess.run(f"source {cargo_home}", shell=True)
    
    # 3. 配置 Cargo 镜像
    print("\n[步骤3] 配置中科大镜像")
    cargo_config = os.path.expanduser("~/.cargo/config.toml")
    os.makedirs(os.path.dirname(cargo_config), exist_ok=True)
    
    with open(cargo_config, 'w') as f:
        f.write("""
[source.crates-io]
replace-with = 'ustc'

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"

[http]
timeout = 60
multiplexing = true

[net]
git-fetch-with-cli = true
retry = 5
""")
    print("[成功] 镜像配置完成")
    
    # 4. 切换到 home 目录编译
    print("\n[步骤4] 编译安装 DeepSeek TUI")
    print("重要: 切换到 ~/ 目录编译，避免 Windows 挂载目录问题")
    
    original_dir = os.getcwd()
    os.chdir(os.path.expanduser("~"))
    
    # 清理临时文件
    subprocess.run("rm -rf /mnt/f/temp/cargo-install*", shell=True)
    subprocess.run("cargo clean", shell=True)
    
    # 安装
    cmd = "cargo install deepseek-tui --locked"
    if run_cmd(cmd, "编译安装 (需要10-15分钟)"):
        print("\n[成功] 安装完成！")
        
        # 验证
        cargo_bin = os.path.expanduser("~/.cargo/bin")
        deepseek = os.path.join(cargo_bin, "deepseek-tui")
        
        if os.path.exists(deepseek):
            subprocess.run(f"{deepseek} --version", shell=True)
            
            # 添加到 PATH
            bashrc = os.path.expanduser("~/.bashrc")
            with open(bashrc, 'r') as f:
                if f"export PATH={cargo_bin}:$PATH" not in f.read():
                    with open(bashrc, 'a') as f2:
                        f2.write(f'\nexport PATH="{cargo_bin}:$PATH"\n')
                    print("\n[配置] 已添加到 ~/.bashrc")
            
            print("\n" + "=" * 60)
            print("使用方法:")
            print("  source ~/.bashrc  # 重载环境")
            print("  deepseek-tui      # 启动程序")
            print("  export DEEPSEEK_API_KEY='your-api-key'  # 设置 API Key")
            print("=" * 60)
        else:
            print("[失败] 未找到可执行文件")
    else:
        print("\n[失败] 编译失败")
        print("\n手动解决步骤:")
        print("1. 安装依赖: sudo apt install libdbus-1-dev pkg-config")
        print("2. 切换到 home: cd ~")
        print("3. 清理缓存: cargo clean")
        print("4. 重新安装: cargo install deepseek-tui --locked")
        sys.exit(1)
    
    os.chdir(original_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
import json
import os
import subprocess
import sys

PIP_MIRROR = 'https://pypi.tuna.tsinghua.edu.cn/simple'


def _load_config():
    path = os.path.join(os.path.dirname(__file__), 'programs.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _check(entry):
    check_cmd = entry['check']
    if check_cmd.startswith('import '):
        mod = check_cmd.split()[1]
        try:
            __import__(mod)
            return True
        except ImportError:
            return False
    else:
        return subprocess.run(check_cmd, shell=True, capture_output=True).returncode == 0


def _pip(args, mirror=None):
    cmd = [sys.executable, '-m', 'pip'] + args
    if mirror:
        cmd += ['-i', mirror]
    return subprocess.run(cmd)


def install_python_packages(mirror=PIP_MIRROR):
    cfg = _load_config()
    failed = 0
    for entry in cfg['python_packages']:
        name = entry['name']
        if _check(entry):
            print(f"  [跳过] {name} 已安装")
            continue
        hint = " (需下载 ~500MB 依赖，请耐心等待)" if name == 'easyocr' else ""
        print(f"  [安装] {name}{hint}...", flush=True)
        r = _pip(['install', entry['install']], mirror=mirror)
        if r.returncode == 0:
            print(f"  [完成] {name} 安装成功")
        else:
            print(f"  镜像失败，尝试官方源...", flush=True)
            r = _pip(['install', entry['install']])
            if r.returncode == 0:
                print(f"  [完成] {name} 安装成功")
            else:
                print(f"  [失败] {name}")
                failed += 1

    # 对齐系统 requests 与已升级的依赖版本，消除版本警告
    r = _pip(['install', '--upgrade', 'requests'], mirror=mirror)
    if r.returncode != 0:
        print(f"  [警告] requests 升级失败")
    return failed


def remove_python_packages():
    return failed


def remove_python_packages():
    cfg = _load_config()
    failed = 0
    for entry in cfg['python_packages']:
        name = entry['name']
        print(f"  [卸载] {name}...", end=' ')
        r = _pip(['uninstall', '-y', entry['uninstall']])
        if r.returncode == 0:
            print("OK")
        else:
            print(f"失败\n{r.stderr.strip()}")
            failed += 1
    return failed


def install_system_tools():
    cfg = _load_config()
    failed = 0
    for entry in cfg['system_tools']:
        name = entry['name']
        if _check(entry):
            print(f"  [跳过] {name} 已安装")
            continue
        print(f"  [安装] {name}...", end=' ')
        r = subprocess.run(entry['install'], shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            print("OK")
        else:
            print(f"失败\n{r.stderr.strip()}")
            failed += 1
    return failed


def remove_system_tools():
    cfg = _load_config()
    failed = 0
    for entry in cfg['system_tools']:
        name = entry['name']
        print(f"  [卸载] {name}...", end=' ')
        r = subprocess.run(entry['uninstall'], shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            print("OK")
        else:
            print(f"失败\n{r.stderr.strip()}")
            failed += 1
    return failed


def install_browsers():
    cfg = _load_config()
    failed = 0
    for entry in cfg['browsers']:
        name = entry['name']
        if _check(entry):
            print(f"  [跳过] {name} 已安装")
            continue
        print(f"  [安装] {name}...", end=' ')
        r = subprocess.run(entry['install'], shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            print("OK")
        else:
            print(f"失败\n{r.stderr.strip()}")
            failed += 1
    return failed


def remove_browsers():
    cfg = _load_config()
    failed = 0
    for entry in cfg['browsers']:
        name = entry['name']
        print(f"  [卸载] {name}...", end=' ')
        r = subprocess.run(entry['uninstall'], shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            print("OK")
        else:
            print(f"失败\n{r.stderr.strip()}")
            failed += 1
    return failed


def install_all(mirror=PIP_MIRROR):
    print("[依赖] 检查并安装依赖...")
    if mirror:
        print(f"  PyPI 镜像: {mirror}")
    f1 = install_python_packages(mirror=mirror)
    f2 = install_system_tools()
    f3 = install_browsers()
    total = f1 + f2 + f3
    if total:
        print(f"[完成] 安装完成，{total} 项失败")
    else:
        print("[完成] 全部就绪")


def remove_all():
    print("[依赖] 卸载所有依赖...")
    remove_python_packages()
    remove_system_tools()
    remove_browsers()
    print("[完成] 卸载完成")


if __name__ == '__main__':
    install_all()

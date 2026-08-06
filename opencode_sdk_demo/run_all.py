"""Opencode SDK Python Demo - 交互式运行器（CLI）

共享模块见 _shared.py，此处仅为 CLI 菜单界面。
"""
import asyncio
import sys

from opencode_ai import APIConnectionError

from _shared import (
    BASE_DIR, DEMO_ORDER, DEMOS,
    load_module, get_description,
    check_connection, start_opencode, stop_opencode,
)


def print_header():
    print()
    print("=" * 56)
    print("  Opencode SDK Python Demo - 交互式菜单")
    print("=" * 56)
    print()


def print_menu():
    current_cat = None
    for num, cat, name in DEMOS:
        if cat != current_cat:
            current_cat = cat
            cat_label = cat.split("_", 1)[1] if "_" in cat else cat
            print(f"  {cat_label}:")
        desc = get_description(cat, name)
        short = desc.split("。")[0].split("\n")[0] if desc else ""
        label = name.split("_", 1)[1] if "_" in name else name
        print(f"    [{num:2d}] {label}")
        if short:
            print(f"         {short}")
    print()
    print("  [a]  全部运行（按顺序自动执行所有 Demo）")
    print("  [q]  退出")
    print()


def show_demo_desc(num, cat, name):
    full_desc = get_description(cat, name)
    label = name.split("_", 1)[1] if "_" in name else name
    print()
    print("=" * 56)
    print(f"  [{num}] {label}")
    print("=" * 56)
    print()
    print(f"  分类: {cat}")
    if full_desc:
        print()
        print(f"  {full_desc}")
    print()
    print(f"  文件: {cat}/{name}.py")
    print()


def run_one(num, cat, name):
    label = f"[{num:02d}] {name}"
    try:
        module = load_module(cat, name)
        fn = getattr(module, "run", None)
        if fn is None:
            raise AttributeError(f"{name}.py 中没有 run() 函数")
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn())
        else:
            fn()
        print()
        print(f"  [OK] {label} 执行成功")
        return True
    except Exception as e:
        if isinstance(e, APIConnectionError):
            print()
            print(f"  [SKIP] {label} 跳过（需要 opencode 服务）")
            return False
        print()
        print(f"  [FAIL] {label} 执行失败: {e}")
        return False


def run_all():
    print()
    print("=" * 56)
    print("  全部运行模式")
    print("=" * 56)
    print()

    passed = 0
    skipped = 0
    failed = []

    for num, cat, name in DEMOS:
        label = f"[{num:02d}] {name}"
        print(f"{'=' * 50}")
        print(f"  开始: {label}")
        print(f"{'=' * 50}")
        print()

        try:
            module = load_module(cat, name)
            fn = getattr(module, "run", None)
            if fn is None:
                raise AttributeError(f"{name}.py 中没有 run() 函数")
            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
            passed += 1
            print()
            print(f"  [OK] {label} 执行成功")
        except Exception as e:
            if isinstance(e, APIConnectionError):
                skipped += 1
                print()
                print(f"  [SKIP] {label} 跳过（需要 opencode 服务）")
            else:
                failed.append((label, str(e)))
                print()
                print(f"  [FAIL] {label} 执行失败: {e}")
        print()

    print("=" * 56)
    print("  汇总报告")
    print("=" * 56)
    print(f"  总计: {len(DEMOS)} 个 Demo")
    print(f"  成功: {passed} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  失败: {len(failed)} 个")

    if skipped > 0:
        print()
        print(f"  跳过的 {skipped} 个 Demo 需要连接 opencode 服务。")
    if failed:
        print()
        for label, reason in failed:
            print(f"  [FAIL] {label}: {reason}")


def main():
    print_header()

    connected = check_connection()
    if connected:
        print("opencode 服务已就绪。")
    else:
        print("opencode 服务未连接，需要网络的 Demo 将自动跳过。")
    print()

    while True:
        print_menu()
        choice = input(f"  请输入编号 (1-{len(DEMOS)}, a, q): ").strip().lower()

        if choice == "q":
            print("  正在关闭...")
            stop_opencode()
            print("  已退出。")
            break

        if choice == "a":
            run_all()
            print()
            input("  按 Enter 键返回菜单...")
            print_header()
            continue

        try:
            num = int(choice)
        except ValueError:
            print(f"  无效输入: {choice}")
            continue

        match = [d for d in DEMOS if d[0] == num]
        if not match:
            print(f"  无效编号: {num}")
            continue

        _, cat, name = match[0]
        show_demo_desc(num, cat, name)
        confirm = input("  确认运行？(y/n): ").strip().lower()
        if confirm == "y":
            print()
            run_one(num, cat, name)
            print()
            input("  按 Enter 键返回菜单...")
        print_header()


if __name__ == "__main__":
    main()

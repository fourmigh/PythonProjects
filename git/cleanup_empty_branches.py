import subprocess
import sys


ZERO_OID = "0" * 40
BASE_CANDIDATES = ["master", "main", "develop"]


def run_git(args):
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=False,
    )


def get_local_branches():
    result = run_git(
        ["for-each-ref", "refs/heads", "--format=%(refname:short)|%(objectname)"]
    )
    if result.returncode != 0:
        print("获取本地分支失败:", result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    branches = {}
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        name, oid = line.split("|", 1)
        branches[name] = oid
    return branches


def get_current_branch():
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_unborn_branch():
    """检测当前是否处于 unborn（空/从未提交）分支。

    unborn 分支没有 ref，for-each-ref 列不出，只能通过检查
    git rev-parse --verify HEAD 失败来判断；它总是当前所在分支，
    且 git 不允许删除当前分支。此时 rev-parse --abbrev-ref HEAD
    返回 HEAD，需用 symbolic-ref 取真实分支名。
    """
    result = run_git(["rev-parse", "--verify", "HEAD"])
    if result.returncode != 0:
        sym = run_git(["symbolic-ref", "--short", "-q", "HEAD"])
        if sym.returncode == 0 and sym.stdout.strip():
            return sym.stdout.strip()
        return "HEAD"
    return None


def find_base_branch(branches, current):
    for name in BASE_CANDIDATES:
        if name in branches:
            return name
    return current


def get_merged_branches(base):
    """返回相对 base 无独有提交（已并入 base）的本地分支列表。"""
    result = run_git(["branch", "--merged", base])
    if result.returncode != 0:
        print("执行 git branch --merged 失败:", result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    names = []
    for line in result.stdout.splitlines():
        name = line.strip().lstrip("*").strip()
        if name and name not in names:
            names.append(name)
    return names


def confirm(prompt):
    while True:
        answer = input(f"{prompt} [y/N] ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no", ""):
            return False
        print("请输入 y 或 n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    dry_run = "--dry-run" in sys.argv
    branches = get_local_branches()
    unborn = get_unborn_branch()

    if unborn:
        print(f"检测到当前所在分支「{unborn}」是空分支（从未提交过 commit）。")
        print("但 git 不允许删除当前所在的分支，请先切换到其它分支后再删除它。")
        return

    current = get_current_branch()
    base = find_base_branch(branches, current)
    if base is None:
        print("无法确定基准分支，程序退出。")
        return

    merged = get_merged_branches(base)
    candidates = [name for name in merged if name != base and name != current]

    if not candidates:
        print(f"未发现相对基准分支「{base}」无独有提交的本地分支，程序退出。")
        return

    print(f"基准分支：{base}")
    print("发现以下分支相对基准分支没有独有提交（可安全删除）：")
    for name in candidates:
        print(f"  - {name}")

    if dry_run:
        print("\n[DRY-RUN] 未执行删除。")
        return

    deleted, declined = [], []
    for name in candidates:
        if confirm(f'删除分支 "{name}"?'):
            result = run_git(["branch", "-d", name])
            if result.returncode == 0:
                deleted.append(name)
            else:
                print(f"删除 {name} 失败:", result.stderr.strip())
        else:
            declined.append(name)

    print("\n=== 结果 ===")
    if deleted:
        print("已删除:", "、".join(deleted))
    if declined:
        print("跳过:", "、".join(declined))
    if not deleted and not declined:
        print("无操作")


if __name__ == "__main__":
    main()

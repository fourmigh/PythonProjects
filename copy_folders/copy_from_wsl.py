import os
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    WSL_ROOT = Path(r"\\wsl.localhost\Ubuntu-22.04\root")
    DEST_BASE = Path(r"F:\Projects")
else:  # linux / wsl
    WSL_ROOT = Path("/root")
    DEST_BASE = Path("/mnt/f/Projects")


def list_directories(path):
    dirs = []
    for entry in os.scandir(path):
        if entry.is_dir():
            dirs.append(entry.name)
    return sorted(dirs)


def count_files(src):
    total = 0
    for dirpath, _, filenames in os.walk(src):
        total += len(filenames)
    return total


def copy_with_progress(src, dst):
    total = count_files(src)
    copied = 0
    for dirpath, dirnames, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        dest_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(dest_dir, exist_ok=True)
        for filename in filenames:
            shutil.copy2(os.path.join(dirpath, filename), os.path.join(dest_dir, filename))
            copied += 1
            print(f"\rProgress: [{copied}/{total}] {filename}", end="", flush=True)
    print()


def main():
    src = WSL_ROOT
    if not src.exists():
        print(f"Error: path not found: {WSL_ROOT}")
        sys.exit(1)

    dirs = list_directories(src)
    if not dirs:
        print("No directories found.")
        sys.exit(1)

    print(f"Directories in {WSL_ROOT}:")
    for i, d in enumerate(dirs, 1):
        print(f"  {i}. {d}")

    while True:
        choice = input("\nSelect number (or q to quit): ").strip()
        if choice.lower() == "q":
            sys.exit(0)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dirs):
                break
            print(f"Please enter 1-{len(dirs)}")
        except ValueError:
            print("Invalid input")

    selected = dirs[idx]
    src_path = src / selected
    dest_path = DEST_BASE / selected

    if dest_path.exists():
        resp = input(f"Destination {dest_path} already exists. Overwrite? (y/N): ")
        if resp.lower() != "y":
            print("Cancelled.")
            sys.exit(0)
        shutil.rmtree(dest_path)

    print(f"Copying {src_path} -> {dest_path} ...")
    copy_with_progress(str(src_path), str(dest_path))
    print("Done!")


if __name__ == "__main__":
    main()

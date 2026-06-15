import os
import sys
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.error
import json
from collections import deque

META_FILE = ".download_state"


def enable_ansi():
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(h, ctypes.byref(mode))
        kernel32.SetConsoleMode(h, mode.value | 0x0004)


def detect_proxy_host():
    try:
        r = subprocess.run(["ip", "route"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            parts = line.split()
            if "default" in parts and "via" in parts:
                return parts[parts.index("via") + 1]
    except:
        pass
    return None


def detect_proxy():
    host = detect_proxy_host()
    if not host:
        return None
    for port in [7890, 10809, 1081, 8080, 3128, 8888, 1080]:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                s.close()
                return f"http://{host}:{port}"
            s.close()
        except:
            continue
    return None


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_eta(seconds):
    if seconds <= 0:
        return "0:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def progress_bar(pct, width=20):
    filled = int(pct * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def get_file_info(url):
    print("Connecting...")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            with urllib.request.urlopen(req, timeout=15) as resp:
                size = int(resp.headers.get("Content-Length", 0))
                accepts_ranges = resp.headers.get("Accept-Ranges", "").lower() == "bytes"
                return size, accepts_ranges
        except Exception as e:
            if attempt < 2:
                print(f"  Retrying HEAD request... ({attempt + 1}/3)")
                time.sleep(3 ** attempt)
            else:
                print(f"Error: cannot reach server after 3 attempts.")
                print(f"  {e}")
                print("Hint: set HTTPS_PROXY if behind a firewall, e.g.")
                print("  export HTTPS_PROXY=http://127.0.0.1:7890")
                print("Diagnostic: run 'curl -IL \"{}\"' from WSL to check connectivity.".format(url))
                sys.exit(1)


def build_chunks(total_size, thread_count):
    base = total_size // thread_count
    remainder = total_size % thread_count
    chunks = []
    start = 0
    for i in range(thread_count):
        size = base + (1 if i < remainder else 0)
        if size <= 0:
            break
        chunks.append((i, start, size))
        start += size
    return chunks


def save_state(url, save_path, total_size, thread_count, completed_indices):
    data = {
        "url": url,
        "save_path": save_path,
        "total_size": total_size,
        "thread_count": thread_count,
        "completed": sorted(completed_indices),
    }
    with open(META_FILE, "w") as f:
        json.dump(data, f)


def load_state():
    try:
        with open(META_FILE) as f:
            data = json.load(f)
        return data["url"], data["save_path"], data["total_size"], data["thread_count"], set(data["completed"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def clear_state():
    if os.path.exists(META_FILE):
        os.remove(META_FILE)
    for fname in os.listdir("."):
        if fname.startswith("chunk_") and fname.endswith(".tmp"):
            os.remove(fname)


def download_chunk(url, chunk_idx, offset, size):
    chunk_path = f"chunk_{chunk_idx}.tmp"
    max_retries = 3
    range_val = f"{offset}-{offset + size - 1}"
    for attempt in range(max_retries):
        try:
            subprocess.run(
                ["curl", "-sS", "-o", chunk_path,
                 "--range", range_val,
                 "--connect-timeout", "5",
                 "--max-time", "60",
                 "-L", url],
                check=True, capture_output=True, text=True,
                timeout=90,
            )
            if os.path.getsize(chunk_path) < size:
                raise IOError(f"expected {size} bytes, got {os.path.getsize(chunk_path)}")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def worker(url, chunk_idx, offset, size, completed_set, failed_set, total_downloaded, worker_idx, thread_stats, lock):
    with lock:
        thread_stats[worker_idx]["status"] = f"chunk {chunk_idx} connecting..."

    try:
        download_chunk(url, chunk_idx, offset, size)
        with lock:
            completed_set.add(chunk_idx)
            total_downloaded[0] += size
            thread_stats[worker_idx]["downloaded"] += size
            thread_stats[worker_idx]["chunks_done"] = 1
            thread_stats[worker_idx]["status"] = "ok"
    except Exception as e:
        with lock:
            failed_set.add(chunk_idx)
            thread_stats[worker_idx]["status"] = f"failed (chunk {chunk_idx})"


def display_loop(thread_stats, lock, completed_set, num_chunks, total_size, total_downloaded, display_stop):
    n = len(thread_stats)
    lines_to_redraw = n + 2
    history = [deque(maxlen=15) for _ in range(n)]

    def render():
        now = time.time()
        with lock:
            downloaded = total_downloaded[0]
            pct = downloaded / total_size if total_size else 0
            done = len(completed_set)
            for i in range(n):
                history[i].append((now, thread_stats[i]["downloaded"]))

        total_speed = 0.0
        speeds = []
        for i in range(n):
            h = history[i]
            speed = 0.0
            if len(h) >= 2:
                t0, b0 = h[0]
                t1, b1 = h[-1]
                dt = t1 - t0
                if dt > 0:
                    speed = (b1 - b0) / dt
            total_speed += speed
            speeds.append(speed)

        overall_eta = (total_size - downloaded) / total_speed if total_speed > 0 else 0

        print(f"\033[{lines_to_redraw}A", end="")
        bar = progress_bar(pct)
        os_str = f"{human_size(total_speed)}/s" if total_speed > 0 else "---"
        oe_str = format_eta(overall_eta) if total_speed > 0 else "---"
        print(f"Overall: {pct * 100:5.1f}% {bar} {human_size(downloaded):>10} / {human_size(total_size)}  {os_str:>10}  ETA {oe_str}  ({done}/{num_chunks} chunks)\033[K")
        print("\033[K")
        for i in range(n):
            s_str = f"{human_size(speeds[i])}/s" if speeds[i] > 0 else "---"
            cd = thread_stats[i].get("chunks_done", 0)
            st = thread_stats[i].get("status", "")
            if cd:
                print(f"Thread {i + 1:2d}: {s_str:>10}  done  {st}\033[K")
            else:
                print(f"Thread {i + 1:2d}: {s_str:>10}         {st}\033[K")
        sys.stdout.flush()

    print()
    for _ in range(n + 1):
        print()
    sys.stdout.flush()

    while not display_stop.is_set():
        render()
        time.sleep(0.2)

    render()


def main():
    enable_ansi()
    socket.setdefaulttimeout(15)

    if not os.environ.get("HTTPS_PROXY"):
        proxy = detect_proxy()
        if proxy:
            os.environ["HTTPS_PROXY"] = proxy
            print(f"Proxy auto-detected: {proxy}")
        else:
            print("No proxy found. Connection may fail.")

    state = load_state()
    url = save_path = total_size = thread_count = None
    completed_set = set()
    loaded_from_state = False

    if state:
        saved_url, saved_path, saved_size, saved_threads, saved_completed = state
        chunks = build_chunks(saved_size, saved_threads)
        actual_completed = set()
        completed_bytes = 0
        for idx, offset, size in chunks:
            chunk_path = f"chunk_{idx}.tmp"
            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) >= size:
                actual_completed.add(idx)
                completed_bytes += size

        done_mb = completed_bytes / 1024 / 1024
        total_mb = saved_size / 1024 / 1024
        print(f"\nUnfinished download found:")
        print(f"  URL: {saved_url}")
        print(f"  File: {saved_path} ({done_mb:.1f} MB / {total_mb:.1f} MB)")
        print(f"  Chunks: {len(actual_completed)}/{len(chunks)}")

        while True:
            choice = input("Resume [1] / New download [2] / Remove state [3]: ").strip()
            if choice == "1":
                url, save_path, total_size, thread_count = saved_url, saved_path, saved_size, saved_threads
                completed_set = actual_completed
                loaded_from_state = True
                break
            elif choice == "2":
                clear_state()
                state = None
                break
            elif choice == "3":
                clear_state()
                print("State and temporary files removed.")
                sys.exit(0)
            else:
                print("Please enter 1, 2, or 3.")

    if not loaded_from_state:
        url = input("URL: ").strip()
        if not url:
            print("URL is required.")
            sys.exit(1)

        thread_input = input("Thread count (default 4): ").strip()
        thread_count = int(thread_input) if thread_input else 4
        if thread_count < 1:
            thread_count = 1

        default_name = url.rstrip("/").split("/")[-1] or "download"
        save_path = input(f"Save as (default {default_name}): ").strip() or default_name

        print("Checking server support...")
        total_size, accepts_ranges = get_file_info(url)

        if not accepts_ranges or total_size <= 0:
            print("Server does not support range requests, using single thread.")
            thread_count = 1

        if total_size <= 0:
            print("Could not determine file size.")
            sys.exit(1)

        print(f"File size: {human_size(total_size)}, Threads: {thread_count}")

    chunks = build_chunks(total_size, thread_count)
    num_chunks = len(chunks)

    lock = threading.Lock()
    save_state(url, save_path, total_size, thread_count, completed_set)
    total_downloaded = [sum(size for idx, _, size in chunks if idx in completed_set)]

    remaining = [(idx, offset, size) for idx, offset, size in chunks if idx not in completed_set]

    if not remaining:
        print("All chunks already downloaded.")
    else:
        print(f"To download: {len(remaining)} chunks ({len(completed_set)} already done).")

    for round_idx in range(4):
        if not remaining:
            break

        if round_idx > 0:
            print(f"\nRetry round {round_idx}/3: {len(remaining)} chunks...")

        batch = remaining[:thread_count]
        n_workers = len(batch)
        thread_stats = [{"downloaded": 0, "chunks_done": 0, "status": ""} for _ in range(n_workers)]
        failed_set = set()
        display_stop = threading.Event()

        display_thread = threading.Thread(
            target=display_loop,
            args=(thread_stats, lock, completed_set, num_chunks, total_size, total_downloaded, display_stop),
            daemon=True,
        )
        display_thread.start()

        workers = []
        for wi, (idx, offset, size) in enumerate(batch):
            t = threading.Thread(
                target=worker,
                args=(url, idx, offset, size, completed_set, failed_set, total_downloaded, wi, thread_stats, lock),
                daemon=True,
            )
            t.start()
            workers.append(t)

        for t in workers:
            t.join()

        display_stop.set()
        time.sleep(0.3)

        remaining = [(idx, offset, size) for idx, offset, size in remaining if idx in failed_set]

    if remaining:
        print(f"\nIncomplete: {len(completed_set)}/{num_chunks} chunks done.")
        print(f"Failed chunks: {[idx for idx, _, _ in remaining]}")
        print("Run again to resume.")
        sys.exit(1)

    print("\nMerging chunks...")
    with open(save_path, "wb") as outfile:
        for idx, offset, size in chunks:
            chunk_path = f"chunk_{idx}.tmp"
            with open(chunk_path, "rb") as infile:
                outfile.write(infile.read())
            os.remove(chunk_path)

    clear_state()
    print(f"Done! File saved as {save_path}")


if __name__ == "__main__":
    main()

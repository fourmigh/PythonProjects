import os
import sys
import threading
import time
import urllib.request
import urllib.error
from collections import deque


def enable_ansi():
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        kernel32.GetConsoleMode(h, ctypes.byref(mode))
        kernel32.SetConsoleMode(h, mode.value | 0x0004)


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def get_file_info(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            with urllib.request.urlopen(req, timeout=60) as resp:
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
                sys.exit(1)


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


def download_chunk(url, start, end, part_index, progress, lock, completed, stop_event):
    part_path = f"part_{part_index}.tmp"
    expected = end - start + 1
    max_retries = 3

    for attempt in range(max_retries):
        try:
            downloaded = 0
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            req.add_header("Range", f"bytes={start}-{end}")
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(part_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        with lock:
                            progress[part_index]["downloaded"] = downloaded
            if downloaded < expected:
                raise IOError(f"expected {expected} bytes, got {downloaded}")
            break
        except Exception as e:
            if stop_event.is_set():
                return
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                with lock:
                    progress[part_index]["error"] = str(e)

    with lock:
        completed[part_index] = True


def display_loop(progress, lock, completed, total_size, stop_event):
    n = len(progress)
    lines_to_redraw = n + 2
    history = [deque(maxlen=15) for _ in range(n)]

    def render():
        now = time.time()
        with lock:
            total_downloaded = 0
            for i in range(n):
                d = progress[i]["downloaded"]
                total_downloaded += d
                history[i].append((now, d))
            pct = total_downloaded / total_size if total_size else 0

        total_speed = 0.0
        speeds = []
        etas = []
        for i in range(n):
            p = progress[i]
            t = p["total"]
            d = p["downloaded"]
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
            remaining = t - d
            eta = remaining / speed if speed > 0 else 0
            etas.append(eta)

        overall_eta = (total_size - total_downloaded) / total_speed if total_speed > 0 else 0

        print(f"\033[{lines_to_redraw}A", end="")
        bar = progress_bar(pct)
        os_str = f"{human_size(total_speed)}/s" if total_speed > 0 else "---"
        oe_str = format_eta(overall_eta) if total_speed > 0 else "---"
        print(f"Overall: {pct * 100:5.1f}% {bar} {human_size(total_downloaded):>10} / {human_size(total_size)}  {os_str:>10}  ETA {oe_str}")
        print()
        for i in range(n):
            p = progress[i]
            t = p["total"]
            d = p["downloaded"]
            tpct = d / t if t else 1
            bar = progress_bar(tpct)
            err = p.get("error", "")
            s_str = f"{human_size(speeds[i])}/s" if speeds[i] > 0 else "---"
            e_str = format_eta(etas[i]) if speeds[i] > 0 else "---"
            line = f"Thread {i + 1:2d}: {bar} {human_size(d):>10} / {human_size(t)}  {s_str:>10}  ETA {e_str}"
            if err:
                line += f"  FAILED: {err}"
            print(f"{line:<90}")
        sys.stdout.flush()

    print()
    for _ in range(n + 1):
        print()
    sys.stdout.flush()

    while not stop_event.is_set():
        render()
        time.sleep(0.2)

    render()


def main():
    enable_ansi()

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

    base = total_size // thread_count
    remainder = total_size % thread_count
    start = 0
    chunks = []
    for i in range(thread_count):
        chunk_size = base + (1 if i < remainder else 0)
        if chunk_size <= 0:
            break
        end = start + chunk_size - 1
        chunks.append((start, end))
        start = end + 1

    actual_threads = len(chunks)

    progress = [{"downloaded": 0, "total": end - start + 1} for start, end in chunks]
    lock = threading.Lock()
    completed = [False] * actual_threads
    stop_event = threading.Event()

    threads = []
    for i, (start, end) in enumerate(chunks):
        t = threading.Thread(
            target=download_chunk,
            args=(url, start, end, i, progress, lock, completed, stop_event),
            daemon=True,
        )
        t.start()
        threads.append(t)

    display_thread = threading.Thread(
        target=display_loop,
        args=(progress, lock, completed, total_size, stop_event),
        daemon=True,
    )
    display_thread.start()

    for t in threads:
        t.join()

    stop_event.set()
    time.sleep(0.3)

    with lock:
        any_error = any("error" in p for p in progress)

    if any_error:
        print("\nSome threads failed.")
        resp = input("Continue with merge? (y/N): ").strip().lower()
        if resp != "y":
            print("Aborted.")
            for i in range(actual_threads):
                part_path = f"part_{i}.tmp"
                if os.path.exists(part_path):
                    os.remove(part_path)
            sys.exit(1)

    print("\nMerging parts...")
    with open(save_path, "wb") as outfile:
        for i in range(actual_threads):
            part_path = f"part_{i}.tmp"
            with open(part_path, "rb") as infile:
                outfile.write(infile.read())
            os.remove(part_path)

    print(f"Done! File saved as {save_path}")


if __name__ == "__main__":
    main()

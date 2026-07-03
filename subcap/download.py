import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(SCRIPT_DIR, "videos")


def check_and_install_ytdlp():
    try:
        __import__("yt_dlp")
    except ImportError:
        print("[INFO] Installing yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])


check_and_install_ytdlp()

import yt_dlp


def progress_hook(d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if total:
            pct = d["downloaded_bytes"] / total * 100
            speed = d.get("speed") or 0
            speed_str = "{:.1f} MB/s".format(speed / 1024 / 1024) if speed else ""
            print("\r[DOWNLOAD] {:.1f}%  {}".format(pct, speed_str), end="")
    elif d["status"] == "finished":
        print("\n[DOWNLOAD] Complete, processing...")
    elif d["status"] == "error":
        print("\n[ERROR] Download failed")


def download_video(url, output_dir=VIDEO_DIR):
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title).100s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            merged = filename.rsplit(".", 1)[0] + ".mp4"
            if os.path.exists(merged):
                filename = merged

        title = info.get("title", "Unknown")
        print("[OK] {}".format(os.path.basename(filename)))
        return filename


def main():
    if len(sys.argv) < 2:
        print("Usage: python download.py <URL1> [URL2] [URL3] ...")
        print("Example: python download.py https://www.iqiyi.com/v_17tyl4c4er4.html")
        sys.exit(1)

    urls = sys.argv[1:]
    print("Downloading {} video(s) to {}/\n".format(len(urls), VIDEO_DIR))

    success = 0
    for i, url in enumerate(urls, 1):
        print("[{:d}/{:d}] {}".format(i, len(urls), url))
        try:
            download_video(url)
            success += 1
        except Exception as e:
            print("[FAIL] {}".format(e))
        print()

    print("Done: {}/{} succeeded".format(success, len(urls)))
    print("Output directory: {}".format(VIDEO_DIR))


if __name__ == "__main__":
    main()

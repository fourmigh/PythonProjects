import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
BACKUP_DIR = 'backup'


class ImageBatchProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("批量图片处理工具")
        self.root.geometry("620x500")
        self.root.minsize(560, 420)

        self.folder_path = tk.StringVar()
        self.do_rotate = tk.BooleanVar(value=True)
        self.do_resize = tk.BooleanVar(value=True)
        self.do_blur = tk.BooleanVar(value=False)
        self.rotate_dir = tk.StringVar(value="顺时针")
        self.rotate_angle = tk.IntVar(value=90)
        self.max_size = tk.IntVar(value=512)
        self.blur_size = tk.IntVar(value=15)

        self._build_ui()
        self._toggle_blur()
        self._update_stats()

    def _build_ui(self):
        root = self.root

        # ── 文件夹选择 ──
        frame_folder = ttk.Frame(root)
        frame_folder.pack(fill=tk.X, padx=12, pady=(12, 4))

        self.btn_folder = ttk.Button(frame_folder, text="选择文件夹", command=self._select_folder)
        self.btn_folder.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_folder_path = ttk.Label(frame_folder, text="未选择", foreground="gray")
        self.lbl_folder_path.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_count = ttk.Label(frame_folder, foreground="gray")
        self.lbl_count.pack(side=tk.RIGHT)

        ttk.Separator(root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=6)

        # ── 旋转选项 ──
        frame_rotate = ttk.Frame(root)
        frame_rotate.pack(fill=tk.X, padx=12, pady=4)

        self.chk_rotate = ttk.Checkbutton(frame_rotate, text="旋转", variable=self.do_rotate,
                                          command=self._toggle_rotate)
        self.chk_rotate.pack(side=tk.LEFT)

        self.lbl_rotate_dir = ttk.Label(frame_rotate, text="方向:")
        self.lbl_rotate_dir.pack(side=tk.LEFT, padx=(16, 4))

        self.combo_dir = ttk.Combobox(frame_rotate, textvariable=self.rotate_dir,
                                      values=["顺时针", "逆时针"], state="readonly", width=6)
        self.combo_dir.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_angle = ttk.Label(frame_rotate, text="角度:")
        self.lbl_angle.pack(side=tk.LEFT, padx=(0, 4))

        self.spin_angle = ttk.Spinbox(frame_rotate, from_=1, to=360, textvariable=self.rotate_angle,
                                      width=5)
        self.spin_angle.pack(side=tk.LEFT)

        self.lbl_deg = ttk.Label(frame_rotate, text="°")
        self.lbl_deg.pack(side=tk.LEFT)

        ttk.Separator(root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=6)

        # ── 模糊车牌选项 ──
        frame_blur = ttk.Frame(root)
        frame_blur.pack(fill=tk.X, padx=12, pady=4)

        self.chk_blur = ttk.Checkbutton(frame_blur, text="检测并模糊车牌", variable=self.do_blur,
                                        command=self._toggle_blur)
        self.chk_blur.pack(side=tk.LEFT)

        self.lbl_blur_size = ttk.Label(frame_blur, text="模糊强度:")
        self.lbl_blur_size.pack(side=tk.LEFT, padx=(16, 4))

        self.spin_blur = ttk.Spinbox(frame_blur, from_=3, to=51, increment=2,
                                     textvariable=self.blur_size, width=5)
        self.spin_blur.pack(side=tk.LEFT)

        self.lbl_blur_note = ttk.Label(frame_blur, text="(高斯模糊核大小, 奇数)")
        self.lbl_blur_note.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Separator(root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=6)

        # ── 缩放选项 ──
        frame_resize = ttk.Frame(root)
        frame_resize.pack(fill=tk.X, padx=12, pady=4)

        self.chk_resize = ttk.Checkbutton(frame_resize, text="等比例缩放", variable=self.do_resize,
                                          command=self._toggle_resize)
        self.chk_resize.pack(side=tk.LEFT)

        self.lbl_max = ttk.Label(frame_resize, text="最大宽/高:")
        self.lbl_max.pack(side=tk.LEFT, padx=(16, 4))

        self.spin_max = ttk.Spinbox(frame_resize, from_=16, to=4096, textvariable=self.max_size,
                                    width=5)
        self.spin_max.pack(side=tk.LEFT)

        self.lbl_px = ttk.Label(frame_resize, text="px")
        self.lbl_px.pack(side=tk.LEFT)

        ttk.Separator(root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=8)

        # ── 执行按钮 ──
        self.btn_start = ttk.Button(root, text="▶ 开始处理", command=self._start_processing)
        self.btn_start.pack(pady=(0, 8))

        # ── 日志区域 ──
        lbl_log = ttk.Label(root, text="处理日志:", font=("", 9, "bold"))
        lbl_log.pack(anchor=tk.W, padx=12)

        log_frame = ttk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(2, 12))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.txt_log = tk.Text(log_frame, height=10, wrap=tk.WORD, font=("Consolas", 9),
                               state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=scrollbar.set)
        self.txt_log.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.txt_log.tag_config("ok", foreground="green")
        self.txt_log.tag_config("err", foreground="red")
        self.txt_log.tag_config("info", foreground="blue")
        self.txt_log.tag_config("bold", font=("Consolas", 9, "bold"))

    def _toggle_rotate(self):
        state = tk.NORMAL if self.do_rotate.get() else tk.DISABLED
        self.combo_dir.config(state=state)
        self.spin_angle.config(state=state)

    def _toggle_resize(self):
        state = tk.NORMAL if self.do_resize.get() else tk.DISABLED
        self.spin_max.config(state=state)

    def _toggle_blur(self):
        state = tk.NORMAL if self.do_blur.get() else tk.DISABLED
        self.spin_blur.config(state=state)

    _reader = None

    @staticmethod
    def _get_reader():
        if ImageBatchProcessor._reader is None:
            ImageBatchProcessor._reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
        return ImageBatchProcessor._reader

    @staticmethod
    def _blur_license_plates(pil_img, kernel_size=15):
        reader = ImageBatchProcessor._get_reader()
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        results = reader.readtext(cv_img)
        ks = kernel_size if kernel_size % 2 == 1 else kernel_size + 1

        for bbox, text, conf in results:
            if conf < 0.3:
                continue
            pts = np.array(bbox, dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            pad = 3
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = min(cv_img.shape[1] - x, w + pad * 2)
            h = min(cv_img.shape[0] - y, h + pad * 2)
            roi = cv_img[y:y + h, x:x + w]
            roi = cv2.GaussianBlur(roi, (ks, ks), 30)
            cv_img[y:y + h, x:x + w] = roi

        return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

    def _select_folder(self):
        folder = filedialog.askdirectory(title="选择要处理的图片文件夹")
        if not folder:
            return
        self.folder_path.set(folder)
        self.lbl_folder_path.config(text=folder, foreground="black")
        self._update_stats()

    def _update_stats(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            self.lbl_count.config(text="")
            return
        count = sum(1 for f in Path(folder).iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS)
        self.lbl_count.config(text=f"共 {count} 张图片")

    def _log(self, msg, tag=None):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, msg + "\n", tag)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def _get_image_files(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            return []
        files = []
        for f in Path(folder).iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
                files.append(f)
        return sorted(files)

    def _backup_images(self, files):
        folder = self.folder_path.get()
        backup_path = Path(folder) / BACKUP_DIR
        backup_path.mkdir(exist_ok=True)
        for f in files:
            shutil.copy2(str(f), str(backup_path / f.name))
        self._log(f"已备份 {len(files)} 张图片到 {BACKUP_DIR}/", "info")

    def _process(self):
        folder = self.folder_path.get()
        files = self._get_image_files()
        if not files:
            self.root.after(0, lambda: messagebox.showwarning("提示", "文件夹中没有支持的图片文件"))
            self._finish()
            return

        rotate = self.do_rotate.get()
        blur = self.do_blur.get()
        resize = self.do_resize.get()
        if not rotate and not blur and not resize:
            self.root.after(0, lambda: messagebox.showwarning("提示", "请至少勾选一个处理功能"))
            self._finish()
            return

        angle = self.rotate_angle.get()
        clockwise = self.rotate_dir.get() == "顺时针"
        final_angle = angle if clockwise else -angle
        blur_ks = self.blur_size.get()
        max_sz = self.max_size.get()
        backup = rotate or blur or resize

        self._log("=" * 50, "bold")
        parts = []
        if rotate:
            dir_text = "顺时针" if clockwise else "逆时针"
            parts.append(f"旋转 {dir_text} {angle}°")
        if blur:
            parts.append(f"模糊车牌 (核大小 {blur_ks})")
        if resize:
            parts.append(f"等比例缩放 ≤ {max_sz}px")
        self._log("操作: " + " → ".join(parts), "bold")
        self._log(f"共 {len(files)} 张图片", "bold")

        if backup:
            self._log("正在备份原图...")
            self._backup_images(files)

        success = 0
        errors = 0

        for i, img_path in enumerate(files, 1):
            try:
                self._log(f"[{i}/{len(files)}] 处理中: {img_path.name}")
                img = Image.open(img_path)
                img = img.convert("RGB")

                if rotate:
                    img = img.rotate(final_angle, expand=True, resample=Image.BICUBIC)

                if blur:
                    img = self._blur_license_plates(img, blur_ks)

                if resize:
                    img.thumbnail((max_sz, max_sz), Image.LANCZOS)

                img.save(img_path, quality=95, optimize=True)
                success += 1
            except Exception as e:
                self._log(f"  ✗ 错误: {e}", "err")
                errors += 1

        self._log("=" * 50, "bold")
        self._log(f"处理完成!  成功: {success}  失败: {errors}",
                   "ok" if errors == 0 else "bold")
        if backup:
            self._log(f"原图已备份至: {Path(folder) / BACKUP_DIR / ''}", "info")
        self._finish()

    def _finish(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_folder.config(state=tk.NORMAL)

    def _start_processing(self):
        if not self.folder_path.get() or not os.path.isdir(self.folder_path.get()):
            messagebox.showwarning("提示", "请先选择一个文件夹")
            return

        if self.do_blur.get() and not HAS_EASYOCR:
            messagebox.showwarning("缺少依赖", "模糊车牌功能需要 easyocr，请运行:\n\npip install easyocr")
            return

        self.btn_start.config(state=tk.DISABLED)
        self.btn_folder.config(state=tk.DISABLED)
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.config(state=tk.DISABLED)

        self._log("开始处理...", "info")
        t = threading.Thread(target=self._process, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    ImageBatchProcessor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""PyInstaller runtime hook：修复 onefile 环境下 onnxruntime/cv2 原生 DLL 加载。

打包时通过 --runtime-hook 注入；在应用代码导入 onnxruntime 前：
1. 把 onnxruntime\capi 和 cv2 目录加入 DLL 搜索路径
2. 用绝对路径先加载 capi 里的 onnxruntime_providers_shared.dll 和 onnxruntime.dll
   （本机 System32 存在旧版 1.0 onnxruntime.dll，若不加前置加载，
    pyd 按名字加载时可能撞上系统旧版 -> DLL 初始化例程失败）
"""

import ctypes
import os
import sys

if getattr(sys, "frozen", False):
    try:
        meipass = sys._MEIPASS
    except AttributeError:
        meipass = None
    if meipass:
        try:
            for sub in ("onnxruntime\\capi", "cv2", "cv2\\data"):
                p = os.path.join(meipass, sub)
                if os.path.isdir(p):
                    try:
                        os.add_dll_directory(p)
                    except Exception:
                        pass
            capi = os.path.join(meipass, "onnxruntime", "capi")
            for name in ("onnxruntime_providers_shared.dll", "onnxruntime.dll"):
                dll = os.path.join(capi, name)
                if os.path.isfile(dll):
                    try:
                        ctypes.WinDLL(dll)
                    except Exception:
                        pass
        except Exception:
            pass
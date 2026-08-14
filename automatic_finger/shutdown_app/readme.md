# 电源助手（睡眠 / 关机 / 重启）

基于 **"视觉识别（OCR）给坐标 → 人形鼠标点击"** 的 Windows 电源控制工具，可执行睡眠、关机、重启三种操作。

- 全鼠标流程，**无键盘依赖**（本机环境下键盘注入被系统拦截）。
- 不含大语言模型/视觉大模型；仅使用 rapidocr 轻量 OCR（约 13 MB 模型）识别屏幕上"睡眠 / 关机 / 重启"文字并提供点击坐标。
- 单文件 exe 分发，目标机无需安装 Python 或任何依赖。

---

## 目录结构

```
automatic_finger/
├── ai_core/                  # 可复用的视觉识别代码（与具体应用解耦）
│   ├── capture.py            #   屏幕抓取：PIL.ImageGrab(GDI) 为主，dxcam(DDA) 回退
│   ├── ocr.py                #   OcrEngine：rapidocr 封装，返回文字框 + 中心坐标
│   └── __init__.py
└── shutdown_app/             # 电源助手应用（自带独立构建脚本）
    ├── engine.py             #   电源引擎（锚点 + OCR + 人形鼠标 + 提权）
    ├── gui.py                #   界面入口（打包目标，主程序）
    ├── rthook_onnx.py        #   PyInstaller runtime hook：修复 onnxruntime DLL 加载
    ├── shutdown_app.bat      #   一键打包脚本
    ├── __init__.py
    └── dist/
        └── 电源助手.exe      #   构建产物（单文件，约 98 MB）
```

---

## 工作原理

完整流程（全鼠标，无键盘）：

1. **任务栏几何计算锚点**：通过 `SHAppBarMessage` 取任务栏矩形，自动推导"开始按钮"与"电源按钮"的屏幕坐标（支持 Win10/Win11、上下左右停靠、居中/靠左布局，非用户配置）。
2. **点开始按钮**：人形鼠标移动到锚点并点击，打开开始菜单。
3. **点电源按钮**：人形鼠标点击电源锚点，弹出"睡眠 / 关机 / 重启"悬浮框。
4. **OCR 定位目标**：rapidocr 在弹框区域识别三个菜单项，定位所选目标（**睡眠 / 关机 / 重启**）的行中心：
   - 关机（中间项）：用**睡眠行与重启行的中点**（比单条文字 OCR 中心更抗抖动）；
   - 睡眠 / 重启（首/末项）：用自身 OCR 中心。
5. **人形鼠标移动 + 点击**：沿贝塞尔曲线移动到位，点击。
6. **点击后校验 + 安全重试**：点击后等待 2 秒，重新 OCR 弹框区域：
   - 弹框已关闭 → 点击生效，已触发目标操作，流程成功；
   - 弹框仍在 → 视为未点中，在目标行内做 y 偏移 `[0, +8, -8, +16, -16]` 重试（**约束在目标行内，不会误点其它行**）；
   - 5 次仍失败 → 保存一张 `失败截图.png` 到 exe 旁并安全中止（绝不点其它入口）。

每一步都有 OCR 校验与重试兜底，找不到目标一律安全中止，**绝不盲点**。

---

## 关键技术点

### 视觉坐标来源：rapidocr（而非大模型）
最初尝试用 qwen2.5vl 视觉大模型输出图标坐标，但实测其 grounding 不可靠（合成图测试偏移 30~200px 甚至越界），已移除。改用 rapidocr（PaddleOCR 系，`ch_PP-OCRv3` 检测/识别 + 方向分类三个 `.onnx`，共约 13 MB），对屏幕上的中文菜单文字定位稳定。

### 全鼠标方案（无键盘）
目标环境键盘注入被拦截：`SendInput`/`keybd_event` 发送 Win 键等均无效（返回 0 / 无效果），而鼠标注入（pyautogui / SendInput）完全正常。因此流程设计为纯鼠标：点开始 → 点电源 → OCR 定位 → 点击所选目标。

### 屏幕抓取：PIL 为主，dxcam 回退
- **PIL.ImageGrab（GDI BitBlt）为主**：无 DDA（Desktop Duplication API）依赖，稳定可靠，支持 `bbox` 直接裁剪 ROI。
- **dxcam（DDA）为回退**：仅在 PIL 失败时使用。
- 原因：dxcam 的 DDA 在冻结 exe / 混合显卡（Intel 核显 + NVIDIA 独显 + 虚拟屏）/ 某些会话下抛 `DXGI_ERROR_UNSUPPORTED (0x887A0004)`，而在开发环境却正常，属于脆弱路径；本项目只需低频截图做 OCR，GDI 足够。

### 人形鼠标（拟人操作）
`engine.py` 的 `human_move`/`human_click` 用 `DEFAULT_PARAMS` 模拟真人手持鼠标的特征：

- **曲线路径**：贝塞尔曲线 + 随机侧弯（`curve_bend`），真人不会走完美直线；
- **速度不均**：按距离定时长 + 随机抖动（`speed_jitter`），缓起缓停（easing），中途最快，符合手部肌肉运动规律；
- **随机等待与抖动**：到位后随机停顿 `0.08~0.22s`，点击目标加 `±2px` 抖动；
- **距离自适应**：远则快、近则慢，时长钳制在 `0.35~1.5s`。

（命名来源：最初面向"需要规避检测的自动化"场景，拟人曲线+抖动+随机延迟使其不易被识别为机器操作；本项目亦使电源操作流程看起来像人手点击。）

### 提权与坐标一致性
- 程序通过 UAC 自动提权（`ensure_elevated`），用 `ShellExecuteW("runas")` 重启自身。
- 设置 `SetProcessDpiAwareness(2)`（Per-Monitor DPI Aware），确保任务栏锚点、PIL 抓屏坐标、鼠标点击坐标全部处于**物理像素**同一坐标系，避免 DPI 缩放错位。

### 打包三大坑与修复（均已固化到 `shutdown_app.bat`）
1. **onnxruntime DLL 初始化失败**：本机 `System32\onnxruntime.dll` 存在旧版 1.0（2019），冻结进程按名加载时可能撞上 → `DLL 初始化例程失败`。修复：`rthook_onnx.py` 在导入前用绝对路径预加载 `_MEIPASS\onnxruntime\capi\onnxruntime.dll` 与 `onnxruntime_providers_shared.dll`，并 `os.add_dll_directory` 加入 capi/cv2 目录。
2. **msvcp140.dll 版本冲突**：PyInstaller 从 JDK 目录收集了旧版 `msvcp140.dll`（14.16，2018），进程启动即绑定 → onnxruntime 1.27 所需的新导出缺失，初始化失败。修复：`--add-binary "%WINDIR%\System32\msvcp140.dll;."` 用系统新版（14.5x）覆盖打入包内。
3. **dxcam DXGI_ERROR_UNSUPPORTED**：冻结 exe 内 DDA 不可用（见上文），抓屏改用 PIL 解决。

---

## 环境与分发

| 项 | 说明 |
| --- | --- |
| 目标机 | **64 位 Windows 10 / 11**（ARM 设备不支持） |
| 依赖 | 无需安装 Python / 任何包，单文件自包含 |
| 体积 | 约 98 MB（Python 运行时 + onnxruntime + OCR 模型 + PIL/dxcam/pyautogui） |
| 注意事项 | 首次启动需解压到临时目录并加载 OCR，多等几秒属正常；未签名 exe 可能触发 SmartScreen / 杀软提示（点"更多信息 → 仍要运行"）；任务栏样式/分辨率差异大的机器建议先点"干跑测试"验证定位 |

---

## 构建方法

在 `shutdown_app` 目录运行 `shutdown_app.bat`（或直接执行）：

```bat
pyinstaller --noconfirm --onefile --windowed --name "电源助手" ^
  --paths "%~dp0.." ^
  --collect-all rapidocr_onnxruntime ^
  --collect-all dxcam ^
  --exclude-module torch ^
  --exclude-module tensorflow ^
  --runtime-hook "%~dp0rthook_onnx.py" ^
  --add-binary "%WINDIR%\System32\msvcp140.dll;." ^
  gui.py
```

构建环境：Windows 10 x64，Python 3.14，PyInstaller 6.21（+ hooks-contrib 2026.6）。
依赖：`pyinstaller`、`rapidocr_onnxruntime`、`dxcam`、`pillow`、`pyautogui`。

> `--exclude-module torch --exclude-module tensorflow` 用于避免无关大库混入（构建时间从约 7 分钟降到约 1 分钟）。

---

## 使用说明

1. 双击 `电源助手.exe`，UAC 弹窗点"是"（程序需要管理员权限才能点击开始菜单/电源菜单）。
2. 选择**目标操作**：睡眠 / 关机 / 重启（单选，默认关机）。
3. 界面操作：
   - **干跑测试**：完整执行"点开始 → 点电源 → OCR 定位 → 移动鼠标到目标行"，但**不点击**，用于安全验证；
   - **开始执行**：正式执行，移动到目标行并点击，触发所选操作（睡眠/关机/重启）；
   - 点击后进入 5 秒倒计时。
4. **急停**：把鼠标甩到屏幕左上角（`pyautogui.FAILSAFE`），立即中止。

### 自动化验证
```bat
电源助手.exe --auto-dry --target 关机
```
启动后自动执行一次干跑（`--target` 可指定 睡眠/关机/重启），用于无人值守验证。

### 运行产物（写在 exe 同目录）
- `电源助手.log`：运行日志；
- 干跑/点击失败时：`失败截图.png`，便于排查当时屏幕状态。

---

## 已知限制

- **锚点是任务栏几何启发式**：开始/电源按钮坐标由任务栏矩形推导，Win11 或特殊任务栏样式可能偏移；靠"OCR 校验 + 重试"兜底，最坏情况安全中止而非误点。
- **DDA 脆弱**：混合显卡 / 远程会话等场景下 dxcam 不可用（已用 PIL GDI 兜底）。
- **仅支持 x64**：bootloader 为 64 位。
- **未签名**：可能触发 SmartScreen / 杀软误报。
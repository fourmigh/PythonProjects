# PythonProjects —— 个人多项目实验仓库

本仓库是**多个独立小工程的集合**：每个顶层文件夹即一个独立项目，互不依赖，各自有各自的依赖与打包方式。本 README 汇总各项目的用途、技术栈、运行方式与当前状态，方便后续继续开发。

## 总览

| 分类 | 项目 | 一句话简介 | 状态 |
|---|---|---|---|
| 桌面工具 | `disk_cleaner` | 单文件 Tkinter 磁盘清理工具（卸载/临时文件/大文件/重复文件/空目录/残留） | ✅ 完整已打包 |
| 桌面工具 | `ps` | PySide6 AI 桌面 P 图工具（豆包风，云端改图 + 局部编辑 + 抠图） | ✅ 完整有测试 |
| 桌面工具 | `translate` | GUI 翻译对照工具（在线/离线双引擎，词级对齐） | ✅ 完整已打包 |
| 桌面工具 | `close360ad` | 自动关闭 360 广告弹窗的托盘常驻工具 | ✅ 完整已打包 |
| 桌面工具 | `automatic_finger` | 「电源助手」：OCR + 拟人鼠标实现 Windows 关机/睡眠 | ✅ 完整已打包 |
| 桌面工具 | `stopsleep` | Windows 防睡眠小脚本（鼠标微移 + API 双保险） | ⚠️ 草稿级 |
| 桌面工具 | `img2text` | 图片转字符画生成器 | ⚠️ WSL 路径硬编码，Windows 原生跑不了 |
| 桌面工具 | `mxd` | MXD/DKL（Dallas Key）文件解析与生成工具，带 GUI | ✅ 完整有测试 |
| 仿真 | `taxi_sim` | 出租车巡游揽客策略仿真平台（真实地图 + 8 种策略 + SQLite） | ✅ 最活跃项目 |
| 仿真 | `simelevator` | 多电梯调度策略对比仿真（7 种策略 + PySide6 GUI） | ✅ 缺 README |
| 仿真 | `parking_system` | 自行车停车库时段预订 + 智能车位分配模拟 | ✅ 完整 |
| AI 应用 | `ai/Lemo-Opuscar` | AI 影片生成器启动器（环境管理 + OpenCode CLI 驱动） | ✅ 完整 |
| AI 应用 | `aibattle` | AI 对弈平台：随机/启发式/LLM 棋类对战（五子棋） | ✅ 完整 |
| AI 应用 | `ps`（同上） | — | — |
| AI 应用 | `drama` | 多智能体喜剧脚本创作（DeepSeek API） | ✅ 需填 API Key |
| AI 应用 | `find_bike` | 多模态大模型自行车牌照检测 + 提示词优化闭环 | ✅ 最成熟 |
| AI 应用 | `yolo` | YOLO 检测学习/实验脚本 | ✅ 简单实验 |
| AI 应用 | `ollama` | Ollama 服务命令行管理面板 | ✅ 松散脚本集 |
| AI 应用 | `llama` | llama.cpp 全家桶管理器（编译/模型/对话/API 服务） | ✅ 完整 |
| 爬虫/OCR | `movie_info_crawler` | 豆瓣 + 猫眼电影信息爬取与 HTML 报告 | ✅ 完整 |
| 爬虫/OCR | `subcap` | 视频中文字幕提取工具（OCR + 广告过滤 + Excel 报表） | ✅ 已跑通 |
| SDK 学习 | `opencode_sdk_demo` | OpenCode Python SDK 教学示例集（22 个 Demo + PySide6 桌面版） | ✅ README 过时 |
| 脚本 | `free_port` | 端口占用查找与释放（跨平台） | ✅ 完整 |
| 脚本 | `git` | Git 空分支清理工具 | ✅ 完整 |
| 脚本 | `copy_folders` | WSL 目录拷贝 + 多线程断点续传下载器 | ✅ 路径硬编码 |
| 脚本 | `tariff` | 意大利停车费最优购票计算器（DFS） | ✅ 完整 |
| 脚本 | `all_media` | 全媒体运营师试卷 PDF 生成器（WeasyPrint） | ✅ 一次性工具 |
| 其他 | `deepseek_tui` | 仅 deepseek-tui 的 WSL cargo 安装脚本，无项目源码 | ⚠️ 非独立工程 |
| 其他 | `usbai` | 空目录（占位） | ⚠️ 空 |

> 本仓库根 `.gitignore` 排除：`__pycache__/`、`build/`、`dist/`、`.deepseek/`、`.codebuddy/`，以及 `taxi_sim/config.ini`（含地图 API Key）与 `taxi_sim/taxi_sim.db`。

---

## 桌面工具

### disk_cleaner — 磁盘清理工具
- **入口**：`python disk_cleaner/disk_cleaner.py`（支持 `--selftest` GUI 自检）
- **打包**：`build_exe.bat`（PyInstaller onefile+windowed）→ `dist/DiskCleaner.exe`
- **依赖**：纯标准库（tkinter、winreg、ctypes），零第三方运行时依赖
- **要点**：单文件 ~2000 行，6 个标签页（软件卸载 / 临时文件 / 大文件 / 重复文件 / 空目录 / 软件残留）；删除一律走 SHFileOperationW 进回收站；重复文件三级去重（大小→部分哈希→sha256）；残留删除前先 `reg export` 备份
- **状态**：完整且已被实际使用

### ps — AI 桌面 P 图工具
- **入口**：`python ps/main.py`；测试 `python -m pytest -q`
- **依赖**：PySide6、Pillow、numpy、opencv-python-headless、requests；可选 rembg + onnxruntime（`ps/requirements.txt`）
- **配置**：`ps/config.json`（模型/费用统计/输出目录）；API Key 仅存内存不落盘；已生成结果在 `ps/outputs/`
- **要点**：云端改图走硅基流动 `Qwen/Qwen-Image-Edit-2509`，智谱做提示词改写；支持画笔/矩形局部编辑、rembg 抠图、OpenCV 消除、批量、多轮修改与历史版本；`psapp/` 按 providers / core / ui 分层

### translate — 翻译对照工具
- **入口**：`python translate/main.py`（合并版，引擎可选）；`main_online.py` / `main_offline.py` 为锁定引擎的独立入口
- **打包**：`build_exe.bat` → 打出 merged / online / offline 三种 exe（splash 启动图 + Win32 单实例）
- **依赖**：deep-translator（在线 Google）、argostranslate（离线）、jieba（分词对齐）、pypdf、python-docx、beautifulsoup4、requests
- **要点**：支持文本/txt/docx/pdf/网页 URL 输入，逐句中英对照输出；`aligner.py` 做词级对齐（悬停高亮）；缺依赖/缺模型有友好报错分支

### close360ad — 360 广告弹窗关闭工具
- **入口**：`python close360ad/main.py`（互斥量单实例；`--list/--listall` 调试列窗口）
- **打包**：`build.bat`（装依赖→生成图标→PyInstaller）+ `Close360Ad.spec` → `dist/Close360Ad.exe`
- **依赖**：pywin32、pystray、Pillow；纯 Win32 原生对话框（非 tkinter）
- **要点**：后台每 2 秒枚举窗口，按 exe 特征 + 标题关键词/类名判定广告窗，多级关闭策略（WM_CLOSE→…→坐标模拟点击→隐藏→可选杀进程）；白/黑名单 JSON 存于 %APPDATA%
- **注意**：代码中大量裸 `except:`，属待改进风格

### automatic_finger — 电源助手
- **入口**：`python automatic_finger/shutdown_app/gui.py`（支持 `--auto-dry --target 关机` 干跑，UAC 自动提权）
- **打包**：`shutdown_app.bat`（onefile+windowed，含 `rthook_onnx.py` onnxruntime 运行时钩子）→ `dist/电源助手.exe`（~98MB）
- **依赖**：pyautogui、rapidocr_onnxruntime、dxcam、Pillow、numpy
- **要点**：全鼠标方案（目标环境键盘注入被拦截）：任务栏几何推算开始/电源按钮锚点 → 贝塞尔拟人鼠标点击 → RapidOCR 定位"睡眠/关机/重启"文字 → OCR 复验重试，5 次失败则存"失败截图.png"安全中止。详见 `shutdown_app/readme.md`

### stopsleep — 防睡眠脚本
- **入口**：`python stopsleep/stopsleep.py`
- **依赖**：纯标准库（仅 Windows）
- **要点**：每 60 秒鼠标右移 1 像素再移回 + `SetThreadExecutionState` 双保险；Ctrl+C 退出恢复电源策略
- **待办**：参数硬编码在 `__main__`，可加 argparse；写法较旧

### img2text — 字符画生成器
- **入口**：`python img2text/img2text.py`（交互式 CLI）
- **依赖**：pillow
- **⚠️ 已知问题**：`list_system_fonts` 硬编码 `F:\mnt\c\Windows\Fonts`（WSL 路径），Windows 原生环境会报错；`get_flattened_data()` 非 Pillow 标准 API（应为 `getdata()`）——当前环境**基本不可直接运行**，需先做平台适配修复
- **版权**：源自 B 站 UP 主教程，转载需保留版权注释

### mxd — MXD/DKL 工具
- **入口**：`python mxd/mxd_gui.py`；测试 `python -m unittest discover -s tests -v`（在 mxd 目录内）
- **打包**：`build.bat` + `MxdTool.spec` → `dist/MxdTool.exe`
- **依赖**：pycryptodome（RSA/XTEA/校验）、tkinter 内置
- **要点**：将 Kotlin 版解析逻辑用 Python 重写；`mxdlib/` 拆分二进制 TLV、CRC32、XTEA、RSA 签名、schema/DKL 模型；回归测试可整文件逐字节重建官方样本。格式文档见 `doc/`（MXD File Format.doc 等）
- **扩展方向**：目前仅实现 DKL，可后续支持 BOC/BOR/STF/ELG/SIN/DIR/TRF

---

## 仿真

### taxi_sim — 出租车巡游策略仿真平台（最活跃）
- **入口**：`python taxi_sim/main.py`（无 Key 时弹设置引导）；离线冒烟测试 `python taxi_sim/smoke_test.py`（不启 GUI、不耗配额）
- **依赖**：PySide6 ≥6.8、requests；SQLite（标准库）
- **配置**：复制 `config.example.ini` → `config.ini` 填高德/腾讯/百度地图 Key（`.gitignore` 已排除）
- **要点**：8 种巡游策略（随机游走/蛇形扫描/热点抢客/网格轮巡/热区驻点/避堵漫游/历史热点/场站驻点）；多平台地图 SDK 按剩余配额自动切换 + "超限自学习真实配额"机制（`mapsdk/quota.py`）；坐标系转换（WGS-84↔GCJ-02↔BD-09）；i18n 中英双语；数据表见 `data/store.py`
- **状态**：2026/11/9 仍在活跃开发

### simelevator — 电梯调度策略对比仿真
- **入口**：`python simelevator/main.py`；测试 `python -m unittest discover tests`
- **依赖**：PySide6（唯一外部依赖）
- **要点**：同一客流喂 7 种空闲停靠策略（Stay/Lobby/Mode/Median/ExpectedCost/Zoned/Adaptive）实时对比等待时间；`data/profiles.json` 提供"人物画像"（住户/访客、轮椅、儿童）驱动的客流生成；离散事件仿真主循环在 `core/simulator.py`
- **待办**：缺 README 和 requirements.txt（功能本身完整、有较全测试）

### parking_system — 停车库时段预订模拟
- **入口**：`python parking_system/ui/parkinggui.py`（需在项目目录内运行）；测试 `python parking_system/test_parking_system.py`
- **依赖**：纯标准库
- **要点**：整数位图做时段冲突检测；`core/allocation.py` 多因子打分的智能车位分配（权重在 `core/config.py`）；docs/ 下有需求与实现两份文档

---

## AI 应用

### ai/Lemo-Opuscar — AI 影片生成器启动器
- **入口**：双击 `ai/Lemo-Opuscar/启动.bat`（或 `py -3 main.py`）；CLI 子命令 `--check` / `--bootstrap` / `--smoke --model xxx`
- **依赖**：Tkinter GUI 纯标准库；运行时依赖由"一键准备"自动安装（OpenCode CLI、ffmpeg、Lemo 仓库 requirements）
- **要点**：检测/自动安装全套环境 → 调 OpenCode CLI agent，按 59 种影片风格 + 主题用代码逐帧渲染短片（Canvas/WebGL + TTS + 采样配乐，不用视频生成模型）；`lemo/` 包按 config / environment / runner / prompt / styles 分层；`repo/` 是上游 Lemo 风格库的克隆（非自研）
- **注意**：`config.json` 已配置本机路径

### aibattle — AI 对弈平台
- **入口**：`python aibattle/main.py [black] [white]`，如 `python main.py random heuristic`；批量 `--headless --games 100 --export results.csv`；GUI 循环赛 `--match 10`
- **依赖**：纯标准库（Tkinter + http.client/urllib 直连 OpenAI/Ollama/Claude）
- **要点**：架构分层清晰——`core/`（棋盘/规则/引擎抽象）、`games/gomoku/`（五子棋实现）、`ai/`（随机/极小极大启发式/LLM）、`gui/`；已有运行产物 `results.json`、`llm_debug.log`
- **扩展方向**：`games/` 预留多棋类扩展，目前只有五子棋

### drama — 喜剧脚本创作
- **入口**：`python drama/comedy/comedy.py`（交互式 CLI，结果存 txt）
- **依赖**：openai SDK（指向 DeepSeek `deepseek-chat`）
- **⚠️ 注意**：`comedy.py` 第 8 行 `API_KEY` 为占位符 `"your-api-key-here"`，需手动填入
- **要点**：单文件实现"喜剧五型"（单口/对口/群口相声、脱口秀、漫才）：编剧 Agent 生成 + 观众 Agent 模拟打分 + 逐段标注笑点强度/密度/命中率

### find_bike — 自行车牌照检测（最成熟）
- **入口**：GUI `python find_bike/gui_app.py`；CLI `python find_bike/main_optimizer.py`（菜单驱动）
- **打包**：`build.bat` → `dist/BikeDetector.exe`
- **依赖**：必装 pillow、requests；按需 zhipuai / openai / boto3 / easyocr 等
- **要点**：多模态大模型（Ollama / 智谱 GLM-4V / OpenAI / AWS Bedrock 四后端，环境变量配 Key）判断自行车是否有牌照；提示词优化闭环——按误报/漏报/位置错自动改写提示词，验证集准确率 ≥95% 才允许保存；`valid_prompts*` 与 `optimization_history/` 为提示词库；三语 GUI；配套预处理工具 `image_batch_processor.py`、`resize.py`、`bw_convert.py`

### yolo — YOLO 实验脚本
- **入口**：`python yolo/bike.py`（模型与图片路径硬编码）
- **依赖**：ultralytics；权重 `yolo26n.pt` / `yolov8n.pt`，测试图 `bike.jpg` / `nobike.jpg`
- **要点**：加载模型打印 Results/Boxes 全部属性的学习脚本；与 `find_bike` 相关；文件头是模型选型速查表

### ollama — Ollama 管理器
- **入口**：`python ollama/ollama_manager.py`（交互菜单）；其余为独立脚本直接运行
- **依赖**：requests、psutil（缺失时自动 pip 装）、ollama SDK（可选）
- **要点**：服务启停、模型拉取、GPU 显存检查（nvidia-smi）、运行中模型检测、对话测试；`fetch_models.py` 从 ollama.com 抓取视觉模型清单生成 `model_list.py`
- **注意**：`model_list.py` 多数条目 size/desc 为空，抓取解析待完善；无统一 requirements.txt

### llama — llama.cpp 管理器
- **入口**：`python llama/main.py`（9 项菜单）；`llama_cpp_manager.py` 是独立的编译安装器（尚未接入主菜单）
- **依赖**：纯标准库；可选 huggingface-hub；编译需 git/cmake
- **要点**：编译安装 llama.cpp（国内镜像）、模型搜索下载（hf-mirror 镜像）、交互对话（llama-cli/llama-server）、OpenAI 兼容 API 服务启停、Ollama API 格式代理
- **注意**：`llama.cpp/` 目录是 vendored 源码（含编译产物 `llama-cli`/`llama-server`），体积大，非本项目代码

---

## 爬虫 / OCR

### movie_info_crawler — 电影信息爬虫
- **入口**：`python movie_info_crawler/setup.py` 装依赖 → `playwright install chromium firefox` → `python movie_info_crawler/main.py`；卸载 `teardown.py`
- **依赖**：Playwright（Stealth）、EasyOCR（~500MB 中文模型）、openpyxl
- **要点**：豆瓣 + 猫眼双平台搜索/提取/合并 → HTML 报告；猫眼加密票房走"截图→EasyOCR→人工确认"链路；电影列表写在 `config.json`
- **状态**：完整，已有 README 且与代码一致

### subcap — 视频字幕提取
- **入口**：`python subcap/subcap.py`（处理 `videos/` 全部视频）；ROI 编辑 `python editor.py videos/01.mp4`；下载 `python download.py <url>`
- **依赖**：opencv-python、rapidocr-onnxruntime、openpyxl、numpy、yt-dlp（缺包自动 pip 装）；YuNet 人脸模型随仓库携带
- **要点**：逐帧扫描字幕 ROI → 双层广告过滤（字幕文本 + 画面水印）→ 相似度去重 → 帧质量评分（清晰度 + 人脸 + 构图 + 亮度）→ 输出截图目录 + 内嵌预览 Excel；`videos/roi_config.json` 保存 ROI 配置
- **注意**：`videos/01.xlsx` 约 210MB（含内嵌截图），`01.mp4` 约 650MB

---

## SDK 学习

### opencode_sdk_demo — OpenCode SDK 示例集
- **入口**：`python opencode_sdk_demo/run_all.py`（CLI 菜单，22 个 Demo）；桌面版 `python desktop/main.py` 或 `dist/OpenCodeDemo.exe`
- **依赖**：opencode-ai（预发布版，需本地 opencode 服务运行于端口 4096）、PySide6（桌面版）
- **要点**：仿 Android ApiDemos 理念，每个 Demo 统一 `run()` 接口；`_shared.py` 为共享注册表与服务连接检查；中文目录按章节分类（基础入门/会话管理/高级用法/文件操作/代码搜索/TUI 交互）
- **⚠️ 待办**：README 已过时（仍写旧的 5 目录/13 Demo，实际 6 目录/22 Demo），建议更新

---

## 独立脚本

### free_port — 端口释放
- **用法**：`python free_port/free_ports.py 3000 4200 8080`
- **依赖**：纯标准库，跨 Windows/Linux/macOS/WSL
- **要点**：Windows 走 netstat+taskkill；Unix 三级回退（lsof → ss → /proc 解析）

### git — 空分支清理
- **用法**：`python git/cleanup_empty_branches.py`（交互式确认，`--dry-run` 预览）；可 PyInstaller 打包（有 spec）
- **依赖**：纯标准库
- **要点**：删除相对基准分支（master/main/develop）已合并的分支，用 `git branch -d` 保安全；能识别 unborn（从未提交）空分支

### copy_folders — 拷贝/下载脚本
- `python copy_folders/copy_from_wsl.py`：交互式把 WSL（Ubuntu-22.04 /root）目录复制到 `F:\Projects`（**路径硬编码**，换环境需改）
- `python copy_folders/multi_thread_downloader.py`：多线程断点续传下载器（curl 按 Range 分块 + `.download_state` 续传 + ANSI 进度 + 自动探测 WSL 代理）
- 依赖：纯标准库

### tariff — 意大利停车费计算器
- **用法**：`python tariff/italy/parking.py`（交互式输入起止时间）
- **依赖**：纯标准库
- **要点**：单文件 405 行，DFS 把 5 种票当"钞票"搜索费用最低组合，输出备选方案；无测试文件

### all_media — 试卷 PDF 生成器
- **用法**：`python all_media/generate_pdf.py`（输出 PDF 到当前目录）
- **依赖**：weasyprint（HTML→PDF，中文字体样式）
- **要点**：题库在 `questions_judge/single/multi.py`，拼装 HTML 后渲染"全媒体运营师三级"试卷；输出为**含答案版**（正确答案标红）；一次性工具

---

## 其他

### deepseek_tui
仅有 `install.py`：WSL 内通过 cargo 安装 Rust 工具 `deepseek-tui` 的脚本（装编译依赖 → rustup → 中科大镜像 → `cargo install deepseek-tui --locked`）。**非独立项目，无源码**。

### usbai
空目录（占位，创建于 2026/5/25）。

---

## 开发约定与公共模式

- **运行环境**：多数项目面向 **Python 3.14 + Windows 10/11 x64**；每个项目独立管理依赖，无共享虚拟环境。
- **打包习惯**：Windows GUI 工具普遍用 PyInstaller（onefile + windowed），配套 `build.bat` / `*.spec`，产物在各自 `dist/`（已被根 .gitignore 排除）。
- **新增项目建议**：
  1. 在根目录新建文件夹，保持现有平铺风格；
  2. 写项目级 README（taxi_sim、simelevator 等有缺）；
  3. 涉及密钥的配置文件加入根 `.gitignore`（参照 taxi_sim 的 config.ini）；
  4. 尽量配 smoke/test 脚本。
- **已知遗留问题**（下次开发可优先处理）：
  - `img2text`：WSL 路径硬编码，Windows 原生无法运行；
  - `drama`：API_KEY 为占位符；
  - `opencode_sdk_demo`：README 目录结构过时；
  - `simelevator`：缺 README 与 requirements.txt；
  - `stopsleep`：参数硬编码，建议加 argparse。

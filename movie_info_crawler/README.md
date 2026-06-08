# MovieInfoCrawler

双平台电影信息汇聚工具。根据电影名称自动搜索、提取信息，合并生成 HTML 报告。

## 功能特性

- **双数据源** — 第一个来源（元数据）、第二个来源（票房/评分人数）
- **stonefont 解码** — 自动截图 → EasyOCR 识别 → 用户确认
- **CAPTCHA 绕过** — Playwright Stealth + 自动检测提示手动解决
- **多平台** — Windows / WSL / Linux
- **批量处理** — 配置文件设置电影列表，全自动批量爬取
- **HTML 报告** — 自动生成可筛选字段的美观报告

## 安装

```bash
# 1. 安装 Python 依赖
python setup.py

# 2. 安装 Playwright 浏览器（Chromium + Firefox）
playwright install chromium firefox
```

首次运行 EasyOCR 时会自动下载 ~500MB 中文识别模型。

## 配置

编辑 `config.json`，设置要爬取的电影名称列表：

```json
{
    "movies": [
        "疯狂的石头",
        "爱情神话",
        "人生大事"
    ]
}
```

## 使用

```bash
python main.py
```

### 处理流程

1. **my 搜索** — 搜索电影，自动选择第一条结果
2. **my 提取** — 提取评分（明文）、票房和评分人数（stonefont 编码）
3. **Stonefont 处理** — headless 截图 → EasyOCR 识别数字 → 用户确认/修改
4. **db 搜索** — 搜索电影（含 5 秒自动选择倒计时）
5. **db 提取** — 提取全部元数据（导演、演员、简介等）
6. **数据合并** — db 数据为主，my 补充票房/评分人数
7. **报告生成** — 生成可交互的 HTML 文件

### 手动输入

OCR 识别失败或结果不正确时，可手动输入：

```
票房 (如 2534w 或 2.61y):    ← w→万, y→亿
评分人数 (如 1469):
```

## 项目结构

```
├── main.py                          # 入口
├── config.json                      # 电影列表配置
├── setup.py                         # 依赖安装脚本
├── crawler/
│   ├── browser_fetcher.py           # Playwright 浏览器管理 + Stealth
│   ├── my_extractor.py              # my 搜索/提取/OCR
│   ├── db_search.py                 # db 搜索
│   ├── info_extractor.py            # db 详情提取
│   ├── html_generator.py            # HTML 报告生成
│   ├── config_manager.py            # 配置管理
│   ├── models.py                    # 数据模型/字段枚举
│   ├── dependency_checker.py        # 依赖检查/安装/卸载
│   └── programs.json                # 可安装的程序清单
```

## 数据来源

| 字段 | 来源 |
|------|------|
| 片名、导演、编剧、主演 | db |
| 类型、地区、语言、片长 | db |
| 又名、上映日期 | db + my |
| 评分 | db + my |
| 评分人数 | db + my |
| 票房 | my（OCR / 手动输入） |
| 剧情简介 | db |

## 常见问题

### 验证码（CAPTCHA）
部分详情页可能触发滑块验证码。脚本会自动检测并切换到可见浏览器，提示手动完成验证码后按回车继续。

### WSL 中截图打不开
确保已安装 ImageMagick：
```bash
sudo apt install imagemagick
```

### EasyOCR 下载慢
默认使用清华 PyPI 镜像。也可以手动下载模型放到 `~/.EasyOCR/model/`。

### 浏览器单实例锁
截图通过 `display -immutable` 打开，每次输入完毕后会自动关闭。如果遇到浏览器单实例报错，用 `pkill firefox` 清理。

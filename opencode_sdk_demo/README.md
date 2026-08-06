# Opencode SDK Python 示例工程

本工程参照 Android ApiDemos 的设计理念，为初学者提供一系列**独立、可运行**的代码示例，演示如何使用 opencode Python SDK 进行二次开发。

## 前置条件

1. 已安装 Python 3.8+
2. 已安装并运行 [opencode](https://opencode.ai)
3. opencode 服务运行在默认端口 `4096`

## 快速开始

```bash
# 1. 安装依赖
pip install --pre opencode-ai

# 2. 确认 opencode 服务已启动
#    在终端运行: opencode

# 3. 运行所有示例
python run_all.py

# 4. 或单独运行某个示例
python -c "from 01_基础入门 import 01_HelloWorld as demo; demo.run()"
```

## 目录说明

```
opencode_sdk_demo/
├── 01_基础入门/       # 创建客户端、获取应用信息
├── 02_会话管理/       # 创建/发送/查看/删除会话
├── 03_搜索功能/       # 文本/文件/符号搜索
├── 04_高级功能/       # 异步客户端、错误处理、流式事件
└── run_all.py         # 一键运行全部 Demo
```

每个 `.py` 文件定义一个 `run()` 函数，可被 `run_all.py` 统一调度，也可独立导入调用。

## 学习路线

| 编号 | 分类 | 内容 | 难度 |
|------|------|------|------|
| 01 | 基础入门 | 创建客户端、检查服务状态 | ⭐ |
| 02 | 基础入门 | 获取应用信息 | ⭐ |
| 03 | 基础入门 | 查看模型和提供商 | ⭐ |
| 04 | 会话管理 | 创建新会话 | ⭐⭐ |
| 05 | 会话管理 | 发送消息 | ⭐⭐ |
| 06 | 会话管理 | 查看消息历史 | ⭐⭐ |
| 07 | 会话管理 | 列出和删除会话 | ⭐⭐ |
| 08 | 搜索功能 | 搜索文本 | ⭐⭐ |
| 09 | 搜索功能 | 搜索文件 | ⭐⭐ |
| 10 | 搜索功能 | 搜索符号 | ⭐⭐ |
| 11 | 高级功能 | 异步客户端 | ⭐⭐⭐ |
| 12 | 高级功能 | 错误处理 | ⭐⭐⭐ |
| 13 | 高级功能 | 流式事件 | ⭐⭐⭐ |

## 链接

- [Opencode 官网](https://opencode.ai)
- [Python SDK 源码](https://github.com/anomalyco/opencode-sdk-python)
- [SDK API 文档](https://github.com/anomalyco/opencode-sdk-python/blob/main/api.md)

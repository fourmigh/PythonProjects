from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .styles import Style
from .util import timestamp

PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")

ASPECT_SIZES = {
    "16:9": "1920x1080",
    "9:16": "1080x1920",
    "1:1": "1080x1080",
}


@dataclass
class FilmRequest:
    style: Style
    topic: str
    duration: int
    aspect: str
    language: str
    voice: bool
    project: str
    model: str

    @property
    def size(self) -> str:
        return ASPECT_SIZES.get(self.aspect, "1920x1080")

    @property
    def project_dir(self) -> Path:
        return Path("films") / self.project


def default_project() -> str:
    return f"film-{timestamp()}"


def normalize_project(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    value = value[:48].strip("-")
    return value or default_project()


def valid_project(name: str) -> bool:
    return bool(PROJECT_RE.fullmatch(name.strip()))


def build_prompt(request: FilmRequest) -> str:
    style = request.style
    voice_text = "启用中文旁白，使用仓库默认的中文语音" if request.voice else "不要旁白，只用音乐和音效"
    language = request.language
    return f"""你正在使用 Lemo-Opuscar 仓库（当前工作目录就是仓库根目录）。请直接制作一支完整短片，不要只给方案。

【任务】
- 风格：{style.zh} / {style.en}
- 风格目录：styles/{style.slug}
- 风格分类：{style.category_zh} / {style.category_en}
- 主题/故事：{request.topic.strip()}
- 时长：约 {request.duration} 秒
- 画幅：{request.aspect}（{request.size}）
- 影片语言：{language}
- 声音：{voice_text}
- 项目目录：films/{request.project}/
- 帧率：24 fps

【工作方式】
1. 先阅读仓库根目录的 AGENTS.md、DIRECTOR.md、TECHNIQUE.md，以及 styles/{style.slug}/STYLE.md，严格遵循其中的风格约束和制作流程。
2. 故事、结构、角色、镜头、节奏、数据呈现都由你根据主题导演；STYLE.md 中的风格不变量必须保留。
3. 不要先给我看分镜，也不要停下来等待确认，直接完成成片。
4. 不要向我提问。所有未决定的事项按你的推荐值处理。
5. 不要修改 core/ 和 styles/；需要的文件复制到项目目录。
6. 依赖已经安装完成，不需要运行 setup.sh deps。若某个风格需要额外 npm 包，安装到项目目录。
7. 完成后做自检，并在最后一行给出成片 mp4 的绝对路径。

【Windows 环境】
- 使用 Git Bash（OPENCODE_GIT_BASH_PATH 已设置）。
- Python 虚拟环境位于仓库 .venv，Windows 布局为 .venv/Scripts/python.exe；同时已提供 .venv/bin/python 兼容入口。
- ffmpeg 已加入 PATH。
- 不要使用 WSL。
- 当前模型不一定是 Claude Opus 5.5；请更严格地对照 STYLE.md 和 DIRECTOR.md 执行，避免自由发挥破坏风格。
"""

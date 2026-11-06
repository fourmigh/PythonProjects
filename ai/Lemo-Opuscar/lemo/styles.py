from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CATEGORIES: list[tuple[str, str]] = [
    ("Edit & Documentary", "剪辑与纪实"),
    ("Evidence Films", "实证影像"),
    ("Hand-drawn & Painting", "手绘与绘画"),
    ("East Asian Traditions", "东方传统"),
    ("Print & Printmaking", "印刷与版画"),
    ("Graphic & Type", "图形与排版"),
    ("Information & Keynote", "信息与发布"),
    ("Cartoon & Anime", "卡通与动画"),
    ("Games", "游戏"),
    ("Cinema & Eras", "电影与时代"),
    ("Materials & 3D", "材质与 3D"),
]


@dataclass(frozen=True)
class Style:
    category_en: str
    category_zh: str
    en: str
    zh: str
    slug: str

    @property
    def label(self) -> str:
        if self.zh == self.en:
            return self.zh
        return f"{self.zh} / {self.en}"

    @property
    def category_label(self) -> str:
        return f"{self.category_zh} / {self.category_en}"


STYLES: list[Style] = [
    Style("Edit & Documentary", "剪辑与纪实", "Caption News", "字幕新闻", "caption-news"),
    Style("Edit & Documentary", "剪辑与纪实", "1920s Newsreel", "1920s 新闻影片", "newsreel"),
    Style("Edit & Documentary", "剪辑与纪实", "Live Countdown Split-screen", "实时倒计时分屏", "countdown"),
    Style("Edit & Documentary", "剪辑与纪实", "Time-lapse Symphony", "延时交响", "city-symphony"),
    Style("Edit & Documentary", "剪辑与纪实", "Visual Investigation", "视觉调查", "visual-investigation"),
    Style("Edit & Documentary", "剪辑与纪实", "Constructivist Montage", "构成主义蒙太奇", "kino-montage"),
    Style("Edit & Documentary", "剪辑与纪实", "Sports Telestrator", "体育战术板", "telestrator"),
    Style("Edit & Documentary", "剪辑与纪实", "Broadcast News Package", "电视新闻包装", "news-package"),
    Style("Evidence Films", "实证影像", "Satellite Briefing", "卫星简报", "satellite-briefing"),
    Style("Evidence Films", "实证影像", "Engineering Briefing Board", "工程简报板", "briefing-board"),
    Style("Evidence Films", "实证影像", "LiDAR Survey", "点云测绘", "lidar-survey"),
    Style("Evidence Films", "实证影像", "Projection on White Model", "白模投影", "white-model"),
    Style("Evidence Films", "实证影像", "Data Physicalization", "数据实物化", "data-physical"),
    Style("Evidence Films", "实证影像", "Exploded Teardown", "产品拆解", "teardown"),
    Style("Evidence Films", "实证影像", "Microscope Story", "显微叙事", "microscope"),
    Style("Evidence Films", "实证影像", "Archive Light Table", "档案灯台", "archive-lighttable"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Crayon Picture Book", "蜡笔儿童绘本", "crayon-book"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Watercolor Brush", "水彩笔刷", "watercolor"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Chinese Ink Wash", "中国水墨", "ink-wash"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Impasto Oil Painting", "油画厚涂", "impasto"),
    Style("Hand-drawn & Painting", "手绘与绘画", "One-line Drawing", "一笔画", "one-line"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Whiteboard Explainer", "白板讲解", "whiteboard"),
    Style("Hand-drawn & Painting", "手绘与绘画", "Urban Sketch · Pen & Wash", "钢笔淡彩", "urban-sketch"),
    Style("East Asian Traditions", "东方传统", "Shadow Puppetry", "皮影戏", "shadow-puppet"),
    Style("East Asian Traditions", "东方传统", "Ukiyo-e", "浮世绘", "ukiyoe"),
    Style("East Asian Traditions", "东方传统", "Red Paper-cut", "红色窗花剪纸", "papercut-red"),
    Style("East Asian Traditions", "东方传统", "Paper-cut Lightbox", "纸雕灯影", "paper-lantern"),
    Style("Print & Printmaking", "印刷与版画", "Risograph Print", "Risograph 孔版印刷", "risograph"),
    Style("Print & Printmaking", "印刷与版画", "Halftone Dossier", "复古半调案卷", "halftone-dossier"),
    Style("Print & Printmaking", "印刷与版画", "Woodcut Print", "木刻版画", "woodcut"),
    Style("Print & Printmaking", "印刷与版画", "Copperplate Engraving", "铜版画", "engraving"),
    Style("Print & Printmaking", "印刷与版画", "Silkscreen Travel Poster", "丝印旅行海报", "silkscreen-poster"),
    Style("Graphic & Type", "图形与排版", "Swiss Motion Graphics", "瑞士动态排版", "swiss-motion"),
    Style("Graphic & Type", "图形与排版", "60s Spy Title Sequence", "60s 间谍片头", "spy-titles"),
    Style("Graphic & Type", "图形与排版", "Art Deco", "装饰艺术", "art-deco"),
    Style("Graphic & Type", "图形与排版", "Blueprint", "蓝图 / 工程制图", "blueprint"),
    Style("Graphic & Type", "图形与排版", "Stained Glass", "彩色玻璃窗", "stained-glass"),
    Style("Graphic & Type", "图形与排版", "Pictogram Motion", "象形运动图形", "pictogram-motion"),
    Style("Graphic & Type", "图形与排版", "ASCII / CRT Terminal", "ASCII / CRT 终端", "ascii-crt"),
    Style("Information & Keynote", "信息与发布", "Data Storytelling", "数据叙事", "dataviz"),
    Style("Information & Keynote", "信息与发布", "Isometric Infographic", "等距信息图", "iso-infographic"),
    Style("Information & Keynote", "信息与发布", "Dark Tech Keynote", "暗色科技发布", "dark-keynote"),
    Style("Information & Keynote", "信息与发布", "Living Screencast", "活体实机录屏", "living-screencast"),
    Style("Information & Keynote", "信息与发布", "Sci-fi Hologram HUD", "科幻全息界面", "hologram-hud"),
    Style("Cartoon & Anime", "卡通与动画", "1930s Rubber Hose Cartoon", "1930s 橡皮管卡通", "rubber-hose"),
    Style("Cartoon & Anime", "卡通与动画", "80s Cel Anime", "80 年代赛璐璐动画", "cel-anime-80s"),
    Style("Cartoon & Anime", "卡通与动画", "Sci-Fi Sitcom Toon", "科幻情景喜剧卡通", "scifi-toon"),
    Style("Cartoon & Anime", "卡通与动画", "Mid-century Cartoon", "50s 扁平卡通", "midcentury-toon"),
    Style("Games", "游戏", "16-bit Pixel RPG", "16-bit 像素 RPG", "pixel-rpg"),
    Style("Games", "游戏", "HD-2D", "HD-2D", "hd-2d"),
    Style("Games", "游戏", "Microgame Frenzy", "微游戏快闪", "microgame"),
    Style("Games", "游戏", "Game Show Flat", "综艺节奏扁平", "game-show"),
    Style("Cinema & Eras", "电影与时代", "1920s Silent Film", "1920s 默片", "silent-film"),
    Style("Cinema & Eras", "电影与时代", "Liminal Found Footage", "后室 / 新怪谈", "backrooms"),
    Style("Materials & 3D", "材质与 3D", "Brick Toy", "积木玩具", "brick-toy"),
    Style("Materials & 3D", "材质与 3D", "Paper Pop-up Book", "纸片立体书", "paper-popup"),
    Style("Materials & 3D", "材质与 3D", "Tilt-Shift Miniature", "移轴微缩", "tilt-shift"),
    Style("Materials & 3D", "材质与 3D", "Low-poly Isometric Island", "低多边形等距", "lowpoly-island"),
    Style("Materials & 3D", "材质与 3D", "Glass Product Render", "玻璃质感产品", "glass-product"),
]

_BY_SLUG = {style.slug: style for style in STYLES}
_BY_LABEL = {style.label: style for style in STYLES}
_BY_NAME = {style.en.lower(): style for style in STYLES}
_BY_NAME.update({style.zh.lower(): style for style in STYLES})


def grouped() -> list[tuple[tuple[str, str], list[Style]]]:
    buckets: dict[tuple[str, str], list[Style]] = {}
    for style in STYLES:
        buckets.setdefault((style.category_en, style.category_zh), []).append(style)
    return [(category, buckets[category]) for category in CATEGORIES if category in buckets]


def find(slug: str) -> Style | None:
    return _BY_SLUG.get(slug)


def find_label(label: str) -> Style | None:
    return _BY_LABEL.get(label)


def find_name(name: str) -> Style | None:
    return _BY_NAME.get(name.strip().lower())


def missing_in_repo(repo: str | Path) -> list[str]:
    style_dir = Path(repo) / "styles"
    return [style.slug for style in STYLES if not (style_dir / style.slug / "STYLE.md").exists()]

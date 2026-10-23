from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image

from .composite import save_image


@dataclass
class Version:
    id: str
    parent: str | None = None
    files: list[str] = field(default_factory=list)
    selected: int = 0
    prompt: str = ""
    rewritten_prompt: str = ""
    model: str = ""
    seed: int | None = None
    steps: int = 0
    cfg: float = 0.0
    mask_file: str | None = None
    cost: float = 0.0
    created: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Version:
        known = {field_name for field_name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in known})


class SessionHistory:
    def __init__(self, root: str | Path, original: Image.Image) -> None:
        root = Path(root)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        session_dir = root / stamp
        counter = 1
        while session_dir.exists():
            counter += 1
            session_dir = root / f"{stamp}-{counter}"
        session_dir.mkdir(parents=True, exist_ok=True)

        self.root = root
        self.session_dir = session_dir
        self.original_file = session_dir / "original.png"
        save_image(original.convert("RGB"), self.original_file)
        self.versions: list[Version] = []
        self.current_id: str | None = None
        self.created = datetime.now().isoformat(timespec="seconds")
        self.save()

    @property
    def index_file(self) -> Path:
        return self.session_dir / "history.json"

    @property
    def total_cost(self) -> float:
        return sum(version.cost for version in self.versions)

    @property
    def current(self) -> Version | None:
        if not self.current_id:
            return self.versions[-1] if self.versions else None
        for version in self.versions:
            if version.id == self.current_id:
                return version
        return None

    def add_version(
        self,
        images: list[Image.Image],
        prompt: str,
        rewritten_prompt: str = "",
        model: str = "",
        seed: int | None = None,
        steps: int = 0,
        cfg: float = 0.0,
        mask: Image.Image | None = None,
        cost: float = 0.0,
        parent: str | None = None,
    ) -> Version:
        version_id = f"v{len(self.versions) + 1:03d}"
        files: list[str] = []
        for index, image in enumerate(images, start=1):
            filename = f"{version_id}_{index}.png"
            save_image(image.convert("RGB"), self.session_dir / filename)
            files.append(filename)

        mask_file = None
        if mask is not None:
            mask_file = f"{version_id}_mask.png"
            mask.convert("L").save(self.session_dir / mask_file)

        version = Version(
            id=version_id,
            parent=parent or self.current_id,
            files=files,
            selected=0,
            prompt=prompt,
            rewritten_prompt=rewritten_prompt,
            model=model,
            seed=seed,
            steps=steps,
            cfg=cfg,
            mask_file=mask_file,
            cost=cost,
            created=datetime.now().isoformat(timespec="seconds"),
        )
        self.versions.append(version)
        self.current_id = version_id
        self.save()
        return version

    def select(self, version_id: str, index: int = 0) -> Version:
        version = self.get(version_id)
        if version is None:
            raise KeyError(version_id)
        version.selected = max(0, min(index, len(version.files) - 1))
        self.current_id = version_id
        self.save()
        return version

    def get(self, version_id: str) -> Version | None:
        for version in self.versions:
            if version.id == version_id:
                return version
        return None

    def image_path(self, version: Version, index: int | None = None) -> Path:
        if not version.files:
            raise ValueError("版本中没有图片")
        index = version.selected if index is None else index
        index = max(0, min(index, len(version.files) - 1))
        return self.session_dir / version.files[index]

    def current_image(self) -> Image.Image:
        version = self.current
        if version is None:
            image = Image.open(self.original_file)
            image.load()
            return image
        return Image.open(self.image_path(version))

    def save(self) -> None:
        payload = {
            "session": self.session_dir.name,
            "created": self.created,
            "original": self.original_file.name,
            "current": self.current_id,
            "versions": [version.to_dict() for version in self.versions],
        }
        self.index_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

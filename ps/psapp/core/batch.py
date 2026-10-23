from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from psapp.providers.base import EditRequest, ImageEditProvider

from .composite import load_image, save_image


@dataclass
class BatchJob:
    input_path: Path
    prompt: str
    output_path: Path


def run_batch(
    jobs: list[BatchJob],
    provider: ImageEditProvider,
    steps: int = 30,
    cfg: float = 4.0,
    on_progress=None,
    should_cancel=None,
) -> list[tuple[BatchJob, bool, str]]:
    results: list[tuple[BatchJob, bool, str]] = []
    total = len(jobs)
    for index, job in enumerate(jobs, start=1):
        if should_cancel is not None and should_cancel():
            break
        try:
            image = load_image(job.input_path)
            request = EditRequest(
                image=image,
                prompt=job.prompt,
                steps=steps,
                cfg=cfg,
                candidates=1,
            )
            result = provider.edit(request)
            if not result.images:
                raise RuntimeError("没有返回图片")
            save_image(result.images[0], job.output_path)
            item = (job, True, str(job.output_path))
        except Exception as exc:
            item = (job, False, str(exc))
        results.append(item)
        if on_progress is not None:
            on_progress(index, total, item)
    return results

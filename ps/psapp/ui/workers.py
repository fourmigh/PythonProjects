from __future__ import annotations

from dataclasses import replace

from PIL import Image
from PySide6.QtCore import QThread, Signal

from psapp.core.batch import BatchJob, run_batch
from psapp.core.cutout import remove_background
from psapp.core.mask import highlight, paste_back
from psapp.providers.base import EditRequest, ImageEditProvider
from psapp.providers.zhipu import PromptRewriter


class EditWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        provider: ImageEditProvider,
        rewriter: PromptRewriter,
        request: EditRequest,
        mask: Image.Image | None = None,
        do_paste_back: bool = True,
        feather: int = 6,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.rewriter = rewriter
        self.request = request
        self.mask = mask
        self.do_paste_back = do_paste_back
        self.feather = feather

    def run(self) -> None:
        try:
            rewritten = self.request.prompt
            rewrite_error = ""
            if self.rewriter is not None and self.rewriter.enabled:
                rewritten = self.rewriter.rewrite(
                    self.request.prompt, has_mask=self.mask is not None
                )
                rewrite_error = self.rewriter.last_error

            image_for_model = self.request.image
            if self.mask is not None:
                image_for_model = highlight(self.request.image, self.mask)

            request = replace(self.request, image=image_for_model, prompt=rewritten)
            result = self.provider.edit(request)

            images = result.images
            if self.mask is not None and self.do_paste_back:
                images = [
                    paste_back(self.request.image, image, self.mask, self.feather)
                    for image in images
                ]

            cost = self.provider.estimate_cost(len(images))
            self.succeeded.emit(
                {
                    "images": images,
                    "original_prompt": self.request.prompt,
                    "prompt": rewritten,
                    "seeds": result.seeds,
                    "warnings": result.warnings,
                    "cost": cost,
                    "mask": self.mask,
                    "rewrite_error": rewrite_error,
                    "steps": request.steps,
                    "cfg": request.cfg,
                    "seed": request.seed,
                }
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class CutoutWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, image: Image.Image) -> None:
        super().__init__()
        self.image = image

    def run(self) -> None:
        try:
            self.succeeded.emit(
                remove_background(self.image, progress=self.progress.emit)
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class BatchWorker(QThread):
    progress = Signal(int, int, str, bool)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        jobs: list[BatchJob],
        provider: ImageEditProvider,
        steps: int,
        cfg: float,
    ) -> None:
        super().__init__()
        self.jobs = jobs
        self.provider = provider
        self.steps = steps
        self.cfg = cfg
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            results = run_batch(
                self.jobs,
                self.provider,
                steps=self.steps,
                cfg=self.cfg,
                on_progress=self._on_progress,
                should_cancel=lambda: self._cancelled,
            )
            self.succeeded.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _on_progress(self, index: int, total: int, item) -> None:
        job, ok, message = item
        self.progress.emit(index, total, f"{job.input_path.name}: {message}", ok)

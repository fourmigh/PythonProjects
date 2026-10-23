from __future__ import annotations

import time

import requests

from psapp.config import AppConfig

from .base import (
    EditRequest,
    EditResult,
    ImageEditProvider,
    ProviderError,
    build_session,
    decode_b64_image,
    download_image,
    error_detail,
    prepare_image,
    to_data_url,
)

DEFAULT_NEGATIVE = "低质量, 模糊, 变形, 比例失调, 多余手指, 文字错乱, 噪点"


class SiliconFlowProvider(ImageEditProvider):
    name = "SiliconFlow"
    cost_per_image = 0.3

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = build_session(
            config.proxy,
            {
                "Authorization": f"Bearer {config.api_key.strip()}",
                "Content-Type": "application/json",
                "X-Enable-Watermark": "0",
                "User-Agent": "PS-Studio/0.1",
            },
        )

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/images/generations"

    def edit(self, request: EditRequest) -> EditResult:
        prepared = prepare_image(request.image, self.config.max_edge)
        data_url = to_data_url(prepared)
        prompt = request.prompt.strip()[:1200]
        negative = request.negative_prompt.strip() or DEFAULT_NEGATIVE

        images = []
        seeds: list[int | None] = []
        warnings: list[str] = []
        last_error: ProviderError | None = None
        count = max(1, int(request.candidates))

        for index in range(count):
            body = {
                "model": self.config.model,
                "prompt": prompt,
                "negative_prompt": negative,
                "image": data_url,
                "num_inference_steps": max(1, min(100, int(request.steps))),
                "cfg": max(0.1, min(20.0, float(request.cfg))),
            }
            if request.seed is not None:
                body["seed"] = int(request.seed) + index

            try:
                payload = self._post(body)
                image, seed = self._parse(payload)
                images.append(image)
                seeds.append(seed)
            except ProviderError as exc:
                last_error = exc
                if not images:
                    raise
                warnings.append(f"第 {index + 1} 张失败：{exc.message}")
                break

        if not images:
            raise last_error or ProviderError("生成失败，接口没有返回图片")

        return EditResult(
            images=images,
            prompt=prompt,
            seeds=seeds,
            warnings=warnings,
            raw=None,
        )

    def _post(self, body: dict) -> dict:
        last_error: ProviderError | None = None
        for attempt in range(3):
            try:
                response = self.session.post(
                    self.endpoint,
                    json=body,
                    timeout=(15, max(30, int(self.config.timeout))),
                )
            except requests.Timeout as exc:
                last_error = ProviderError("请求超时，请检查网络后重试", str(exc))
                if attempt < 2:
                    time.sleep(2 + attempt * 3)
                    continue
                raise last_error
            except requests.RequestException as exc:
                last_error = ProviderError(
                    "网络请求失败，请检查网络或代理设置", str(exc)
                )
                if attempt < 2:
                    time.sleep(2 + attempt * 3)
                    continue
                raise last_error

            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ProviderError("接口返回了无法解析的内容", str(exc))
                if isinstance(payload, dict) and not (
                    payload.get("images") or payload.get("data")
                ):
                    detail = error_detail(response)
                    raise ProviderError("接口没有返回图片", detail)
                return payload

            if response.status_code in (429, 503, 504):
                last_error = self._status_error(response)
                if attempt < 2:
                    time.sleep(3 + attempt * 5)
                    continue
                raise last_error

            if response.status_code in (400, 422):
                detail = error_detail(response).lower()
                removable = [
                    key
                    for key in ("cfg", "negative_prompt")
                    if key in detail and key in body
                ]
                if removable:
                    for key in removable:
                        body.pop(key, None)
                    continue

            raise self._status_error(response)

        raise last_error or ProviderError("请求失败")

    def _status_error(self, response: requests.Response) -> ProviderError:
        detail = error_detail(response)
        status = response.status_code
        if status in (401, 403):
            return ProviderError("API Key 无效或没有权限，请到设置中检查", detail)
        if status == 402:
            return ProviderError("账户余额不足，请先充值", detail)
        if status == 429:
            return ProviderError("请求过于频繁，请稍后再试", detail)
        if status in (400, 422):
            return ProviderError("请求被拒绝，可能是提示词或图片触发了内容审核", detail)
        if status in (503, 504):
            return ProviderError("服务繁忙，请稍后重试", detail)
        return ProviderError(f"接口错误（HTTP {status}）", detail)

    def _parse(self, payload: dict) -> tuple:
        items = payload.get("images") or payload.get("data") or []
        if not isinstance(items, list) or not items:
            raise ProviderError("接口没有返回图片", str(payload)[:300])
        item = items[0]
        seed = payload.get("seed")
        if isinstance(seed, int):
            pass
        elif isinstance(item, dict) and isinstance(item.get("seed"), int):
            seed = item["seed"]
        else:
            seed = None

        if isinstance(item, dict) and item.get("url"):
            return download_image(self.session, item["url"], self.config.timeout), seed
        if isinstance(item, dict) and item.get("b64_json"):
            return decode_b64_image(item["b64_json"]), seed
        raise ProviderError("接口返回的图片格式无法识别", str(item)[:300])

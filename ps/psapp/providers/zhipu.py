from __future__ import annotations

from psapp.config import AppConfig

from .base import build_session

SYSTEM_PROMPT = (
    "你是图像编辑提示词优化助手。将用户的口语指令改写为一条精确、可执行的中文图像编辑提示词。"
    "要求：1. 明确要修改的对象、位置和最终效果；"
    "2. 明确要求保持人物身份、面部、姿态、表情、服装、"
    "光线、构图和其他未提及内容不变；"
    "3. 如果提示本次编辑带有红色高亮区域，必须强调只修改红色半透明"
    "高亮区域，其余区域保持完全不变；"
    "4. 画面边缘和过渡要自然；"
    "5. 只输出提示词本身，不要解释，不要加引号，不超过 250 字。"
)


class PromptRewriter:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.last_error = ""
        self.session = build_session(
            config.proxy,
            {
                "Authorization": f"Bearer {config.zhipu_api_key.strip()}",
                "Content-Type": "application/json",
                "User-Agent": "PS-Studio/0.1",
            },
        )

    @property
    def enabled(self) -> bool:
        return self.config.rewrite_enabled and bool(self.config.zhipu_api_key.strip())

    def rewrite(self, prompt: str, has_mask: bool = False) -> str:
        self.last_error = ""
        if not self.enabled:
            return prompt

        user_text = prompt.strip()
        if has_mask:
            user_text += "\n本次编辑带有红色半透明高亮区域，只修改该区域。"

        body = {
            "model": self.config.zhipu_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }

        try:
            response = self.session.post(
                self.config.zhipu_url,
                json=body,
                timeout=(10, 35),
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            text = str(content).strip().strip('"').strip("'")
            for prefix in ("提示词：", "提示词:", "改写后：", "改写后:"):
                if text.startswith(prefix):
                    text = text[len(prefix):].strip()
            if not text:
                return prompt
            return text[:800]
        except Exception as exc:
            self.last_error = str(exc)[:300]
            return prompt

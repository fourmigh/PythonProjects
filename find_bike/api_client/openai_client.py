# api_client/openai_client.py
# ============================================================
# OpenAI兼容API客户端
# ============================================================

import base64
import time
from pathlib import Path
from typing import Tuple

from .base import BaseAPIClient


class OpenAIClient(BaseAPIClient):
    """OpenAI兼容API客户端"""
    
    def __init__(self, api_key: str, base_url: str, model_name: str, timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        start_time = time.time()
        
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            ext = Path(image_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.bmp': 'image/bmp', '.gif': 'image/gif'
            }.get(ext, 'image/jpeg')
            image_url = f"data:{mime_type};base64,{image_base64}"
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"读取图片失败: {e}", elapsed
        
        from openai import OpenAI
        
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_question},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]}
                ],
                max_tokens=2000,
                temperature=0
            )
            
            elapsed = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            reasoning = ""
            
            return True, answer, reasoning, elapsed
            
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"API调用失败: {e}", elapsed
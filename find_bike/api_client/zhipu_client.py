# api_client/zhipu_client.py
# ============================================================
# 智谱AI API 客户端
# ============================================================

import base64
import time
from typing import Tuple

from .base import BaseAPIClient


class ZhipuClient(BaseAPIClient):
    """智谱AI API 客户端"""
    
    def __init__(self, api_key: str, model_name: str = "glm-4v-flash", timeout: int = 120):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        start_time = time.time()
        
        try:
            from zhipuai import ZhipuAI
            
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            client = ZhipuAI(api_key=self.api_key)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_base64}},
                        {"type": "text", "text": user_question}
                    ]
                }
            ]
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            
            elapsed = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            reasoning = ""
            
            return True, answer, reasoning, elapsed
            
        except ImportError:
            elapsed = time.time() - start_time
            return False, "", "请先安装 zhipuai: pip install zhipuai", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"智谱API调用失败: {e}", elapsed
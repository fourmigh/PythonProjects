# api_client/zhipu_client.py
# ============================================================
# 智谱AI API 客户端
# ============================================================

import base64
import time
import os
import json
from typing import Tuple

from .base import BaseAPIClient

API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


class ZhipuClient(BaseAPIClient):
    """智谱AI API 客户端"""
    
    def __init__(self, api_key: str, model_name: str = "glm-4v-flash", timeout: int = 120):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def _build_data_uri(self, image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.bmp': 'bmp', '.gif': 'gif'}
        mime_type = mime_map.get(ext, 'png')
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/{mime_type};base64,{image_base64}"
    
    def _call_ocr_via_httpx(self, data_uri: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        import httpx
        
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": user_question}
                    ]
                }
            ],
            "stream": False
        }
        
        response = httpx.post(
            f"{API_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=body,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        data = response.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return True, answer, "", 0.0
    
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        start_time = time.time()
        
        try:
            is_ocr = 'ocr' in self.model_name.lower()
            
            if is_ocr:
                data_uri = self._build_data_uri(image_path)
                success, answer, reasoning, _ = self._call_ocr_via_httpx(
                    data_uri, system_prompt, user_question
                )
                elapsed = time.time() - start_time
                return success, answer, reasoning, elapsed
            
            from zhipuai import ZhipuAI
            
            data_uri = self._build_data_uri(image_path)
            
            client = ZhipuAI(api_key=self.api_key)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": user_question}
                    ]
                }
            ]
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                timeout=self.timeout
            )
            
            elapsed = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            reasoning = ""
            
            return True, answer, reasoning, elapsed
            
        except ImportError as e:
            elapsed = time.time() - start_time
            return False, "", f"导入zhipuai失败: {e}。请安装: pip install zhipuai", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"智谱API调用失败: {e}", elapsed
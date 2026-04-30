# api_client/ollama_client.py
# ============================================================
# Ollama API 客户端 - 统一使用 HTTP API
# ============================================================

import os
import base64
import time
import requests
import subprocess
from pathlib import Path
from typing import Tuple, List

from .base import BaseAPIClient


class OllamaClient(BaseAPIClient):
    """Ollama API 客户端 - 统一使用 HTTP API"""
    
    def __init__(self, api_url: str, model_name: str = None, timeout: int = 120, 
                 max_tokens: int = 2000, temperature: float = 0):
        # 清理 API URL
        self.api_url = api_url.rstrip('/')
        if self.api_url.endswith('/v1/chat/completions'):
            self.api_url = self.api_url.replace('/v1/chat/completions', '')
        
        self.config_model_name = model_name if model_name else None
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._actual_model = None
    
    def get_model_name(self) -> str:
        """获取当前实际使用的模型名称"""
        if self._actual_model:
            return self._actual_model
        
        if self.config_model_name:
            self._actual_model = self.config_model_name
            print(f"[INFO] 使用配置的模型: {self._actual_model}")
            return self._actual_model
        
        running = self._get_running_model()
        if running:
            self._actual_model = running
            print(f"[INFO] 自动检测到运行中的模型: {self._actual_model}")
            return self._actual_model
        
        installed = self._get_installed_models()
        if installed:
            self._actual_model = installed[0]
            print(f"[WARN] 没有运行中的模型，使用已安装模型: {self._actual_model}")
            return self._actual_model
        
        self._actual_model = "unknown"
        print(f"[ERROR] 没有找到任何可用模型")
        return self._actual_model
    
    def _get_running_model(self) -> str:
        """获取当前正在运行的模型"""
        try:
            response = requests.get(f"{self.api_url}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'models' in data and data['models']:
                    model = data['models'][0]
                    if 'name' in model:
                        return model['name']
                    if 'model' in model:
                        return model['model']
        except Exception as e:
            print(f"[DEBUG] API查询失败: {e}")
        
        # 命令行备用
        try:
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.split()
                            if parts:
                                return parts[0]
        except Exception as e:
            print(f"[DEBUG] 命令行查询失败: {e}")
        
        return None
    
    def _get_installed_models(self) -> List[str]:
        """获取已安装的模型列表"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return [m.get('name', '') for m in models]
        except Exception:
            pass
        
        # 命令行备用
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                models = []
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            models.append(parts[0])
                return models
        except Exception:
            pass
        
        return []

    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        """调用 Ollama API 识别图片"""
        start_time = time.time()
        
        model_name = self.get_model_name()
        
        if model_name == "unknown":
            elapsed = time.time() - start_time
            return False, "", "没有可用的模型", elapsed
        
        if not os.path.exists(image_path):
            elapsed = time.time() - start_time
            return False, "", f"图片不存在: {image_path}", elapsed
        
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode()
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"读取图片失败: {e}", elapsed
        
        url = f"{self.api_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": f"{system_prompt}\n\n{user_question}",
            "images": [image_base64],
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
                "repeat_penalty": 1.1,
                "top_k": 40,
                "top_p": 0.9,
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code != 200:
                elapsed = time.time() - start_time
                return False, "", f"HTTP {response.status_code}: {response.text[:200]}", elapsed
            
            result = response.json()
            answer = result.get("response", "").strip()
            
            if not answer:
                elapsed = time.time() - start_time
                return False, "", "模型返回空响应", elapsed
            
            elapsed = time.time() - start_time
            return True, answer, "", elapsed
            
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            return False, "", f"请求超时({self.timeout}秒)", elapsed
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            return False, "", f"连接失败: {e}", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"请求异常: {type(e).__name__}: {e}", elapsed
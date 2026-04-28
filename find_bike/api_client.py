# api_client.py
# ============================================================
# API客户端抽象层 - 支持多种API提供商
# ============================================================

import os
import base64
import time
import requests
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Dict, Any


class BaseAPIClient(ABC):
    """API客户端基类"""
    
    @abstractmethod
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass


# api_client.py 中的 OllamaClient 类（完整修复版）

class OllamaClient(BaseAPIClient):
    """Ollama API 客户端 - 自动使用运行中的模型"""
    
    def __init__(self, api_url: str, model_name: str = None, timeout: int = 120, 
                 max_tokens: int = 2000, temperature: float = 0):
        # 清理 API URL
        self.api_url = api_url.rstrip('/')
        if self.api_url.endswith('/v1/chat/completions'):
            self.api_url = self.api_url.replace('/v1/chat/completions', '')
        
        # 如果 model_name 是空字符串，也视为 None
        self.config_model_name = model_name if model_name else None
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._actual_model = None  # 实际使用的模型
    
    def get_model_name(self) -> str:
        """获取当前实际使用的模型名称"""
        # 如果有缓存，直接返回
        if self._actual_model:
            return self._actual_model
        
        # 优先使用配置文件中的模型名
        if self.config_model_name:
            self._actual_model = self.config_model_name
            print(f"[INFO] 使用配置的模型: {self._actual_model}")
            return self._actual_model
        
        # 自动检测运行中的模型
        running = self._get_running_model()
        if running:
            self._actual_model = running
            print(f"[INFO] 自动检测到运行中的模型: {self._actual_model}")
            return self._actual_model
        
        # 降级到已安装的第一个模型
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
                
                # 根据你的实际输出，数据格式是 {'models': [{'name': 'llava-phi3:latest', ...}]}
                if 'models' in data and data['models']:
                    model = data['models'][0]
                    # 优先使用 name 字段
                    if 'name' in model:
                        return model['name']
                    if 'model' in model:
                        return model['model']
        except Exception as e:
            print(f"[DEBUG] API查询失败: {e}")
        
        # 命令行备用
        try:
            import subprocess
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
    
    def _get_installed_models(self) -> list:
        """获取已安装的模型列表"""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return [m.get('name', '') for m in models]
        except Exception:
            pass
        return []

    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        start_time = time.time()
        
        # 获取实际使用的模型
        model_name = self.get_model_name()
        
        print(f"[DEBUG] 使用模型: {model_name}")
        print(f"[DEBUG] 图片路径: {image_path}")
        print(f"[DEBUG] 图片存在: {os.path.exists(image_path)}")
        
        if model_name == "unknown":
            elapsed = time.time() - start_time
            return False, "", "没有可用的模型", elapsed
        
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode()
            print(f"[DEBUG] 图片大小: {len(image_data)} bytes")
            print(f"[DEBUG] Base64长度: {len(image_base64)}")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[DEBUG] 读取图片失败: {e}")
            return False, "", f"读取图片失败: {e}", elapsed
        
        # 使用 Ollama 原生 API
        url = f"{self.api_url}/api/generate"
        payload = {
            "model": model_name,
            "prompt": f"{system_prompt}\n\n{user_question}",
            "images": [image_base64],
            "stream": False,
            "options": {
                "num_predict": 512,
                "temperature": 0.3,
                "repeat_penalty": 1.1,      # 重复惩罚系数（>1 惩罚重复）
                "repeat_last_n": 64,        # 检查最近多少个token的重复
                "top_k": 40,                # 限制采样范围
                "top_p": 0.9,               # 核采样
                "frequency_penalty": 0.5,   # 频率惩罚
                "presence_penalty": 0.5     # 存在惩罚
            }
        }
        
        print(f"[DEBUG] API URL: {url}")
        print(f"[DEBUG] 请求大小: {len(str(payload))} bytes")
        
        try:
            print(f"[DEBUG] 发送请求...")
            response = requests.post(url, json=payload, timeout=self.timeout)
            print(f"[DEBUG] HTTP状态码: {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            elapsed = time.time() - start_time
            answer = result.get("response", "").strip()
            print(f"[DEBUG] 响应长度: {len(answer)}")
            
            if not answer:
                print(f"[DEBUG] 响应为空，完整结果: {result}")
            
            return True, answer, "", elapsed
            
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"[DEBUG] 请求超时")
            return False, "", f"API请求超时({self.timeout}秒)", elapsed
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"[DEBUG] 连接错误: {e}")
            return False, "", f"网络连接失败: {e}", elapsed
        except requests.exceptions.HTTPError as e:
            elapsed = time.time() - start_time
            print(f"[DEBUG] HTTP错误: {e}")
            if e.response.status_code == 404:
                return False, "", f"模型 '{model_name}' 不存在", elapsed
            print(f"[DEBUG] 响应内容: {e.response.text[:500]}")
            return False, "", f"HTTP错误: {e}", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[DEBUG] 未知错误: {type(e).__name__}: {e}")
            return False, "", f"未知错误: {e}", elapsed


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


class BedrockClient(BaseAPIClient):
    """Amazon Bedrock API 客户端"""
    
    def __init__(self, model_id: str, region_name: str = "us-east-1",
                 bearer_token: str = None, access_key_id: str = None,
                 secret_access_key: str = None, session_token: str = None,
                 timeout: int = 120):
        
        self.model_id = model_id
        self.region_name = region_name
        self.timeout = timeout
        
        if bearer_token:
            self.auth_type = "bearer"
            self.bearer_token = bearer_token
            self.client = None
        else:
            self.auth_type = "iam"
            import boto3
            from botocore.config import Config as Boto3Config
            config = Boto3Config(region_name=region_name, read_timeout=timeout)
            
            if access_key_id and secret_access_key:
                self.client = boto3.client('bedrock-runtime', config=config,
                    aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token)
            else:
                self.client = boto3.client('bedrock-runtime', config=config)
    
    def get_model_name(self) -> str:
        return self.model_id
    
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        import json
        start_time = time.time()
        
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            ext = Path(image_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.bmp': 'image/bmp', '.gif': 'image/gif'
            }.get(ext, 'image/jpeg')
            
            if self.auth_type == "bearer":
                return self._call_with_bearer_token(image_base64, mime_type, system_prompt, user_question, start_time)
            else:
                return self._call_with_iam(image_base64, mime_type, system_prompt, user_question, start_time)
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"Bedrock调用失败: {e}", elapsed
    
    def _call_with_bearer_token(self, image_base64: str, mime_type: str,
                                 system_prompt: str, user_question: str,
                                 start_time: float) -> Tuple[bool, str, str, float]:
        import json, requests
        endpoint = f"https://bedrock-runtime.{self.region_name}.amazonaws.com/model/{self.model_id}/invoke"
        request_body = {
            "anthropic_version": "bedrock-2023-05-31", "max_tokens": 2000, "temperature": 0.1,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_base64}},
                {"type": "text", "text": f"{system_prompt}\n\n{user_question}"}
            ]}]
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Authorization": f"Bearer {self.bearer_token}"}
        
        response = requests.post(endpoint, headers=headers, json=request_body, timeout=self.timeout)
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            return False, "", f"HTTP {response.status_code}: {response.text}", elapsed
        
        result = response.json()
        answer = result.get('content', [{}])[0].get('text', '').strip()
        return True, answer, "", elapsed
    
    def _call_with_iam(self, image_base64: str, mime_type: str,
                        system_prompt: str, user_question: str,
                        start_time: float) -> Tuple[bool, str, str, float]:
        import json
        request_body = {
            "anthropic_version": "bedrock-2023-05-31", "max_tokens": 2000, "temperature": 0.1,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_base64}},
                {"type": "text", "text": f"{system_prompt}\n\n{user_question}"}
            ]}]
        }
        response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(request_body))
        elapsed = time.time() - start_time
        response_body = json.loads(response['body'].read())
        answer = response_body.get('content', [{}])[0].get('text', '').strip()
        return True, answer, "", elapsed


def create_api_client(api_type: str, config: Dict[str, Any]) -> BaseAPIClient:
    """根据API类型创建对应的客户端"""
    api_type = api_type.lower()
    
    if api_type == 'ollama':
        return OllamaClient(
            api_url=config.get('api_url', 'http://localhost:11434'),
            model_name=config.get('model_name'),  # 可为 None
            timeout=config.get('timeout', 120),
            max_tokens=config.get('max_tokens', 2000),
            temperature=config.get('temperature', 0)
        )
    elif api_type == 'zhipu':
        return ZhipuClient(api_key=config.get('api_key', ''), model_name=config.get('model_name', 'glm-4v-flash'))
    elif api_type == 'openai':
        return OpenAIClient(api_key=config.get('api_key', ''), base_url=config.get('base_url', ''),
                           model_name=config.get('model_name', ''), timeout=config.get('timeout', 120))
    elif api_type == 'bedrock':
        return BedrockClient(model_id=config.get('model_id'), region_name=config.get('region_name', 'us-east-1'),
                            bearer_token=config.get('bearer_token'), access_key_id=config.get('access_key_id'),
                            secret_access_key=config.get('secret_access_key'), timeout=config.get('timeout', 120))
    else:
        raise ValueError(f"不支持的API类型: {api_type}")
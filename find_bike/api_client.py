# api_client.py
# ============================================================
# API客户端抽象层 - 支持多种API提供商
# ============================================================

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
        """
        发送图像和文本到模型，获取回答
        
        Args:
            image_path: 图片文件路径
            system_prompt: 系统提示词
            user_question: 用户问题
        
        Returns:
            tuple: (是否成功, 模型回答, 推理过程/错误信息, 耗时秒数)
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        pass


class OllamaClient(BaseAPIClient):
    """Ollama API 客户端"""
    
    def __init__(self, api_url: str, model_name: str, timeout: int = 120, max_tokens: int = 2000, temperature: float = 0):
        self.api_url = api_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def get_model_name(self) -> str:
        return self.model_name
    
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        start_time = time.time()
        
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"读取图片失败: {e}", elapsed
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_question},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "stream": False,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            elapsed = time.time() - start_time
            answer = result["choices"][0]["message"].get("content", "").strip()
            reasoning = result["choices"][0]["message"].get("reasoning", "")
            
            return True, answer, reasoning, elapsed
            
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            return False, "", f"API请求超时({self.timeout}秒)", elapsed
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            return False, "", f"网络连接失败: {e}", elapsed
        except requests.exceptions.HTTPError as e:
            elapsed = time.time() - start_time
            return False, "", f"HTTP错误: {e}", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"未知错误: {e}", elapsed


class ZhipuClient(BaseAPIClient):
    """智谱AI API 客户端 (GLM-4V-Flash) - 使用官方 SDK"""
    
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
            
            # 读取并编码图片
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
            
            # 创建客户端
            client = ZhipuAI(api_key=self.api_key)
            
            # 构建消息
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
            
            # 调用 API
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
            error_msg = str(e)
            if "1210" in error_msg:
                error_msg = "API参数错误。请检查：\n1. temperature 必须在 (0,1) 之间\n2. top_p 必须在 (0,1) 之间\n3. 模型名称是否正确"
            return False, "", f"智谱API调用失败: {error_msg}", elapsed


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
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif'
            }.get(ext, 'image/jpeg')
            
            image_url = f"data:{mime_type};base64,{image_base64}"
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"读取图片失败: {e}", elapsed
        
        from openai import OpenAI
        
        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_question},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
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
    """
    Amazon Bedrock API 客户端
    支持 API Key（Bearer Token）和 IAM 凭证两种认证方式
    """
    
    def __init__(self, 
                 model_id: str,
                 region_name: str = "us-east-1",
                 bearer_token: str = None,
                 access_key_id: str = None,
                 secret_access_key: str = None,
                 session_token: str = None,
                 timeout: int = 120):
        
        self.model_id = model_id
        self.region_name = region_name
        self.timeout = timeout
        
        # 优先使用 API Key 方式
        if bearer_token:
            self.auth_type = "bearer"
            self.bearer_token = bearer_token
            self.client = None
        else:
            # 回退到 IAM 凭证方式
            self.auth_type = "iam"
            import boto3
            from botocore.config import Config as Boto3Config
            
            config = Boto3Config(
                region_name=region_name,
                read_timeout=timeout,
                connect_timeout=10,
                retries={'max_attempts': 3}
            )
            
            if access_key_id and secret_access_key:
                self.client = boto3.client(
                    'bedrock-runtime',
                    config=config,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token
                )
            else:
                self.client = boto3.client('bedrock-runtime', config=config)
    
    def get_model_name(self) -> str:
        return self.model_id
    
    def chat_with_image(self, image_path: str, system_prompt: str, 
                        user_question: str) -> Tuple[bool, str, str, float]:
        
        start_time = time.time()
        
        try:
            # 读取并编码图片
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            
            ext = Path(image_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif'
            }.get(ext, 'image/jpeg')
            
            # 根据认证方式选择调用方法
            if self.auth_type == "bearer":
                return self._call_with_bearer_token(
                    image_base64, mime_type, system_prompt, user_question, start_time
                )
            else:
                return self._call_with_iam(
                    image_base64, mime_type, system_prompt, user_question, start_time
                )
                
        except Exception as e:
            elapsed = time.time() - start_time
            return False, "", f"Bedrock API 调用失败: {e}", elapsed
    
    def _call_with_bearer_token(self, image_base64: str, mime_type: str,
                                 system_prompt: str, user_question: str,
                                 start_time: float) -> Tuple[bool, str, str, float]:
        """使用 Bearer Token 方式调用 Bedrock API"""
        import json
        import requests
        
        endpoint = f"https://bedrock-runtime.{self.region_name}.amazonaws.com/model/{self.model_id}/invoke"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"{system_prompt}\n\n{user_question}"
                        }
                    ]
                }
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_body,
            timeout=self.timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            return False, "", f"HTTP {response.status_code}: {response.text}", elapsed
        
        result = response.json()
        answer = result.get('content', [{}])[0].get('text', '').strip()
        
        return True, answer, "", elapsed
    
    def _call_with_iam(self, image_base64: str, mime_type: str,
                        system_prompt: str, user_question: str,
                        start_time: float) -> Tuple[bool, str, str, float]:
        """使用 IAM 凭证方式调用 Bedrock API"""
        import json
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"{system_prompt}\n\n{user_question}"
                        }
                    ]
                }
            ]
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        
        elapsed = time.time() - start_time
        response_body = json.loads(response['body'].read())
        answer = response_body.get('content', [{}])[0].get('text', '').strip()
        
        return True, answer, "", elapsed


# ============================================================
# 工厂函数：根据配置创建客户端
# ============================================================

def create_api_client(api_type: str, config: Dict[str, Any]) -> BaseAPIClient:
    """
    根据API类型创建对应的客户端
    
    Args:
        api_type: API类型，支持 'ollama', 'zhipu', 'openai', 'bedrock'
        config: 配置字典，包含对应API所需的参数
    
    Returns:
        BaseAPIClient实例
    """
    api_type = api_type.lower()
    
    if api_type == 'ollama':
        return OllamaClient(
            api_url=config.get('api_url', 'http://localhost:11434/v1/chat/completions'),
            model_name=config.get('model_name', 'llama3.2-vision'),
            timeout=config.get('timeout', 120),
            max_tokens=config.get('max_tokens', 2000),
            temperature=config.get('temperature', 0)
        )
    
    elif api_type == 'zhipu':
        return ZhipuClient(
            api_key=config.get('api_key', ''),
            model_name=config.get('model_name', 'glm-4v-flash'),
            timeout=config.get('timeout', 120)
        )
    
    elif api_type == 'openai':
        return OpenAIClient(
            api_key=config.get('api_key', ''),
            base_url=config.get('base_url', ''),
            model_name=config.get('model_name', ''),
            timeout=config.get('timeout', 120)
        )
    
    elif api_type == 'bedrock':
        return BedrockClient(
            model_id=config.get('model_id'),
            region_name=config.get('region_name', 'us-east-1'),
            bearer_token=config.get('bearer_token'),
            access_key_id=config.get('access_key_id'),
            secret_access_key=config.get('secret_access_key'),
            session_token=config.get('session_token'),
            timeout=config.get('timeout', 120)
        )
    
    else:
        raise ValueError(f"不支持的API类型: {api_type}")
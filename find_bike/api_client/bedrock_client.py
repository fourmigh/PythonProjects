# api_client/bedrock_client.py
# ============================================================
# Amazon Bedrock API 客户端
# ============================================================

import base64
import json
import time
from pathlib import Path
from typing import Tuple

from .base import BaseAPIClient


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
        import requests
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
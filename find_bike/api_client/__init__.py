# api_client/__init__.py
# ============================================================
# API客户端模块 - 统一导出入口
# ============================================================

from typing import Dict, Any
from .base import BaseAPIClient
from .ollama_client import OllamaClient
from .zhipu_client import ZhipuClient
from .openai_client import OpenAIClient
from .bedrock_client import BedrockClient


def create_api_client(api_type: str, config: Dict[str, Any]) -> BaseAPIClient:
    """根据API类型创建对应的客户端"""
    api_type = api_type.lower()
    
    if api_type == 'ollama':
        return OllamaClient(
            api_url=config.get('api_url', 'http://localhost:11434'),
            model_name=config.get('model_name'),
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


__all__ = [
    'BaseAPIClient',
    'OllamaClient',
    'ZhipuClient', 
    'OpenAIClient',
    'BedrockClient',
    'create_api_client'
]
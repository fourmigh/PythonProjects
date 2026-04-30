# api_client/base.py
# ============================================================
# API客户端基类
# ============================================================

from abc import ABC, abstractmethod
from typing import Tuple


class BaseAPIClient(ABC):
    """API客户端基类"""
    
    @abstractmethod
    def chat_with_image(self, image_path: str, system_prompt: str, user_question: str) -> Tuple[bool, str, str, float]:
        """
        调用API识别图片
        
        Returns:
            Tuple[bool, str, str, float]: (是否成功, 回答内容, 推理过程, 耗时)
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """获取模型名称"""
        pass
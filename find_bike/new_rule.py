# new_rule.py
from base_prompt_optimizer import BasePromptOptimizer
from typing import Dict, Tuple, Optional

class MyNewOptimizer(BasePromptOptimizer):
    
    def get_rule_name(self) -> str:
        return "my_new_rule"
    
    def get_rule_description(self) -> str:
        return "我的新业务规则描述"
    
    def get_default_system_prompt(self) -> str:
        return """你的系统提示词..."""
    
    def get_default_user_prompt(self) -> str:
        return "你的用户提示词..."
    
    def parse_response(self, answer: str) -> Tuple[bool, str]:
        # 解析模型回答
        if "【结论】是" in answer:
            return True, ""
        return False, ""
    
    def get_expected_from_filename(self, filename: str) -> Optional[bool]:
        # 根据文件名判断期望
        if not filename:
            return None
        return filename[0] == '是'
    
    def get_error_patterns(self) -> Dict:
        return {
            "false_positive": {
                "keywords": [],
                "add_to_user_prompt": "\n\n注意：...",
                "add_to_system_prompt": "..."
            },
            "false_negative": {
                "keywords": [],
                "add_to_user_prompt": "\n\n请仔细检查...",
                "add_to_system_prompt": "..."
            }
        }
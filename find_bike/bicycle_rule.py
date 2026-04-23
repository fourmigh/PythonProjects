# bicycle_rule.py
# ============================================================
# 业务规则：判断图片中是否有自行车且无车牌
# ============================================================

from typing import Dict, Tuple, Optional
from base_prompt_optimizer import BasePromptOptimizer


class BicycleNoPlateOptimizer(BasePromptOptimizer):
    """自行车无车牌判断优化器"""
    
    def get_rule_name(self) -> str:
        return "bicycle_no_plate"
    
    def get_rule_description(self) -> str:
        return "判断图片中是否有自行车，且自行车上没有车牌"
    
    def get_default_system_prompt(self) -> str:
        return """你是一个图像分析助手。请严格按照以下步骤分析图片：

第一步：判断图片中是否有自行车
注意：自行车包括完整自行车或局部（如车轮、车架、链条、座垫、车把等），只要能看到自行车的一部分就算有自行车。

第二步：判断自行车上是否有车牌（包括任何带数字/字母的矩形牌子）

第三步：根据以下规则输出结论：
- 如果【有自行车】且【无车牌】→ 输出【结论】是
- 其他所有情况（无自行车、有车牌、无法确定）→ 输出【结论】否

【特别注意】即使你看到了车牌，也要输出"否"！不要输出"是"。

输出格式：【分析】...【结论】是/否
"""
    
    def get_default_user_prompt(self) -> str:
        return "请分析这张图片：是否有自行车（包括自行车局部），且自行车上没有车牌？"
    
    def parse_response(self, answer: str) -> Tuple[bool, str]:
        reasoning = ""
        
        # 提取推理过程
        if "【分析】" in answer and "【结论】" in answer:
            parts = answer.split("【结论】")
            reasoning = parts[0].replace("【分析】", "").strip()
        
        # 提取结论
        if "【结论】是" in answer:
            return True, reasoning
        elif "【结论】否" in answer:
            return False, reasoning
        else:
            # 尝试从回答中直接判断
            if "是" in answer[:20] and "否" not in answer[:20]:
                return True, reasoning
            else:
                return False, reasoning
    
    def get_expected_from_filename(self, filename: str) -> Optional[bool]:
        if not filename:
            return None
        first_char = filename[0]
        if first_char == '是':
            return True
        elif first_char == '否':
            return False
        return None
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
        if "【分析】" in answer and "【结论】" in answer:
            parts = answer.split("【结论】")
            reasoning = parts[0].replace("【分析】", "").strip()
        
        if "【结论】是" in answer:
            return True, reasoning
        elif "【结论】否" in answer:
            return False, reasoning
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
    
    def get_error_patterns(self) -> Dict:
        return {
            # 误报：实际不符合（无自行车/有车牌），模型认为符合
            "false_positive": {
                "keywords": ["贴纸", "sticker", "标签", "label", "品牌"],
                "add_to_user_prompt": "\n\n注意：品牌贴纸、尺寸标签、说明书等不算车牌，请忽略它们。",
                "add_to_system_prompt": "请忽略车辆上的品牌贴纸、尺寸标签、说明书等非官方车牌物品。"
            },
            # 漏报：模型没有识别出自行车（推理中没有自行车相关词汇）
            "false_negative_bicycle": {
                "keywords": [],
                "add_to_user_prompt": "\n\n请仔细检查图片中是否有自行车。自行车包括完整自行车或局部（如车轮、车架、链条、座垫、车把等）。",
                "add_to_system_prompt": "请仔细识别图片中是否有自行车。自行车包括完整自行车或局部（如车轮、车架、链条等）。"
            },
            # 漏报：模型看到了车牌，所以回答"否"
            "false_negative_plate": {
                "keywords": [],
                "add_to_user_prompt": "\n\n请仔细检查整张图片，即使车牌不清晰、角度倾斜、部分被遮挡，也认为有车牌。",
                "add_to_system_prompt": "请仔细检查图片中的任何位置，寻找矩形带数字/字母的牌子。"
            },
            # 结论错误：看到了自行车但没有正确应用规则
            "conclusion_error": {
                "keywords": [],
                "add_to_user_prompt": "\n\n【重要】判断规则：\n- 有自行车（包括局部）且无车牌 → 回答\"是\"\n- 其他情况 → 回答\"否\"\n\n如果你在图片中看到了自行车（包括车轮、车架等局部），且没有看到车牌，请回答\"是\"。",
                "add_to_system_prompt": "【关键规则】有自行车（包括局部）且无车牌时必须回答\"是\"。"
            }
        }
    
    def analyze_error(self, reasoning: str, expected: bool, actual: bool,
                      image_filename: str = "") -> Dict:
        """分析错误原因"""
        if actual == expected:
            return {"error_type": "correct", "confidence": 100}
        
        reasoning_lower = reasoning.lower()
        patterns = self.get_error_patterns()
        
        # 检查推理中是否提到了自行车相关词汇（包括局部）
        bicycle_keywords = [
            "自行车", "bicycle", "bike", "车轮", "wheel", "车架", "frame", 
            "链条", "chain", "座垫", "seat", "车把", "handlebar", "轮胎", "tire",
            "局部", "部分", "后轮", "前轮", "零件"
        ]
        has_bicycle_in_reasoning = any(kw in reasoning_lower for kw in bicycle_keywords)
        
        # 检查推理中是否提到了车牌相关词汇
        plate_keywords = ["车牌", "plate", "牌照", "号码", "number", "贴纸", "sticker", "标签", "label", "注册"]
        has_plate_in_reasoning = any(kw in reasoning_lower for kw in plate_keywords)
        
        if expected == True and actual == False:
            # 期望"是"（有自行车且无车牌），实际"否"
            
            if has_plate_in_reasoning:
                # 模型看到了车牌，所以回答"否"（正确逻辑，但期望是"是"说明图片中不应该有车牌）
                # 可能是模型误将贴纸等识别为车牌
                pattern = patterns.get("false_positive", {})
                return {
                    "error_type": "false_positive",
                    "confidence": 85,
                    "add_to_user_prompt": pattern.get("add_to_user_prompt", ""),
                    "add_to_system_prompt": pattern.get("add_to_system_prompt", "")
                }
            elif has_bicycle_in_reasoning:
                # 模型看到了自行车，但回答"否" - 判断逻辑错误
                pattern = patterns.get("conclusion_error", {})
                return {
                    "error_type": "conclusion_error",
                    "confidence": 90,
                    "add_to_user_prompt": pattern.get("add_to_user_prompt", ""),
                    "add_to_system_prompt": pattern.get("add_to_system_prompt", "")
                }
            else:
                # 模型没有识别出自行车
                pattern = patterns.get("false_negative_bicycle", {})
                return {
                    "error_type": "false_negative_bicycle",
                    "confidence": 85,
                    "add_to_user_prompt": pattern.get("add_to_user_prompt", ""),
                    "add_to_system_prompt": pattern.get("add_to_system_prompt", "")
                }
        
        elif expected == False and actual == True:
            # 期望"否"（无自行车/有车牌），实际"是"
            pattern = patterns.get("false_positive", {})
            return {
                "error_type": "false_positive",
                "confidence": 85,
                "add_to_user_prompt": pattern.get("add_to_user_prompt", ""),
                "add_to_system_prompt": pattern.get("add_to_system_prompt", "")
            }
        
        return {
            "error_type": "unknown",
            "confidence": 0,
            "add_to_user_prompt": "",
            "add_to_system_prompt": ""
        }
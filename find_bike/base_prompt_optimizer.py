# base_prompt_optimizer.py
# ============================================================
# 提示词优化器基类 - 不包含具体业务逻辑
# ============================================================

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from api_client import create_api_client
from config import API_TYPE, OLLAMA_CONFIG, ZHIPU_CONFIG, OPENAI_CONFIG, BEDROCK_CONFIG


class BasePromptOptimizer(ABC):
    """
    提示词优化器基类
    
    优化策略：
    1. 遍历所有测试图片
    2. 遇到第一个错误时，立即停止本轮测试
    3. 分析错误并优化提示词
    4. 从头开始重新测试所有图片
    5. 重复直到全部通过或达到最大轮次
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client or self._create_api_client()
        self.optimization_dir = Path("optimization_history")
        self.optimization_dir.mkdir(exist_ok=True)
        
        # 优化状态
        self.current_user_prompt = None
        self.current_system_prompt = None
        self.optimization_history = []  # 记录每次优化
        self.round_history = []  # 记录每轮测试结果
    
    def _create_api_client(self):
        """创建API客户端"""
        if API_TYPE == 'ollama':
            return create_api_client('ollama', OLLAMA_CONFIG)
        elif API_TYPE == 'zhipu':
            return create_api_client('zhipu', ZHIPU_CONFIG)
        elif API_TYPE == 'openai':
            return create_api_client('openai', OPENAI_CONFIG)
        elif API_TYPE == 'bedrock':
            return create_api_client('bedrock', BEDROCK_CONFIG)
        raise ValueError(f"不支持的API类型: {API_TYPE}")
    
    # ============================================================
    # 抽象方法 - 子类必须实现
    # ============================================================
    
    @abstractmethod
    def get_rule_name(self) -> str:
        """返回规则名称"""
        pass
    
    @abstractmethod
    def get_rule_description(self) -> str:
        """返回规则描述"""
        pass
    
    @abstractmethod
    def get_default_system_prompt(self) -> str:
        """返回默认的系统提示词"""
        pass
    
    @abstractmethod
    def get_default_user_prompt(self) -> str:
        """返回默认的用户提示词"""
        pass
    
    @abstractmethod
    def parse_response(self, answer: str) -> Tuple[bool, str]:
        """
        解析模型回答
        
        Args:
            answer: 模型的原始回答
        
        Returns:
            tuple: (是否符合条件, 推理过程)
        """
        pass
    
    @abstractmethod
    def get_expected_from_filename(self, filename: str) -> Optional[bool]:
        """
        根据文件名判断期望结果
        
        Args:
            filename: 文件名
        
        Returns:
            True: 期望符合条件
            False: 期望不符合条件
            None: 无法判断（跳过验证）
        """
        pass
    
    @abstractmethod
    def get_error_patterns(self) -> Dict:
        """
        返回错误类型及优化策略
        
        格式:
        {
            "false_positive": {
                "add_to_user_prompt": "添加到用户提示词的内容",
                "add_to_system_prompt": "添加到系统提示词的内容"
            },
            "false_negative_bicycle": {
                "add_to_user_prompt": "...",
                "add_to_system_prompt": "..."
            },
            "false_negative_plate": {
                "add_to_user_prompt": "...",
                "add_to_system_prompt": "..."
            },
            "conclusion_error": {
                "add_to_user_prompt": "...",
                "add_to_system_prompt": "..."
            }
        }
        """
        pass
    
    # ============================================================
    # 可重写方法
    # ============================================================
    
    def analyze_error(self, reasoning: str, expected: bool, actual: bool,
                      image_filename: str = "") -> Dict:
        """
        分析错误原因，子类可重写以实现更精准的分析
        
        Returns:
            dict: 包含 error_type, confidence, add_to_user_prompt, add_to_system_prompt
        """
        if actual == expected:
            return {"error_type": "correct", "confidence": 100}
        
        patterns = self.get_error_patterns()
        reasoning_lower = reasoning.lower()
        
        # 根据期望和实际结果判断默认错误类型
        if expected and not actual:
            error_type = "false_negative"
        elif not expected and actual:
            error_type = "false_positive"
        else:
            error_type = "unknown"
        
        pattern = patterns.get(error_type, {})
        return {
            "error_type": error_type,
            "confidence": 60,
            "add_to_user_prompt": pattern.get("add_to_user_prompt", ""),
            "add_to_system_prompt": pattern.get("add_to_system_prompt", "")
        }
    
    def optimize_prompts(self, error_analysis: Dict) -> Tuple[str, str]:
        """根据错误分析优化提示词"""
        new_user = self.current_user_prompt
        new_system = self.current_system_prompt
        
        add_user = error_analysis.get("add_to_user_prompt", "")
        if add_user and add_user not in new_user:
            new_user += add_user
        
        add_system = error_analysis.get("add_to_system_prompt", "")
        if add_system and add_system not in new_system:
            new_system = new_system.rstrip() + "\n\n" + add_system
        
        return new_user, new_system
    
    def call_model(self, image_path: str) -> Tuple[bool, str, str, float]:
        """调用大模型"""
        return self.api_client.chat_with_image(
            image_path, self.current_system_prompt, self.current_user_prompt
        )
    
    def test_single_image(self, image_path: str, expected: bool, 
                          verbose: bool = False) -> Dict:
        """测试单张图片"""
        filename = Path(image_path).name
        success, answer, reasoning, elapsed = self.call_model(image_path)
        
        if not success:
            return {
                "success": False,
                "filename": filename,
                "error": f"API调用失败: {answer}"
            }
        
        actual, reasoning_text = self.parse_response(answer)
        
        result = {
            "success": True,
            "filename": filename,
            "expected": expected,
            "actual": actual,
            "is_correct": (actual == expected),
            "answer": answer,
            "reasoning": reasoning or reasoning_text,
            "elapsed": elapsed
        }
        
        if verbose:
            status = "[OK]" if result["is_correct"] else "[FAIL]"
            print(f"  {status} 期望:{'是' if expected else '否'} 实际:{'是' if actual else '否'} 耗时:{elapsed:.2f}s")
            if not result["is_correct"] and result["reasoning"]:
                reasoning_preview = result["reasoning"][:200]
                if len(result["reasoning"]) > 200:
                    reasoning_preview += "..."
                print(f"      推理: {reasoning_preview}")
        
        return result
    
    def get_supported_images(self, folder_path: str) -> List[Tuple[Path, bool]]:
        """获取文件夹中所有支持的图片及期望结果"""
        from config import SUPPORTED_EXTENSIONS
        folder = Path(folder_path)
        if not folder.exists():
            return []
        
        images = []
        for ext in SUPPORTED_EXTENSIONS:
            for img_path in folder.glob(f"*{ext}"):
                expected = self.get_expected_from_filename(img_path.name)
                if expected is not None:
                    images.append((img_path, expected))
            for img_path in folder.glob(f"*{ext.upper()}"):
                expected = self.get_expected_from_filename(img_path.name)
                if expected is not None:
                    images.append((img_path, expected))
        
        return sorted(images, key=lambda x: x[0].name)
    
    # ============================================================
    # 核心优化逻辑
    # ============================================================
    
    def optimize(self, test_folder: str,
                 user_prompt: str = None,
                 system_prompt: str = None,
                 max_rounds: int = 10,
                 save_history: bool = True,
                 verbose: bool = True) -> Dict:
        """
        执行提示词优化
        
        流程：
        1. 遍历所有测试图片
        2. 遇到第一个错误时，立即停止本轮测试
        3. 分析错误并优化提示词
        4. 从头开始重新测试所有图片
        5. 重复直到全部通过或达到最大轮次
        
        Args:
            test_folder: 测试集文件夹路径
            user_prompt: 初始用户提示词（不提供则使用默认）
            system_prompt: 初始系统提示词（不提供则使用默认）
            max_rounds: 最大优化轮次
            save_history: 是否保存历史记录
            verbose: 是否打印详细信息
        
        Returns:
            dict: 优化结果
        """
        # 初始化
        self.current_user_prompt = user_prompt or self.get_default_user_prompt()
        self.current_system_prompt = system_prompt or self.get_default_system_prompt()
        
        # 获取测试图片
        test_images = self.get_supported_images(test_folder)
        if not test_images:
            return {
                "success": False,
                "error": f"在 {test_folder} 中没有找到有效的测试图片"
            }
        
        print(f"\n{'='*70}")
        print(f"提示词优化器 - {self.get_rule_description()}")
        print(f"{'='*70}")
        print(f"测试图片数: {len(test_images)}")
        print(f"最大优化轮次: {max_rounds}")
        print(f"当前API: {API_TYPE} - {self.api_client.get_model_name()}")
        print(f"{'='*70}")
        
        # 显示测试图片列表
        if verbose:
            print("\n测试图片列表:")
            for img_path, expected in test_images:
                expected_str = "期望:是" if expected else "期望:否"
                print(f"  - {img_path.name} ({expected_str})")
        
        self.round_history = []
        all_passed = False
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n{'#'*70}")
            print(f"第 {round_num} 轮测试")
            print(f"{'#'*70}")
            
            # 记录本轮结果
            round_result = {
                "round": round_num,
                "user_prompt": self.current_user_prompt,
                "system_prompt": self.current_system_prompt,
                "results": [],
                "error": None,
                "all_passed": False
            }
            
            # 遍历所有测试图片，遇到第一个错误就停止
            error_occurred = False
            first_error = None
            
            for idx, (img_path, expected) in enumerate(test_images, 1):
                print(f"\n[{idx}/{len(test_images)}] 测试: {img_path.name}")
                print(f"  期望: {'是' if expected else '否'}")
                
                result = self.test_single_image(str(img_path), expected, verbose=verbose)
                round_result["results"].append(result)
                
                if not result["is_correct"]:
                    # 遇到错误，记录并停止本轮测试
                    error_occurred = True
                    first_error = result
                    print(f"\n  >>> 发现错误，停止本轮测试 <<<")
                    if result.get("reasoning"):
                        reasoning_preview = result["reasoning"][:300]
                        if len(result["reasoning"]) > 300:
                            reasoning_preview += "..."
                        print(f"\n  推理过程:\n{reasoning_preview}")
                    break
            
            # 统计本轮结果（只统计已测试的图片）
            tested_count = len(round_result["results"])
            correct_count = sum(1 for r in round_result["results"] if r.get("is_correct", False))
            accuracy = correct_count / tested_count * 100 if tested_count > 0 else 0
            
            round_result["tested_count"] = tested_count
            round_result["correct_count"] = correct_count
            round_result["accuracy"] = accuracy
            
            print(f"\n{'-'*50}")
            print(f"第 {round_num} 轮结果: {correct_count}/{tested_count} 正确 ({accuracy:.2f}%)")
            
            if not error_occurred:
                # 所有图片都正确
                all_passed = True
                round_result["all_passed"] = True
                print(f"\n[成功] 所有测试通过！提示词优化成功！")
                self.round_history.append(round_result)
                break
            
            # 有错误，分析并优化提示词
            if round_num < max_rounds:
                print(f"\n[优化] 发现错误，分析并优化提示词...")
                
                error_analysis = self.analyze_error(
                    first_error.get("reasoning", ""),
                    first_error.get("expected", False),
                    first_error.get("actual", False),
                    first_error.get("filename", "")
                )
                
                print(f"  错误类型: {error_analysis.get('error_type', 'unknown')}")
                print(f"  置信度: {error_analysis.get('confidence', 0):.0f}%")
                
                # 打印优化策略说明
                add_user = error_analysis.get("add_to_user_prompt", "")
                if add_user:
                    # 提取关键信息
                    if "自行车" in add_user and "局部" in add_user:
                        print(f"  优化策略: 强调自行车局部也算自行车")
                    elif "车牌" in add_user and "检查" in add_user:
                        print(f"  优化策略: 强调检查车牌")
                    elif "判断规则" in add_user:
                        print(f"  优化策略: 强调判断规则")
                    else:
                        preview = add_user.replace('\n', ' ').strip()
                        if len(preview) > 60:
                            preview = preview[:60] + "..."
                        print(f"  优化策略: {preview}")
                
                # 记录优化前的提示词
                optimization_record = {
                    "round": round_num,
                    "error_image": first_error.get("filename"),
                    "error_analysis": error_analysis,
                    "old_user_prompt": self.current_user_prompt,
                    "old_system_prompt": self.current_system_prompt
                }
                
                # 优化提示词
                new_user, new_system = self.optimize_prompts(error_analysis)
                self.current_user_prompt = new_user
                self.current_system_prompt = new_system
                
                optimization_record["new_user_prompt"] = self.current_user_prompt
                optimization_record["new_system_prompt"] = self.current_system_prompt
                self.optimization_history.append(optimization_record)
                
                print(f"\n  已优化提示词，将从头开始重新测试...")
                
                # 重置本轮结果，准备重新开始
                round_result["optimized"] = True
                self.round_history.append(round_result)
            else:
                # 达到最大轮次
                print(f"\n[失败] 达到最大优化轮次({max_rounds})，优化失败")
                round_result["all_passed"] = False
                self.round_history.append(round_result)
        
        # 最终结果
        final_result = {
            "success": all_passed,
            "rounds": len(self.round_history),
            "total_images": len(test_images),
            "final_user_prompt": self.current_user_prompt,
            "final_system_prompt": self.current_system_prompt,
            "round_history": self.round_history,
            "optimization_history": self.optimization_history
        }
        
        # 保存历史记录
        if save_history:
            self._save_optimization_result(test_folder, final_result)
        
        return final_result
    
    def _save_optimization_result(self, test_folder: str, result: Dict):
        """保存优化结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.optimization_dir / f"optimization_{self.get_rule_name()}_{timestamp}.json"
        
        record = {
            "timestamp": timestamp,
            "rule": self.get_rule_name(),
            "test_folder": test_folder,
            "success": result["success"],
            "rounds": result["rounds"],
            "total_images": result["total_images"],
            "final_user_prompt": result["final_user_prompt"],
            "final_system_prompt": result["final_system_prompt"],
            "round_history": [
                {
                    "round": r["round"],
                    "accuracy": r["accuracy"],
                    "correct_count": r["correct_count"],
                    "tested_count": r.get("tested_count", 0),
                    "all_passed": r["all_passed"]
                }
                for r in result["round_history"]
            ],
            "optimization_history": [
                {
                    "round": o["round"],
                    "error_image": o["error_image"],
                    "error_type": o["error_analysis"].get("error_type"),
                    "old_user_prompt_preview": o["old_user_prompt"][:200] if o["old_user_prompt"] else ""
                }
                for o in result["optimization_history"]
            ]
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        print(f"\n[保存] 优化记录已保存: {filename}")
    
    def save_final_prompt(self, accuracy: float = None, test_info: dict = None) -> Path:
        """保存最终优化完成的提示词"""
        from prompt_optimizer import PromptValidator
        return PromptValidator.save_valid_prompt(
            user_prompt=self.current_user_prompt,
            system_prompt=self.current_system_prompt,
            accuracy=accuracy or 100.0,
            test_info=test_info or {},
            api_type=API_TYPE,
            model_name=self.api_client.get_model_name()
        )
    
    def print_summary(self):
        """打印优化摘要"""
        print(f"\n{'='*70}")
        print("优化摘要")
        print(f"{'='*70}")
        print(f"总轮次: {len(self.round_history)}")
        print(f"优化次数: {len(self.optimization_history)}")
        
        if self.round_history:
            final_round = self.round_history[-1]
            print(f"最终准确率: {final_round.get('accuracy', 0):.2f}%")
            print(f"是否通过: {'是' if final_round.get('all_passed', False) else '否'}")
        
        if self.optimization_history:
            print(f"\n优化历史:")
            for opt in self.optimization_history:
                print(f"  第{opt['round']}轮: {opt['error_image']} -> {opt['error_analysis'].get('error_type')}")
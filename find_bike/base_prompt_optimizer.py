# base_prompt_optimizer.py
# ============================================================
# 提示词优化器基类 - 使用大模型优化提示词
# ============================================================

import json
import time
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from api_client import create_api_client
from config import API_TYPE, OLLAMA_CONFIG, ZHIPU_CONFIG, OPENAI_CONFIG, BEDROCK_CONFIG


class BasePromptOptimizer(ABC):
    """
    提示词优化器基类 - 使用大模型优化提示词
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
        pass
    
    @abstractmethod
    def get_rule_description(self) -> str:
        pass
    
    @abstractmethod
    def get_default_system_prompt(self) -> str:
        pass
    
    @abstractmethod
    def get_default_user_prompt(self) -> str:
        pass
    
    @abstractmethod
    def parse_response(self, answer: str) -> Tuple[bool, str]:
        pass
    
    @abstractmethod
    def get_expected_from_filename(self, filename: str) -> Optional[bool]:
        pass
    
    # ============================================================
    # 获取支持的图片（子类可重写）
    # ============================================================
    
    def get_supported_images(self, folder_path: str) -> List[Tuple[Path, bool]]:
        """获取文件夹中所有支持的图片及期望结果（子类可重写）"""
        from config import SUPPORTED_EXTENSIONS
        folder = Path(folder_path)
        if not folder.exists():
            return []
        
        images = []
        for ext in SUPPORTED_EXTENSIONS:
            images.extend(folder.glob(f"*{ext}"))
            images.extend(folder.glob(f"*{ext.upper()}"))
        
        # 去重：按文件名（小写）去重
        seen = set()
        unique_images = []
        for img_path in images:
            key = img_path.name.lower()
            if key not in seen:
                seen.add(key)
                unique_images.append(img_path)
        
        result = []
        for img_path in unique_images:
            expected = self.get_expected_from_filename(img_path.name)
            if expected is not None:
                result.append((img_path, expected))
        
        return sorted(result, key=lambda x: x[0].name)
    
    # ============================================================
    # 大模型优化提示词
    # ============================================================
    
    def llm_optimize_prompts(self, 
                              current_user_prompt: str,
                              current_system_prompt: str,
                              failed_image_path: str,
                              expected: str,
                              actual: str,
                              reasoning: str,
                              use_chinese: bool = True) -> Tuple[str, str]:
        """
        使用大模型来优化提示词
        """
        
        if use_chinese:
            # 正确的规则定义
            CORRECT_RULE = """【正确的判断规则】
- 条件成立（有自行车且无车牌）→ 回答"是"
- 条件不成立（无自行车、有车牌、无法确定）→ 回答"否"

注意：
1. 自行车包括完整自行车或局部（车轮、车架、链条、座垫、车把等）
2. 车牌包括任何带数字/字母的矩形牌子
3. 品牌贴纸、尺寸标签、说明书不算车牌"""
            
            optimizer_prompt = f"""你是一个提示词优化专家。当前提示词导致模型判断错误，请修正。

{CORRECT_RULE}

## 当前提示词
【用户提示词】
{current_user_prompt}

【系统提示词】
{current_system_prompt}

## 错误信息
- 测试图片: {Path(failed_image_path).name}
- 期望结果: {expected}
- 模型实际输出: {actual}
- 模型推理过程: {reasoning[:300] if reasoning else '无推理过程'}

## 分析
期望结果是"{expected}"，模型输出"{actual}"。
请分析模型为什么判断错误，然后输出优化后的提示词。

## 输出格式（必须严格遵守）
用户提示词：
[优化后的用户提示词]

系统提示词：
[优化后的系统提示词，必须包含上述正确的判断规则]

注意：
1. 系统提示词必须包含正确的判断规则
2. 输出格式要求：模型必须输出【分析】...【结论】是/否
3. 不要输出其他任何内容"""
            
            try:
                success, answer, reasoning_text, elapsed = self.api_client.chat_with_image(
                    failed_image_path,
                    optimizer_prompt,
                    "请优化提示词，必须使用正确的判断规则"
                )
                
                if not success:
                    print(f"  [警告] 大模型优化失败: {answer}")
                    return current_user_prompt, current_system_prompt
                
                print(f"  [大模型优化] 耗时: {elapsed:.2f}s")
                
                if not answer or len(answer.strip()) == 0:
                    print(f"  [警告] 大模型返回空内容")
                    return current_user_prompt, current_system_prompt
                
                # 打印原始返回内容
                print(f"\n  [调试] 大模型返回:")
                print("-" * 40)
                print(answer)
                print("-" * 40)
                
                # 解析优化后的提示词
                new_user = current_user_prompt
                new_system = current_system_prompt
                
                # 查找用户提示词
                user_match = re.search(r'用户提示词[：:]\s*\n?(.*?)(?=\n系统提示词[：:]|\Z)', answer, re.DOTALL)
                if user_match:
                    user_content = user_match.group(1).strip()
                    if user_content and len(user_content) > 5:
                        new_user = user_content
                        print(f"  [解析] 提取到用户提示词")
                
                # 查找系统提示词
                system_match = re.search(r'系统提示词[：:]\s*\n?(.*?)(?=\Z)', answer, re.DOTALL)
                if system_match:
                    system_content = system_match.group(1).strip()
                    if system_content and len(system_content) > 20:
                        new_system = system_content
                        print(f"  [解析] 提取到系统提示词")
                
                # 如果解析失败，尝试直接使用整个回答
                if new_user == current_user_prompt and new_system == current_system_prompt:
                    if len(answer) > 20 and len(answer) < 2000:
                        new_user = answer
                        print(f"  [警告] 解析失败，使用完整回答作为用户提示词")
                
                print(f"\n  [结果] 优化后的用户提示词:\n{new_user}")
                print(f"\n  [结果] 优化后的系统提示词:\n{new_system}")
                
                return new_user, new_system
                
            except Exception as e:
                print(f"  [警告] 大模型优化异常: {e}")
                import traceback
                traceback.print_exc()
                return current_user_prompt, current_system_prompt
        
        else:
            return current_user_prompt, current_system_prompt
    
    # ============================================================
    # 核心方法
    # ============================================================
    
    def call_model(self, image_path: str, system_prompt: str, user_prompt: str) -> Tuple[bool, str, str, float]:
        """调用大模型"""
        return self.api_client.chat_with_image(image_path, system_prompt, user_prompt)
    
    def test_single_image(self, image_path: str, expected: bool, 
                          verbose: bool = False) -> Dict:
        """测试单张图片"""
        filename = Path(image_path).name
        success, answer, reasoning, elapsed = self.call_model(
            image_path, self.current_system_prompt, self.current_user_prompt
        )
        
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
                print(f"      推理: {result['reasoning']}")
        
        return result
    
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
        """
        # 初始化
        self.current_user_prompt = user_prompt or self.get_default_user_prompt()
        self.current_system_prompt = system_prompt or self.get_default_system_prompt()
        
        # 获取测试图片（使用子类重写的方法）
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
        print(f"优化方式: 大模型智能优化")
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
            
            print(f"\n[当前用户提示词]:\n{self.current_user_prompt}")
            print(f"\n[当前系统提示词]:\n{self.current_system_prompt}")
            
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
                    error_occurred = True
                    first_error = result
                    print(f"\n  >>> 发现错误，停止本轮测试 <<<")
                    if result.get("reasoning"):
                        print(f"\n  推理过程:\n{result['reasoning']}")
                    break
            
            # 统计本轮结果
            tested_count = len(round_result["results"])
            correct_count = sum(1 for r in round_result["results"] if r.get("is_correct", False))
            accuracy = correct_count / tested_count * 100 if tested_count > 0 else 0
            
            round_result["tested_count"] = tested_count
            round_result["correct_count"] = correct_count
            round_result["accuracy"] = accuracy
            
            print(f"\n{'-'*50}")
            print(f"第 {round_num} 轮结果: {correct_count}/{tested_count} 正确 ({accuracy:.2f}%)")
            
            if not error_occurred:
                all_passed = True
                round_result["all_passed"] = True
                print(f"\n[成功] 所有测试通过！提示词优化成功！")
                self.round_history.append(round_result)
                break
            
            # 有错误，使用大模型优化提示词
            if round_num < max_rounds:
                print(f"\n[优化] 发现错误，正在使用大模型优化提示词...")
                
                # 打印错误详情
                print(f"\n  [错误详情]")
                print(f"    图片: {first_error.get('filename')}")
                print(f"    期望: {'是' if first_error.get('expected') else '否'}")
                print(f"    实际: {'是' if first_error.get('actual') else '否'}")
                print(f"    推理过程: {first_error.get('reasoning', '')}")
                
                # 记录优化前的提示词
                optimization_record = {
                    "round": round_num,
                    "error_image": first_error.get("filename"),
                    "old_user_prompt": self.current_user_prompt,
                    "old_system_prompt": self.current_system_prompt
                }
                
                # 使用大模型优化
                new_user, new_system = self.llm_optimize_prompts(
                    self.current_user_prompt,
                    self.current_system_prompt,
                    str(Path(test_folder) / first_error.get("filename")),
                    "是" if first_error.get("expected") else "否",
                    "是" if first_error.get("actual") else "否",
                    first_error.get("reasoning", ""),
                    use_chinese=True
                )
                
                # 检查提示词是否有变化
                if new_user == self.current_user_prompt and new_system == self.current_system_prompt:
                    print(f"\n  [警告] 提示词未变化，停止优化")
                    round_result["all_passed"] = False
                    self.round_history.append(round_result)
                    break
                
                # 更新提示词
                self.current_user_prompt = new_user
                self.current_system_prompt = new_system
                
                optimization_record["new_user_prompt"] = self.current_user_prompt
                optimization_record["new_system_prompt"] = self.current_system_prompt
                self.optimization_history.append(optimization_record)
                
                print(f"\n  已使用大模型优化提示词，将从头开始重新测试...")
                
                round_result["optimized"] = True
                self.round_history.append(round_result)
            else:
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
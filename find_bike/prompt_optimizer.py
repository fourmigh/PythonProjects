# prompt_optimizer.py
# ============================================================
# 提示词优化器和验证器
# ============================================================

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PromptOptimizer:
    """根据推理过程自动优化提示词"""
    
    def __init__(self, save_optimizations: bool = True):
        self.error_patterns = {
            "false_positive": {
                "keywords": ["white rectangular", "tag", "sticker", "label", "白色矩形", "标签", "贴纸", "品牌贴纸", "尺寸标签"],
                "add_to_prompt": "\n\n注意：品牌贴纸、尺寸标签、说明书等不算车牌，请忽略它们。",
                "modify_system": "请忽略车辆上的品牌贴纸、尺寸标签、说明书等非官方车牌物品。"
            },
            "false_negative": {
                "keywords": ["no license plate", "没有车牌", "not visible", "看不到", "无法识别"],
                "add_to_prompt": "\n\n请仔细检查整张图片，即使车牌不清晰、角度倾斜、部分被遮挡，也认为有车牌。",
                "modify_system": "请仔细检查图片中的车辆前后部位，即使不清晰、倾斜、遮挡，只要看起来像车牌就认为有。"
            },
            "location_error": {
                "keywords": ["below the bike", "separate object", "自行车下方", "背景中", "旁边", "not on the bicycle"],
                "add_to_prompt": "\n\n请注意：只要图片中任何位置有车牌，都算有车牌，不限于自行车上。",
                "modify_system": "请检查整张图片的任何位置，不限于自行车上。只要图片中有车牌，就认为有车牌。"
            },
            "no_bicycle": {
                "keywords": ["no bicycle", "没有自行车", "car", "汽车", "motorcycle"],
                "add_to_prompt": "\n\n请仔细确认图片中是否有自行车。自行车有两个轮子、车架、车把、座垫。",
                "modify_system": "请仔细识别图片中是否有自行车。自行车通常有两个轮子、车架、车把和座垫。"
            }
        }
        self.optimization_history = []
        self.save_optimizations = save_optimizations
        self.optimization_dir = Path("optimization_history")
        if save_optimizations:
            self.optimization_dir.mkdir(exist_ok=True)
    
    def analyze_error(self, reasoning: str, expected: str, actual: str) -> Dict:
        reasoning_lower = reasoning.lower()
        best_match = None
        best_score = 0
        
        for error_type, pattern in self.error_patterns.items():
            found = [kw for kw in pattern["keywords"] if kw.lower() in reasoning_lower]
            if found:
                score = len(found) / len(pattern["keywords"]) * 100
                if score > best_score:
                    best_score = score
                    best_match = error_type
        
        if expected == "是" and actual == "否" and best_match is None:
            best_match = "false_negative"
        elif expected == "否" and actual == "是" and best_match is None:
            best_match = "false_positive"
        
        error_analysis = {
            "error_type": best_match or "unknown",
            "confidence": min(best_score, 95) if best_match else 0,
            "reason": self._get_reason(best_match, actual, expected),
            "add_to_prompt": self.error_patterns.get(best_match, {}).get("add_to_prompt", ""),
            "modify_system": self.error_patterns.get(best_match, {}).get("modify_system", "")
        }
        return error_analysis
    
    def _get_reason(self, error_type: str, actual: str, expected: str) -> str:
        reasons = {
            "false_positive": f"模型误将非车牌物品识别为车牌（实际:{actual}, 期望:{expected}）",
            "false_negative": f"模型没有检测到存在的车牌（实际:{actual}, 期望:{expected}）",
            "location_error": "模型认为车牌位置不正确",
            "no_bicycle": "模型没有识别出自行车",
            "unknown": "无法确定具体错误原因"
        }
        return reasons.get(error_type, "未知错误")
    
    def generate_optimized_prompts(self, user_prompt: str, system_prompt: str,
                                    reasoning: str, expected: str, actual: str,
                                    image_path: str = None) -> Tuple[str, str, Dict]:
        error = self.analyze_error(reasoning, expected, actual)
        
        new_user = user_prompt
        new_system = system_prompt
        
        if error.get("add_to_prompt") and error["add_to_prompt"] not in new_user:
            new_user += error["add_to_prompt"]
        
        if error.get("modify_system") and error["modify_system"] not in new_system:
            new_system = new_system.rstrip() + "\n\n" + error["modify_system"]
        
        optimization_record = {
            "timestamp": datetime.now().isoformat(),
            "image_path": image_path,
            "original_user_prompt": user_prompt,
            "original_system_prompt": system_prompt,
            "new_user_prompt": new_user,
            "new_system_prompt": new_system,
            "error_analysis": error,
            "expected": expected,
            "actual": actual
        }
        self.optimization_history.append(optimization_record)
        
        if self.save_optimizations:
            self._save_optimization_record(optimization_record)
        
        return new_user, new_system, error
    
    def _save_optimization_record(self, record: Dict):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.optimization_dir / f"optimization_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"  [保存] 优化记录已保存: {filename}")
    
    def save_final_prompts(self, user_prompt: str, system_prompt: str, 
                           accuracy: float = None, test_info: dict = None,
                           api_type: str = None, model_name: str = None) -> Path:
        from prompt_optimizer import PromptValidator
        return PromptValidator.save_valid_prompt(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            accuracy=accuracy or 100.0,
            test_info=test_info or {},
            api_type=api_type,
            model_name=model_name
        )
    
    def print_optimization_summary(self):
        print("\n" + "=" * 60)
        print("优化摘要")
        print(f"总优化次数: {len(self.optimization_history)}")
        for i, hist in enumerate(self.optimization_history[-5:], 1):
            error = hist["error_analysis"]
            print(f"\n{i}. {hist['timestamp'][:19]}")
            print(f"   错误类型: {error['error_type']}")
            print(f"   置信度: {error['confidence']:.0%}")


class PromptValidator:
    """提示词验证器 - 管理有效提示词的验证、保存和加载"""
    
    VALID_PROMPTS_DIR = Path("valid_prompts")
    
    @classmethod
    def get_valid_prompts_dir(cls) -> Path:
        cls.VALID_PROMPTS_DIR.mkdir(exist_ok=True)
        return cls.VALID_PROMPTS_DIR
    
    @classmethod
    def save_valid_prompt(cls, user_prompt: str, system_prompt: str, accuracy: float,
                          test_info: dict = None, api_type: str = None, model_name: str = None) -> Path:
        prompts_dir = cls.get_valid_prompts_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_file = prompts_dir / f"prompt_{timestamp}.json"
        data = {
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "accuracy": accuracy,
            "api_type": api_type,
            "model_name": model_name,
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "test_info": test_info or {}
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        txt_file = prompts_dir / f"prompt_{timestamp}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(f"# 有效提示词\n")
            f.write(f"# 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 准确率: {accuracy:.2f}%\n")
            f.write(f"# API类型: {api_type}\n")
            f.write(f"# 模型: {model_name}\n")
            f.write(f"\n# ===== 系统提示词 =====\n")
            f.write(system_prompt)
            f.write(f"\n\n# ===== 用户提示词 =====\n")
            f.write(user_prompt)
        
        print(f"\n[保存] 优化后的提示词已保存!")
        print(f"       JSON: {json_file}")
        print(f"       TXT: {txt_file}")
        return json_file
    
    @classmethod
    def list_valid_prompts(cls) -> List[Dict]:
        prompts_dir = cls.get_valid_prompts_dir()
        prompts = []
        for json_file in sorted(prompts_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    prompts.append({
                        "id": data.get("timestamp", json_file.stem.replace("prompt_", "")),
                        "datetime": data.get("datetime", ""),
                        "accuracy": data.get("accuracy", 0),
                        "api_type": data.get("api_type", "unknown"),
                        "model_name": data.get("model_name", "unknown")
                    })
            except:
                continue
        return prompts
    
    @classmethod
    def load_valid_prompt(cls, prompt_id: str = None) -> Optional[Dict]:
        prompts_dir = cls.get_valid_prompts_dir()
        json_files = sorted(prompts_dir.glob("*.json"))
        if not json_files:
            return None
        
        if prompt_id:
            target = prompts_dir / f"prompt_{prompt_id}.json"
            if target.exists():
                json_files = [target]
        
        with open(json_files[-1], "r", encoding="utf-8") as f:
            return json.load(f)
    
    @classmethod
    def get_active_prompt(cls, auto_select: bool = True) -> Optional[Dict]:
        prompts = cls.list_valid_prompts()
        if not prompts:
            return None
        if len(prompts) == 1 and auto_select:
            return cls.load_valid_prompt(prompts[0]['id'])
        return cls.select_prompt_interactive()
    
    @classmethod
    def select_prompt_interactive(cls) -> Optional[Dict]:
        prompts = cls.list_valid_prompts()
        if not prompts:
            print("[提示] 没有找到任何已保存的有效提示词")
            return None
        
        print("\n" + "=" * 60)
        print("已保存的有效提示词列表:")
        for i, p in enumerate(prompts, 1):
            print(f"\n  {i}. ID: {p['id']}")
            print(f"     时间: {p['datetime']}")
            print(f"     准确率: {p['accuracy']:.2f}%")
            print(f"     API: {p['api_type']} - {p['model_name']}")
        
        while True:
            try:
                choice = input("\n请选择编号 (输入0退出): ").strip()
                if choice == '0':
                    return None
                idx = int(choice) - 1
                if 0 <= idx < len(prompts):
                    return cls.load_valid_prompt(prompts[idx]['id'])
                print(f"  请输入 1-{len(prompts)} 之间的数字")
            except ValueError:
                print("  输入无效，请输入数字编号")


class AutoOptimizer:
    """自动优化器：自动优化提示词并保存结果"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.optimizer = PromptOptimizer(save_optimizations=True)
        self.retry_count = 0
        self.best_user_prompt = None
        self.best_system_prompt = None
    
    def reset(self):
        self.retry_count = 0
    
    def optimize_with_feedback(self, user_prompt: str, system_prompt: str,
                               reasoning: str, expected: str, actual: str,
                               image_path: str = None) -> Tuple[str, str, Dict]:
        self.retry_count += 1
        new_user, new_system, error = self.optimizer.generate_optimized_prompts(
            user_prompt, system_prompt, reasoning, expected, actual, image_path
        )
        self.best_user_prompt = new_user
        self.best_system_prompt = new_system
        return new_user, new_system, error
    
    def save_final_prompt(self, accuracy: float, test_info: dict = None,
                          api_type: str = None, model_name: str = None) -> Path:
        if self.best_user_prompt and self.best_system_prompt:
            return self.optimizer.save_final_prompts(
                self.best_user_prompt,
                self.best_system_prompt,
                accuracy,
                test_info,
                api_type,
                model_name
            )
        return None
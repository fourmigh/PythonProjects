# bicycle_rule.py
# ============================================================
# 业务规则：判断图片中是否有自行车且无车牌
# ============================================================

import time
from pathlib import Path
from typing import Dict, Tuple, Optional

from config import (
    CURRENT_CONFIG, SUPPORTED_EXTENSIONS,
    DEFAULT_CSV_FILENAME, API_TYPE
)
from api_client import create_api_client
from prompt_optimizer import PromptValidator
from base_prompt_optimizer import BasePromptOptimizer


# ============================================================
# API客户端（业务层使用）
# ============================================================
def get_api_client():
    from config import OLLAMA_CONFIG, ZHIPU_CONFIG, OPENAI_CONFIG, BEDROCK_CONFIG
    if API_TYPE == 'ollama':
        return create_api_client('ollama', OLLAMA_CONFIG)
    elif API_TYPE == 'zhipu':
        return create_api_client('zhipu', ZHIPU_CONFIG)
    elif API_TYPE == 'openai':
        return create_api_client('openai', OPENAI_CONFIG)
    elif API_TYPE == 'bedrock':
        return create_api_client('bedrock', BEDROCK_CONFIG)
    raise ValueError(f"不支持的API类型: {API_TYPE}")


API_CLIENT = get_api_client()


# ============================================================
# 核心业务函数
# ============================================================
def get_expected_from_filename(filename: str) -> Optional[bool]:
    """根据文件名获取期望结果"""
    if not filename:
        return None
    first_char = filename[0]
    if first_char == '是':
        return True
    elif first_char == '否':
        return False
    return None


def get_supported_images_from_folder(folder_path: str) -> list:
    """获取文件夹中所有支持的图片（已去重）"""
    folder = Path(folder_path)
    if not folder.exists():
        return []
    
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(folder.glob(f"*{ext}"))
        images.extend(folder.glob(f"*{ext.upper()}"))
    
    # 去重：按文件名（小写）去重
    seen = set()
    unique = []
    for img in images:
        key = img.name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(img)
    
    return sorted(unique)


def parse_bicycle_response(answer: str) -> Tuple[bool, str]:
    """解析模型回答，返回 (是否符合条件, 推理过程)"""
    reasoning = ""
    
    # 提取推理过程
    if "【分析】" in answer and "【结论】" in answer:
        parts = answer.split("【结论】")
        reasoning = parts[0].replace("【分析】", "").strip()
    
    # 提取结论（中文）
    if "【结论】是" in answer:
        return True, reasoning
    elif "【结论】否" in answer:
        return False, reasoning
    
    # 提取结论（英文）
    if "【Conclusion】YES" in answer.upper():
        return True, reasoning
    elif "【Conclusion】NO" in answer.upper():
        return False, reasoning
    
    # 清理标点符号
    answer_clean = answer.strip()
    while answer_clean and answer_clean[-1] in '。！？,.!?；;':
        answer_clean = answer_clean[:-1]
    answer_clean = answer_clean.strip()
    
    # 直接判断
    if answer_clean == "是" or answer_clean.upper() == "YES":
        return True, reasoning
    elif answer_clean == "否" or answer_clean.upper() == "NO":
        return False, reasoning
    elif "是" in answer_clean and "否" not in answer_clean:
        return True, reasoning
    elif "YES" in answer_clean.upper() and "NO" not in answer_clean.upper():
        return True, reasoning
    else:
        return False, reasoning


def call_model(image_path: str, system_prompt: str, user_prompt: str) -> tuple:
    """调用大模型"""
    return API_CLIENT.chat_with_image(image_path, system_prompt, user_prompt)


def has_bicycle_registration_plate(image_path: str, system_prompt: str, user_prompt: str, 
                                    verbose: bool = False, debug: bool = False) -> tuple:
    """判断图片中是否有自行车且无车牌"""
    success, answer, reasoning, elapsed = call_model(image_path, system_prompt, user_prompt)
    
    if debug:
        print(f"\n  [API原始返回]")
        print(f"    success: {success}")
        print(f"    answer: {answer}")
        print(f"    reasoning: {reasoning if reasoning else 'None'}")
        print(f"    elapsed: {elapsed:.2f}s")
    
    if not success:
        return False, False, elapsed, answer, reasoning
    
    is_allowed, reasoning_from_answer = parse_bicycle_response(answer)
    
    if not reasoning_from_answer and reasoning:
        reasoning_from_answer = reasoning
    
    if verbose:
        print(f"\n  [模型完整回答]")
        print("-" * 40)
        print(answer)
        print("-" * 40)
        if reasoning_from_answer:
            print(f"\n  [推理过程]")
            print("-" * 40)
            print(reasoning_from_answer)
            print("-" * 40)
    
    return True, is_allowed, elapsed, answer, reasoning_from_answer


# ============================================================
# 单张图片检测
# ============================================================
def process_single_image(image_path: str, system_prompt: str, user_prompt: str,
                         verbose: bool = True, debug: bool = False) -> dict:
    """处理单张图片"""
    if not Path(image_path).exists():
        print(f"[错误] 图片不存在")
        return None
    
    filename = Path(image_path).name
    expected = get_expected_from_filename(filename)
    
    print(f"\n文件: {filename}")
    print(f"  模型: {API_CLIENT.get_model_name()}")
    if expected is not None:
        expected_str = "允许" if expected else "不允许"
        print(f"  期望: {expected_str}")
    
    success, is_allowed, elapsed, answer, reasoning = has_bicycle_registration_plate(
        image_path, system_prompt, user_prompt, verbose, debug
    )
    
    if success:
        status = "[允许]" if is_allowed else "[不允许]"
        print(f"   {status} | 耗时: {elapsed:.2f}秒")
        
        if expected is not None:
            if is_allowed == expected:
                print(f"   [验证] 正确 ✓")
            else:
                print(f"   [验证] 错误 ✗")
                if reasoning:
                    copy_choice = input("   复制推理过程到剪贴板？(y/n): ").strip().lower()
                    if copy_choice in ['y', 'yes', '是']:
                        copy_to_clipboard(reasoning)
    else:
        print(f"   [检测失败] {answer}")
    
    return {"filename": filename, "is_allowed": is_allowed if success else None, "success": success}


def single_image_mode(system_prompt: str, user_prompt: str, debug: bool = False):
    """单张图片检测模式"""
    print("\n[模式] 单张图片检测")
    print(f"[API] {API_TYPE.upper()} - {API_CLIENT.get_model_name()}")
    
    current_folder = None
    image_files = None
    
    while True:
        if current_folder is None:
            folder = input("\n请输入图片文件夹路径: ").strip()
            if not folder:
                continue
            if not Path(folder).exists():
                print(f"  文件夹不存在")
                continue
            image_files = get_supported_images_from_folder(folder)
            if not image_files:
                print(f"  没有找到支持的图片")
                continue
            current_folder = folder
            display_image_list(image_files)
        
        selected, need_reinput = select_image_from_folder(image_files)
        if need_reinput:
            current_folder = None
            continue
        if selected is None:
            break
        
        print(f"\n[检测] {selected.name}")
        print("=" * 60)
        process_single_image(str(selected), system_prompt, user_prompt, verbose=True, debug=debug)
        print("=" * 60)


# ============================================================
# 批量检测
# ============================================================
def batch_detection_mode(folder_path: str, system_prompt: str, user_prompt: str,
                         stop_on_failure: bool = True, stop_on_validation_error: bool = True,
                         debug: bool = False) -> tuple:
    """批量检测"""
    image_files = get_supported_images_from_folder(folder_path)
    if not image_files:
        print(f"[错误] 没有找到图片")
        return [], False, "", -1
    
    print(f"[信息] 找到 {len(image_files)} 张图片")
    print(f"[时间] 开始: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results, correct, valid = [], 0, 0
    stopped, stop_reason, stop_index = False, "", -1
    
    for idx, img in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}] {img.name}")
        expected = get_expected_from_filename(img.name)
        if expected is not None:
            expected_str = "允许" if expected else "不允许"
            print(f"  期望: {expected_str}")
        
        success, is_allowed, elapsed, answer, reasoning = has_bicycle_registration_plate(
            str(img), system_prompt, user_prompt, verbose=False, debug=debug
        )
        
        if not success:
            print(f"   [检测失败]")
            if stop_on_failure:
                stopped, stop_reason, stop_index = True, f"检测失败: {img.name}", idx
                break
            continue
        
        status = "[允许]" if is_allowed else "[不允许]"
        print(f"   {status} | 耗时: {elapsed:.2f}秒")
        
        # 打印完整的模型回答和推理过程（不截断）
        if answer:
            print(f"   [模型回答]: {answer}")
        if reasoning:
            print(f"   [推理过程]: {reasoning}")
        
        if expected is not None:
            if is_allowed == expected:
                correct += 1
                print(f"   [验证] 正确 ✓")
            else:
                print(f"   [验证] 错误 ✗")
                if stop_on_validation_error:
                    if reasoning:
                        copy_to_clipboard(reasoning)
                    stopped, stop_reason, stop_index = True, f"验证错误: {img.name}", idx
                    break
            valid += 1
        
        results.append({"filename": img.name, "is_allowed": is_allowed, "success": True})
    
    print("\n" + "=" * 70)
    if stopped:
        print(f"[停止] {stop_reason} (第{stop_index}张)")
    else:
        acc = correct / valid * 100 if valid > 0 else 0
        print(f"[完成] 准确率: {acc:.2f}% ({correct}/{valid})")
    return results, stopped, stop_reason, stop_index


# ============================================================
# 验证并保存提示词
# ============================================================
def validate_and_save_prompts(system_prompt: str = None, user_prompt: str = None) -> bool:
    """验证并保存提示词"""
    print("\n" + "=" * 60)
    print("          验证模式 - 创建有效提示词")
    print("=" * 60)
    print("\n测试集要求: 文件名以'是'或'否'开头")
    print("  是_xxx.jpg - 正例（有自行车且无车牌，期望'是'）")
    print("  否_xxx.jpg - 负例（其他情况，期望'否'）")
    
    test_folder = input("\n请输入测试集文件夹路径: ").strip()
    if not Path(test_folder).exists():
        print(f"[错误] 文件夹不存在")
        return False
    
    image_files = get_supported_images_from_folder(test_folder)
    expected_results = {}
    for img in image_files:
        exp = get_expected_from_filename(img.name)
        if exp is not None:
            expected_results[str(img)] = exp
    
    if not expected_results:
        print("[错误] 没有找到以'是'或'否'开头的图片")
        return False
    
    pos = sum(1 for v in expected_results.values() if v)
    neg = len(expected_results) - pos
    print(f"\n[信息] 正例: {pos}张, 负例: {neg}张")
    
    # 获取提示词
    if system_prompt is None or user_prompt is None:
        print("\n请输入系统提示词 (回车使用默认):")
        system = input().strip()
        if not system:
            system = CURRENT_CONFIG["SYSTEM_PROMPT"]
        print("\n请输入用户提示词 (回车使用默认):")
        user = input().strip()
        if not user:
            user = CURRENT_CONFIG["USER_QUESTION"]
    else:
        system = system_prompt
        user = user_prompt
        print(f"\n使用当前提示词:")
        print(f"  用户提示词:\n{user}")
        print(f"  系统提示词:\n{system}")
    
    print("\n开始验证...")
    correct = 0
    errors = []
    
    for img_path, expected in expected_results.items():
        exp_str = "是" if expected else "否"
        print(f"\n检测: {Path(img_path).name} (期望:{exp_str})")
        
        success, answer, reasoning, elapsed = call_model(img_path, system, user)
        if not success:
            print(f"  失败: {answer}")
            continue
        
        print(f"  模型回答:\n{answer}")
        if reasoning:
            print(f"  推理过程:\n{reasoning}")
        
        actual, _ = parse_bicycle_response(answer)
        
        act_str = "是" if actual else "否"
        if actual == expected:
            correct += 1
            print(f"  结果: {act_str} ✓")
        else:
            print(f"  结果: {act_str} ✗")
            errors.append({"file": Path(img_path).name, "expected": exp_str, "actual": act_str})
    
    acc = correct / len(expected_results) * 100
    print(f"\n[结果] 准确率: {acc:.2f}% ({correct}/{len(expected_results)})")
    
    if errors:
        print(f"\n错误: {len(errors)}个")
        for e in errors:
            print(f"  - {e['file']}: 期望{e['expected']}, 实际{e['actual']}")
    
    if acc >= 95:
        print(f"\n[通过] 准确率 {acc:.2f}% >= 95%")
        if input("保存此提示词？(y/n): ").lower() in ['y', 'yes', '是']:
            PromptValidator.save_valid_prompt(user, system, acc, {"total": len(expected_results), "correct": correct},
                                              API_TYPE, API_CLIENT.get_model_name())
            print("\n[成功] 提示词已保存！")
            return True
    else:
        print(f"\n[不通过] 准确率 {acc:.2f}% < 95%，请优化后重试")
    
    return False


# ============================================================
# 辅助UI函数
# ============================================================
def copy_to_clipboard(text: str, max_length: int = 10000):
    try:
        import pyperclip
        if len(text) > max_length:
            text = text[:max_length] + "\n\n... (已截断)"
        pyperclip.copy(text)
        print(f"  [剪贴板] 已复制")
    except ImportError:
        pass
    except Exception as e:
        print(f"  [剪贴板] 复制失败: {e}")


def display_image_list(image_files: list):
    print("\n" + "-" * 60)
    print("图片列表:")
    for idx, img in enumerate(image_files, 1):
        exp = get_expected_from_filename(img.name)
        hint = " [期望: 允许]" if exp is True else " [期望: 不允许]" if exp is False else ""
        print(f"  {idx}. {img.name}{hint}")
    print("-" * 60)


def select_image_from_folder(image_files: list) -> tuple:
    while True:
        print("\n操作: 输入编号检测 | 'r' 重新输入 | 'q' 返回主菜单")
        choice = input("请输入: ").strip().lower()
        if choice == 'q':
            return None, False
        if choice == 'r':
            return None, True
        try:
            num = int(choice)
            if 1 <= num <= len(image_files):
                return image_files[num - 1], False
            print(f"  请输入 1-{len(image_files)}")
        except ValueError:
            print("  输入无效")


def export_results_to_csv(results: list, output_file: str = DEFAULT_CSV_FILENAME):
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["文件名", "是否允许", "检测成功"])
        for r in results:
            writer.writerow([r['filename'], "允许" if r['is_allowed'] else "不允许", r['success']])
    print(f"[导出] {output_file}")


# ============================================================
# 优化器类（继承基类）
# ============================================================
class BicycleNoPlateOptimizer(BasePromptOptimizer):
    """自行车无车牌判断优化器"""
    
    def get_rule_name(self) -> str:
        return "bicycle_no_plate"
    
    def get_rule_description(self) -> str:
        return "Determine if there is a bicycle without a license plate in the image"
    
    def get_default_system_prompt(self) -> str:
        """默认系统提示词（英文）"""
        return """You are an image analysis assistant. Follow these rules:

First: Check if there is a bicycle in the image (including bicycle parts such as wheels, frame, chain, seat, handlebars, etc.)

Second: Check if the bicycle has a license plate (any rectangular plate with numbers/letters)

Third: Output the conclusion according to these rules:
- If [has bicycle] AND [no license plate] → answer "YES"
- If [no bicycle] OR [has license plate] OR [uncertain] → answer "NO"

Important: Even if you see a license plate, answer "NO"!

Output format: 【Analysis】...【Conclusion】YES/NO

Examples:
【Analysis】There is a blue bicycle in the image. No license plate found on the bicycle.
【Conclusion】YES

【Analysis】There is a black bicycle with a white license plate "ABC123" on the frame.
【Conclusion】NO

【Analysis】This is a car, not a bicycle.
【Conclusion】NO"""
    
    def get_default_user_prompt(self) -> str:
        """默认用户提示词（英文）"""
        return "Please analyze this image: Is there a bicycle (including bicycle parts) with NO license plate?"
    
    def parse_response(self, answer: str) -> Tuple[bool, str]:
        """解析模型回答"""
        return parse_bicycle_response(answer)
    
    def get_expected_from_filename(self, filename: str) -> Optional[bool]:
        """根据文件名获取期望结果"""
        return get_expected_from_filename(filename)
    
    def get_supported_images(self, folder_path: str) -> list:
        """获取支持的图片列表"""
        from bicycle_rule import get_supported_images_from_folder
        
        image_files = get_supported_images_from_folder(folder_path)
        
        result = []
        for img_path in image_files:
            expected = self.get_expected_from_filename(img_path.name)
            if expected is not None:
                result.append((img_path, expected))
        
        return sorted(result, key=lambda x: x[0].name)
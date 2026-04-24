# find_plate_cn.py
# ============================================================
# 自行车检测工具 - 主程序
# 只能使用经过验证并保存的有效提示词
# ============================================================

import time
import sys
from pathlib import Path

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

from config import (
    CHINESE_CONFIG, ENGLISH_CONFIG, YES_CHARS, NO_CHARS, SUPPORTED_EXTENSIONS,
    DEFAULT_STOP_ON_FAILURE, DEFAULT_STOP_ON_VALIDATION_ERROR,
    DEFAULT_CSV_FILENAME, API_TYPE, OLLAMA_CONFIG, ZHIPU_CONFIG,
    OPENAI_CONFIG, BEDROCK_CONFIG, validate_config
)
from api_client import create_api_client
from prompt_optimizer import PromptValidator

# 导入 bicycle_rule 中的解析函数
from bicycle_rule import parse_bicycle_response, get_bicycle_expected_from_filename


# 验证配置
if not validate_config():
    print("\n[错误] 配置验证失败，程序退出")
    sys.exit(1)


def get_api_client():
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
USE_CHINESE = True
SYSTEM_PROMPT = ""
USER_QUESTION = ""
DEBUG_API_RESPONSE = True  # 设为 False 可关闭调试输出

def copy_to_clipboard(text: str, max_length: int = 10000):
    if not text or not HAS_PYPERCLIP:
        return
    if len(text) > max_length:
        text = text[:max_length] + "\n\n... (已截断)"
    try:
        pyperclip.copy(text)
        print(f"  [剪贴板] 已复制")
    except Exception as e:
        print(f"  [剪贴板] 复制失败: {e}")


def get_expected_from_filename(filename: str) -> bool:
    """复用 bicycle_rule 的函数"""
    return get_bicycle_expected_from_filename(filename)


def get_supported_images_from_folder(folder_path: str) -> list:
    folder = Path(folder_path)
    if not folder.exists():
        return []
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(folder.glob(f"*{ext}"))
        images.extend(folder.glob(f"*{ext.upper()}"))
    return sorted(images)


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


def has_bicycle_registration_plate(image_path: str, verbose: bool = False) -> tuple:
    success, answer, reasoning, elapsed = API_CLIENT.chat_with_image(
        image_path, SYSTEM_PROMPT, USER_QUESTION
    )
    
    # 调试：打印原始返回数据
    if DEBUG_API_RESPONSE:
        print(f"\n  [API原始返回]")
        print(f"    success: {success}")
        print(f"    answer: {repr(answer)}")
        print(f"    reasoning: {repr(reasoning) if reasoning else 'None'}")
        print(f"    elapsed: {elapsed:.2f}s")
    
    if not success:
        return False, False, elapsed, answer, reasoning
    
    # 使用 bicycle_rule 中的解析函数
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


def process_single_image(image_path: str, verbose: bool = True):
    """处理单张图片"""
    if not Path(image_path).exists():
        print(f"[错误] 图片不存在")
        return None
    
    filename = Path(image_path).name
    expected = get_expected_from_filename(filename)
    
    print(f"\n文件: {filename}")
    print(f"  模型: {API_CLIENT.get_model_name()}")
    if expected is not None:
        print(f"  期望: {'允许' if expected else '不允许'}")
    
    success, is_allowed, elapsed, answer, reasoning = has_bicycle_registration_plate(image_path, verbose)
    
    if success:
        status = "[允许]" if is_allowed else "[不允许]"
        print(f"   {status} | 耗时: {elapsed:.2f}秒")
        
        if expected is not None:
            if is_allowed == expected:
                print(f"   [验证] 正确 ✓")
            else:
                print(f"   [验证] 错误 ✗")
                # 错误时询问是否复制到剪贴板
                if reasoning and input("   复制推理过程到剪贴板？(y/n): ").lower() in ['y', 'yes', '是']:
                    copy_to_clipboard(reasoning)
    else:
        print(f"   [检测失败] {answer}")
    
    return {"filename": filename, "is_allowed": is_allowed if success else None, "success": success}


def process_single_image_mode():
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
        process_single_image(str(selected), verbose=True)
        print("=" * 60)


def process_images_folder(folder_path: str, stop_on_failure: bool = True,
                          stop_on_validation_error: bool = True) -> tuple:
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
            print(f"  期望: {'允许' if expected else '不允许'}")
        
        success, is_allowed, elapsed, answer, reasoning = has_bicycle_registration_plate(str(img), False)
        
        if not success:
            print(f"   [检测失败]")
            if stop_on_failure:
                stopped, stop_reason, stop_index = True, f"检测失败: {img.name}", idx
                break
            continue
        
        status = "[允许]" if is_allowed else "[不允许]"
        print(f"   {status} | 耗时: {elapsed:.2f}秒")
        
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


def export_results_to_csv(results: list, output_file: str = DEFAULT_CSV_FILENAME):
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["文件名", "是否允许", "检测成功"])
        for r in results:
            writer.writerow([r['filename'], "允许" if r['is_allowed'] else "不允许", r['success']])
    print(f"[导出] {output_file}")


def validate_and_save_mode():
    """验证模式：创建有效提示词"""
    print("\n" + "=" * 60)
    print("          验证模式 - 创建有效提示词")
    print("=" * 60)
    print("\n测试集要求: 文件名以'是'或'否'开头")
    print("  是_xxx.jpg - 正例（有自行车且无车牌，期望'是'）")
    print("  否_xxx.jpg - 负例（其他情况，期望'否'）")
    
    test_folder = input("\n请输入测试集文件夹路径: ").strip()
    if not Path(test_folder).exists():
        print(f"[错误] 文件夹不存在")
        return
    
    image_files = get_supported_images_from_folder(test_folder)
    expected_results = {}
    for img in image_files:
        exp = get_expected_from_filename(img.name)
        if exp is not None:
            expected_results[str(img)] = exp
    
    if not expected_results:
        print("[错误] 没有找到以'是'或'否'开头的图片")
        return
    
    pos = sum(1 for v in expected_results.values() if v)
    neg = len(expected_results) - pos
    print(f"\n[信息] 正例: {pos}张, 负例: {neg}张")
    
    print("\n请输入系统提示词 (回车使用默认):")
    system = input().strip()
    if not system:
        system = CHINESE_CONFIG["SYSTEM_PROMPT"]
    print("\n请输入用户提示词 (回车使用默认):")
    user = input().strip()
    if not user:
        user = CHINESE_CONFIG["USER_QUESTION"]
    
    print("\n开始验证...")
    correct = 0
    errors = []
    
    for img_path, expected in expected_results.items():
        exp_str = "是" if expected else "否"
        print(f"\n检测: {Path(img_path).name} (期望:{exp_str})")
        
        success, answer, reasoning, elapsed = API_CLIENT.chat_with_image(img_path, system, user)
        if not success:
            print(f"  失败: {answer}")
            continue
        
        # 使用统一的解析函数
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
        for e in errors[:5]:
            print(f"  - {e['file']}: 期望{e['expected']}, 实际{e['actual']}")
    
    if acc >= 95:
        print(f"\n[通过] 准确率 {acc:.2f}% >= 95%")
        if input("保存此提示词？(y/n): ").lower() in ['y', 'yes', '是']:
            PromptValidator.save_valid_prompt(user, system, acc, {"total": len(expected_results), "correct": correct},
                                              API_TYPE, API_CLIENT.get_model_name())
            print("\n[成功] 提示词已保存！")
    else:
        print(f"\n[不通过] 准确率 {acc:.2f}% < 95%，请优化后重试")


def get_user_choice():
    print("\n" + "=" * 50)
    print("          自行车检测工具")
    print("=" * 50)
    print("\n请选择:")
    print("  1 - 单张图片检测")
    print("  2 - 批量检测")
    print("  3 - 验证并保存提示词")
    print("  0 - 退出")
    
    while True:
        choice = input("\n请输入 (0/1/2/3): ").strip()
        if choice in ['0', '1', '2', '3']:
            return choice
        print("  输入无效")


def get_folder_path():
    while True:
        path = input("\n请输入文件夹路径: ").strip()
        if not path:
            continue
        if Path(path).exists() and Path(path).is_dir():
            return path
        print(f"  文件夹不存在")


def get_export_choice():
    return input("\n导出CSV？(y/n): ").lower() in ['y', 'yes', '是']


def get_stop_strategy():
    print("\n停止策略:")
    print("  1 - 遇到错误停止")
    print("  2 - 验证错误继续")
    print("  3 - 忽略所有错误")
    c = input("请选择 (1/2/3): ").strip()
    if c == '1':
        return True, True
    elif c == '2':
        return True, False
    return False, False


# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("          自行车检测工具")
    print("=" * 50)
    
    # 检查是否有有效提示词
    prompts = PromptValidator.list_valid_prompts()
    
    if not prompts:
        print("\n[提示] 没有找到有效提示词，请先创建")
        if input("立即进入验证模式？(y/n): ").lower() in ['y', 'yes', '是']:
            validate_and_save_mode()
            prompts = PromptValidator.list_valid_prompts()
    
    if prompts:
        data = PromptValidator.get_active_prompt(auto_select=len(prompts) == 1)
        if data:
            SYSTEM_PROMPT = data.get("system_prompt", "")
            USER_QUESTION = data.get("user_prompt", "")
            USE_CHINESE = "是" in USER_QUESTION
            print(f"\n[配置] 语言: {'中文' if USE_CHINESE else '英文'}")
            print(f"[配置] API: {API_TYPE.upper()} - {API_CLIENT.get_model_name()}")
            print(f"[配置] 准确率: {data.get('accuracy', 0):.2f}%")
    else:
        print("\n[错误] 没有可用的有效提示词")
        sys.exit(1)
    
    while True:
        choice = get_user_choice()
        if choice == '0':
            print("\n[信息] 退出")
            break
        elif choice == '1':
            process_single_image_mode()
        elif choice == '2':
            print("\n[模式] 批量检测")
            folder = get_folder_path()
            export = get_export_choice()
            sf, sv = get_stop_strategy()
            results, stopped, reason, idx = process_images_folder(folder, sf, sv)
            if export and results:
                export_results_to_csv(results)
            if stopped:
                print(f"\n[提示] 在第{idx}张停止: {reason}")
        elif choice == '3':
            validate_and_save_mode()
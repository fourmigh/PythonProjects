# main_optimizer.py
# ============================================================
# 自行车检测工具 - 主程序入口（只负责流程控制）
# ============================================================

import sys
from pathlib import Path

from config import API_TYPE, validate_config
from prompt_optimizer import PromptValidator
from bicycle_rule import (
    BicycleNoPlateOptimizer,
    single_image_mode,
    batch_detection_mode,
    validate_and_save_prompts,
    export_results_to_csv,
    API_CLIENT
)


# ============================================================
# 全局变量：存储当前加载的提示词
# ============================================================
CURRENT_SYSTEM_PROMPT = ""
CURRENT_USER_PROMPT = ""


# ============================================================
# 配置验证
# ============================================================
if not validate_config():
    print("\n[错误] 配置验证失败，程序退出")
    sys.exit(1)


# ============================================================
# UI辅助函数
# ============================================================
def print_separator(char: str = "=", length: int = 70):
    print(char * length)


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


def get_user_choice():
    print("\n" + "=" * 50)
    print("          自行车检测工具")
    print("=" * 50)
    print("\n请选择:")
    print("  1 - 单张图片检测")
    print("  2 - 批量检测")
    print("  3 - 验证并保存提示词")
    print("  4 - 提示词优化器")
    print("  0 - 退出")
    
    while True:
        choice = input("\n请输入 (0/1/2/3/4): ").strip()
        if choice in ['0', '1', '2', '3', '4']:
            return choice
        print("  输入无效")


# ============================================================
# 加载有效提示词
# ============================================================
def load_valid_prompt():
    """加载有效提示词到内存"""
    global CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT
    
    prompts = PromptValidator.list_valid_prompts()
    
    if not prompts:
        print("\n[提示] 没有找到有效提示词，请先创建")
        if input("立即进入验证模式？(y/n): ").lower() in ['y', 'yes', '是']:
            from bicycle_rule import validate_and_save_prompts
            validate_and_save_prompts()
            prompts = PromptValidator.list_valid_prompts()
    
    if prompts:
        data = PromptValidator.get_active_prompt(auto_select=len(prompts) == 1)
        if data:
            CURRENT_SYSTEM_PROMPT = data.get("system_prompt", "")
            CURRENT_USER_PROMPT = data.get("user_prompt", "")
            print(f"\n[配置] 语言: {'中文' if '是' in CURRENT_USER_PROMPT else '英文'}")
            print(f"[配置] API: {API_TYPE.upper()} - {API_CLIENT.get_model_name()}")
            print(f"[配置] 准确率: {data.get('accuracy', 0):.2f}%")
            return True
    else:
        print("\n[错误] 没有可用的有效提示词")
        return False
    
    return True


# ============================================================
# 批量检测交互
# ============================================================
def batch_detection_interactive(system_prompt: str, user_prompt: str, debug: bool = False):
    """批量检测交互"""
    print("\n[模式] 批量检测")
    folder = get_folder_path()
    export = get_export_choice()
    sf, sv = get_stop_strategy()
    results, stopped, reason, idx = batch_detection_mode(
        folder, system_prompt, user_prompt, sf, sv, debug
    )
    if export and results:
        export_results_to_csv(results)
    if stopped:
        print(f"\n[提示] 在第{idx}张停止: {reason}")


# ============================================================
# 提示词优化器交互
# ============================================================
def prompt_optimizer_interactive():
    """提示词优化器交互"""
    global CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT
    
    print("\n[模式] 提示词优化器")
    print(f"[API] {API_TYPE.upper()} - {API_CLIENT.get_model_name()}")
    
    optimizer = BicycleNoPlateOptimizer()
    
    # 输入测试集路径
    test_folder = input("\n请输入测试集文件夹路径 (直接回车使用默认: images): ").strip()
    if not test_folder:
        test_folder = "images"
        print(f"使用默认路径: {test_folder}")
    
    if not Path(test_folder).exists():
        print(f"错误: 文件夹不存在 - {test_folder}")
        return
    
    # 选择提示词来源
    print("\n提示词来源选项:")
    print(f"  1 - 使用当前已加载的提示词 (准确率: {PromptValidator.list_valid_prompts()[-1]['accuracy'] if PromptValidator.list_valid_prompts() else '未知'}%)")
    print("  2 - 使用代码中的默认提示词")
    print("  3 - 手动输入提示词")
    
    source = input("\n请选择 (1/2/3，默认1): ").strip()
    
    if source == '2':
        user_prompt = optimizer.get_default_user_prompt()
        system_prompt = optimizer.get_default_system_prompt()
        print("\n使用代码中的默认提示词")
    elif source == '3':
        print("\n请输入用户提示词:")
        user_prompt = input().strip()
        print("\n请输入系统提示词:")
        system_prompt = input().strip()
    else:
        # 默认使用当前加载的提示词（选项1）
        user_prompt = CURRENT_USER_PROMPT
        system_prompt = CURRENT_SYSTEM_PROMPT
        if user_prompt and system_prompt:
            print("\n使用当前已加载的提示词")
        else:
            print("\n[警告] 当前没有加载提示词，使用代码中的默认提示词")
            user_prompt = optimizer.get_default_user_prompt()
            system_prompt = optimizer.get_default_system_prompt()
    
    # 确保提示词不为空
    if not user_prompt or not system_prompt:
        print("[警告] 提示词为空，使用代码中的默认提示词")
        user_prompt = optimizer.get_default_user_prompt()
        system_prompt = optimizer.get_default_system_prompt()
    
    # 打印提示词并确认
    print("\n" + "=" * 70)
    print("使用的提示词")
    print("=" * 70)
    print("\n[用户提示词]")
    print("-" * 50)
    print(user_prompt)
    print("\n[系统提示词]")
    print("-" * 50)
    print(system_prompt)
    
    confirm = input("\n按回车键继续优化，输入 'q' 退出: ").strip().lower()
    if confirm == 'q':
        return
    
    # 优化参数
    max_rounds = input("\n最大优化轮次 (默认: 10): ").strip()
    max_rounds = int(max_rounds) if max_rounds else 10
    
    verbose = input("打印详细信息？(y/n, 默认y): ").strip().lower()
    verbose = verbose not in ['n', 'no', '否']
    
    print("\n" + "=" * 70)
    print("开始优化...")
    print("=" * 70)
    
    result = optimizer.optimize(
        test_folder=test_folder,
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        max_rounds=max_rounds,
        verbose=verbose
    )
    
    print("\n" + "=" * 70)
    print("优化结果")
    print("=" * 70)
    
    if result["success"]:
        print(f"\n[成功] 提示词优化成功！")
        print(f"   总轮次: {result['rounds']}")
        print(f"   测试图片数: {result['total_images']}")
        
        print(f"\n最终用户提示词:")
        print("-" * 50)
        print(result['final_user_prompt'])
        
        print(f"\n最终系统提示词:")
        print("-" * 50)
        print(result['final_system_prompt'])
        
        if input("\n保存最终提示词？(y/n): ").lower() in ['y', 'yes', '是']:
            optimizer.save_final_prompt(
                accuracy=100.0,
                test_info={"test_folder": test_folder, "total_images": result['total_images'], "rounds": result['rounds']}
            )
            print("\n[保存] 提示词已保存到 valid_prompts/ 目录")
    else:
        print(f"\n[失败] 提示词优化失败")
        print(f"   已完成轮次: {result['rounds']}")
        print(f"   测试图片数: {result['total_images']}")


# ============================================================
# 验证模式交互
# ============================================================
def validate_mode_interactive():
    """验证模式交互"""
    global CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT
    
    print("\n[模式] 验证并保存提示词")
    
    # 询问是否使用当前加载的提示词
    if CURRENT_USER_PROMPT and CURRENT_SYSTEM_PROMPT:
        print(f"\n当前已加载的提示词准确率: 100%")
        use_current = input("是否使用当前已加载的提示词进行验证？(y/n, 默认y): ").strip().lower()
        if use_current in ['y', 'yes', '是', '']:
            success = validate_and_save_prompts(CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT)
            if success:
                # 验证完成后重新加载提示词
                load_valid_prompt()
            return
    
    # 否则使用默认方式（手动输入）
    validate_and_save_prompts()


# ============================================================
# 主程序
# ============================================================
def main():
    print_separator()
    print("自行车检测工具 & 提示词优化器")
    print_separator()
    
    # 加载有效提示词
    if not load_valid_prompt():
        print("\n[错误] 无法加载有效提示词")
        sys.exit(1)
    
    while True:
        choice = get_user_choice()
        
        if choice == '0':
            print("\n[信息] 退出")
            break
        elif choice == '1':
            single_image_mode(CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT, debug=False)
        elif choice == '2':
            batch_detection_interactive(CURRENT_SYSTEM_PROMPT, CURRENT_USER_PROMPT, debug=False)
        elif choice == '3':
            validate_mode_interactive()
        elif choice == '4':
            prompt_optimizer_interactive()


if __name__ == "__main__":
    main()
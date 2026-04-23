# main_optimizer.py
# ============================================================
# 提示词优化器 - 主程序入口
# ============================================================

from pathlib import Path
from bicycle_rule import BicycleNoPlateOptimizer
from config import API_TYPE


def print_separator(char: str = "=", length: int = 70):
    print(char * length)


def wait_for_enter(prompt: str = "按回车键继续..."):
    """等待用户按回车键"""
    input(prompt)


def main():
    print_separator()
    print("提示词优化器")
    print_separator()
    
    print(f"\n当前API类型: {API_TYPE}")
    
    # 创建优化器
    optimizer = BicycleNoPlateOptimizer()
    
    print(f"\n规则: {optimizer.get_rule_description()}")
    print(f"模型: {optimizer.api_client.get_model_name()}")
    
    # 输入测试集路径（默认 images）
    print("\n" + "-" * 50)
    test_folder = input("请输入测试集文件夹路径 (直接回车使用默认: images): ").strip()
    
    if not test_folder:
        test_folder = "images"
        print(f"使用默认路径: {test_folder}")
    
    if not Path(test_folder).exists():
        print(f"错误: 文件夹不存在 - {test_folder}")
        return
    
    # 是否使用默认提示词
    print("\n" + "-" * 50)
    use_default = input("使用默认提示词？(y/n, 默认y): ").strip().lower()
    
    if use_default in ['n', 'no', '否']:
        print("\n请输入用户提示词:")
        user_prompt = input().strip()
        print("\n请输入系统提示词:")
        system_prompt = input().strip()
    else:
        user_prompt = None
        system_prompt = None
    
    # 获取实际使用的提示词
    actual_user_prompt = user_prompt or optimizer.get_default_user_prompt()
    actual_system_prompt = system_prompt or optimizer.get_default_system_prompt()
    
    # 打印提示词并等待确认
    print("\n" + "=" * 70)
    print("当前使用的提示词")
    print("=" * 70)
    
    print("\n[用户提示词]")
    print("-" * 50)
    print(actual_user_prompt)
    
    print("\n[系统提示词]")
    print("-" * 50)
    print(actual_system_prompt)
    
    print("\n" + "=" * 70)
    print("请确认以上提示词是否正确")
    print("  - 按回车键继续优化")
    print("  - 输入 'q' 退出程序")
    print("  - 输入其他内容重新输入提示词")
    print("=" * 70)
    
    confirm = input("\n请输入: ").strip().lower()
    
    if confirm == 'q':
        print("\n[信息] 退出程序")
        return
    elif confirm:
        # 用户输入了其他内容，重新输入提示词
        print("\n请重新输入用户提示词:")
        user_prompt = input().strip()
        print("\n请重新输入系统提示词:")
        system_prompt = input().strip()
        actual_user_prompt = user_prompt
        actual_system_prompt = system_prompt
        print("\n[信息] 已更新提示词")
        
        # 再次打印确认
        print("\n" + "=" * 70)
        print("更新后的提示词")
        print("=" * 70)
        print("\n[用户提示词]")
        print("-" * 50)
        print(actual_user_prompt)
        print("\n[系统提示词]")
        print("-" * 50)
        print(actual_system_prompt)
        
        wait_for_enter("\n按回车键继续优化...")
    else:
        # 直接回车，使用当前提示词继续
        pass
    
    # 设置最大优化轮次
    print("\n" + "-" * 50)
    max_rounds_input = input("最大优化轮次 (直接回车使用默认: 10): ").strip()
    max_rounds = int(max_rounds_input) if max_rounds_input else 10
    
    # 设置是否打印详细信息
    verbose_input = input("是否打印详细信息？(y/n, 默认y): ").strip().lower()
    verbose = verbose_input not in ['n', 'no', '否', 'false']
    
    # 执行优化
    print("\n" + "=" * 70)
    print("开始优化...")
    print("=" * 70)
    
    result = optimizer.optimize(
        test_folder=test_folder,
        user_prompt=actual_user_prompt,
        system_prompt=actual_system_prompt,
        max_rounds=max_rounds,
        verbose=verbose
    )
    
    # 输出最终结果
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
        
        # 询问是否保存
        save = input("\n是否保存最终提示词？(y/n): ").strip().lower()
        if save in ['y', 'yes', '是']:
            optimizer.save_final_prompt(
                accuracy=100.0,
                test_info={
                    "test_folder": test_folder,
                    "total_images": result['total_images'],
                    "rounds": result['rounds']
                }
            )
            print("\n[保存] 提示词已保存到 valid_prompts/ 目录")
    else:
        print(f"\n[失败] 提示词优化失败")
        print(f"   已完成轮次: {result['rounds']}")
        print(f"   测试图片数: {result['total_images']}")
        print(f"\n最终用户提示词:")
        print("-" * 50)
        print(result['final_user_prompt'])
        
        # 即使失败也询问是否保存
        save = input("\n是否保存当前提示词？(y/n): ").strip().lower()
        if save in ['y', 'yes', '是']:
            optimizer.save_final_prompt(
                accuracy=0.0,
                test_info={
                    "test_folder": test_folder,
                    "total_images": result['total_images'],
                    "rounds": result['rounds'],
                    "success": False
                }
            )
            print("\n[保存] 提示词已保存到 valid_prompts/ 目录")
    
    # 打印优化摘要
    optimizer.print_summary()


if __name__ == "__main__":
    main()
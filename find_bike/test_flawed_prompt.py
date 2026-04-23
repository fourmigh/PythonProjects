# test_flawed_prompt.py
# 测试有瑕疵的提示词是否能被优化器修复

from pathlib import Path
from bicycle_rule import BicycleNoPlateOptimizer


# 有瑕疵的提示词
FLAWED_USER_PROMPT = "这张图片里有自行车吗？有就说是，没有就说否。"

FLAWED_SYSTEM_PROMPT = """你是一个图像分析助手。
请回答图片中是否有自行车。
如果有自行车回答"是"，没有自行车回答"否"。
"""


def main():
    print("=" * 70)
    print("有瑕疵提示词优化测试")
    print("=" * 70)
    
    # 创建优化器
    optimizer = BicycleNoPlateOptimizer()
    
    print(f"\n当前API: {optimizer.api_client.get_model_name()}")
    print(f"当前模型: {optimizer.api_client.get_model_name()}")
    
    print("\n[有瑕疵的提示词]")
    print("-" * 50)
    print(f"用户提示词: {FLAWED_USER_PROMPT}")
    print(f"\n系统提示词: {FLAWED_SYSTEM_PROMPT}")
    
    # 询问测试集路径
    test_folder = input("\n请输入测试集文件夹路径 (默认: images): ").strip()
    if not test_folder:
        test_folder = "images"
    
    if not Path(test_folder).exists():
        print(f"错误: 文件夹不存在 - {test_folder}")
        return
    
    # 询问是否使用大模型优化
    use_llm = input("\n是否使用大模型优化？(y/n, 默认y): ").strip().lower()
    use_llm = use_llm not in ['n', 'no', '否']
    
    if not use_llm:
        print("\n[信息] 不使用大模型优化，直接测试")
        # 直接测试当前提示词
        optimizer.current_user_prompt = FLAWED_USER_PROMPT
        optimizer.current_system_prompt = FLAWED_SYSTEM_PROMPT
        
        test_images = optimizer.get_supported_images(test_folder)
        correct = 0
        for img_path, expected in test_images:
            result = optimizer.test_single_image(str(img_path), expected, verbose=True)
            if result["is_correct"]:
                correct += 1
        print(f"\n准确率: {correct}/{len(test_images)} = {correct/len(test_images)*100:.2f}%")
        return
    
    # 执行优化
    print("\n" + "=" * 70)
    print("开始优化...")
    print("=" * 70)
    
    result = optimizer.optimize(
        test_folder=test_folder,
        user_prompt=FLAWED_USER_PROMPT,
        system_prompt=FLAWED_SYSTEM_PROMPT,
        max_rounds=5,  # 最多5轮
        verbose=True
    )
    
    # 输出结果
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
        
        # 显示每轮的结果
        print(f"\n[各轮结果]")
        for r in result['round_history']:
            print(f"  第{r['round']}轮: {r.get('correct_count', 0)}/{r.get('tested_count', 0)} 正确 ({r.get('accuracy', 0):.2f}%)")


if __name__ == "__main__":
    main()
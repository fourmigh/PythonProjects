import os
import sys
from PIL import Image
from pathlib import Path

def convert_images_to_bw(folder_path):
    """
    将文件夹内所有图片转换为黑白（灰度）并覆盖原文件

    Args:
        folder_path: 文件夹路径
    """
    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

    # 统计信息
    processed_count = 0
    skipped_count = 0
    error_count = 0

    # 遍历文件夹
    for file_path in Path(folder_path).iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_formats:
            try:
                with Image.open(file_path) as img:
                    # 检查是否已经是灰度图
                    if img.mode == 'L':
                        print(f"跳过 {file_path.name} - 已经是黑白图")
                        skipped_count += 1
                        continue

                    # 转换为灰度（黑白摄像头效果）
                    bw_img = img.convert('L')

                    # 覆盖保存（JPEG 使用高质量，其它格式直接保存）
                    if file_path.suffix.lower() in ('.jpg', '.jpeg'):
                        bw_img.save(file_path, quality=95, optimize=True)
                    else:
                        bw_img.save(file_path)

                    print(f"已转换 {file_path.name}")
                    processed_count += 1

            except Exception as e:
                print(f"处理 {file_path.name} 时出错: {str(e)}")
                error_count += 1

    # 打印统计信息
    print("\n" + "=" * 50)
    print("处理完成！")
    print(f"已转换: {processed_count} 个文件")
    print(f"已跳过: {skipped_count} 个文件")
    print(f"错误: {error_count} 个文件")
    print("=" * 50)

if __name__ == "__main__":
    # 获取当前工作目录
    current_dir = os.getcwd()

    # 优先使用命令行参数，否则让用户输入文件夹名
    if len(sys.argv) > 1:
        folder_name = sys.argv[1].strip()
    else:
        print(f"当前目录: {current_dir}")
        folder_name = input("请输入文件夹名: ").strip()

    folder_name = folder_name.strip('"').strip("'")

    # 构建完整路径
    folder_path = os.path.join(current_dir, folder_name)

    # 检查文件夹是否存在
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        print(f"正在处理文件夹: {folder_path}")
        print("-" * 50)
        convert_images_to_bw(folder_path)
    else:
        print(f"错误: 在当前目录下找不到文件夹 '{folder_name}'")
        print(f"请确保文件夹 '{folder_name}' 存在于: {current_dir}")

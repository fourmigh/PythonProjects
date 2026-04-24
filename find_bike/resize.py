import os
from PIL import Image
from pathlib import Path

def resize_images_to_512(folder_path):
    """
    将文件夹内所有图片缩放到512x512尺寸
    
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
                # 打开图片
                with Image.open(file_path) as img:
                    original_size = img.size
                    
                    # 检查是否已经是512x512
                    if original_size == (512, 512):
                        print(f"跳过 {file_path.name} - 已经是512x512")
                        skipped_count += 1
                        continue
                    
                    # 使用高质量的Lanczos重采样算法进行缩放
                    resized_img = img.resize((512, 512), Image.Resampling.LANCZOS)
                    
                    # 保存图片（覆盖原文件）
                    resized_img.save(file_path, quality=95, optimize=True)
                    print(f"已缩放 {file_path.name} - 从 {original_size[0]}x{original_size[1]} 到 512x512")
                    processed_count += 1
                    
            except Exception as e:
                print(f"处理 {file_path.name} 时出错: {str(e)}")
                error_count += 1
    
    # 打印统计信息
    print("\n" + "="*50)
    print(f"处理完成！")
    print(f"已缩放: {processed_count} 个文件")
    print(f"已跳过: {skipped_count} 个文件")
    print(f"错误: {error_count} 个文件")
    print("="*50)

if __name__ == "__main__":
    # 获取当前工作目录
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}")
    
    # 让用户输入文件夹名
    folder_name = input("请输入文件夹名: ").strip()
    folder_name = folder_name.strip('"').strip("'")
    
    # 构建完整路径
    folder_path = os.path.join(current_dir, folder_name)
    
    # 检查文件夹是否存在
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        print(f"正在处理文件夹: {folder_path}")
        print("-" * 50)
        resize_images_to_512(folder_path)
    else:
        print(f"错误: 在当前目录下找不到文件夹 '{folder_name}'")
        print(f"请确保文件夹 '{folder_name}' 存在于: {current_dir}")
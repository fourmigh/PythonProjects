# test_image.py
# 测试 Ollama 图片识别功能（VLM）

import requests
import base64
import os
import sys
import time
from pathlib import Path

def get_running_model():
    """获取当前运行中的模型"""
    try:
        response = requests.get("http://localhost:11434/api/ps", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            if models:
                return models[0].get('name')
    except Exception:
        pass
    return None

def get_installed_models():
    """获取已安装的模型列表"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m.get('name', '') for m in data.get('models', [])]
    except Exception:
        pass
    return []

def test_image_recognition(image_path, model_name=None, prompt=None):
    """测试图片识别"""
    
    # 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"[ERROR] 图片不存在: {image_path}")
        return None
    
    # 如果没有指定模型，自动检测运行中的模型
    if not model_name:
        model_name = get_running_model()
        if model_name:
            print(f"[INFO] 自动检测到运行中的模型: {model_name}")
        else:
            print("[WARN] 没有运行中的模型")
            installed = get_installed_models()
            if installed:
                print(f"[INFO] 可用的已安装模型: {', '.join(installed)}")
                model_name = installed[0]
                print(f"[INFO] 将使用: {model_name}")
            else:
                print("[ERROR] 没有可用的模型，请先安装并运行一个 VLM 模型")
                print("示例: ollama run llama3.2-vision")
                return None
    
    # 默认提示词
    if not prompt:
        prompt = "请用一句话描述这张图片的内容"
    
    print(f"\n" + "=" * 60)
    print(f"测试图片识别")
    print(f"模型: {model_name}")
    print(f"图片: {image_path}")
    print(f"文件大小: {os.path.getsize(image_path) / 1024:.1f} KB")
    print(f"提示词: {prompt}")
    print("=" * 60)
    
    # 读取并编码图片
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode()
        print(f"[INFO] Base64编码长度: {len(image_base64)} 字符")
    except Exception as e:
        print(f"[ERROR] 读取图片失败: {e}")
        return None
    
    # 调用 Ollama API
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "num_predict": 256,
            "temperature": 0.1
        }
    }
    
    print("[INFO] 发送请求...")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"[INFO] HTTP状态码: {response.status_code}")
        print(f"[INFO] 耗时: {elapsed:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            print("\n" + "=" * 60)
            print("识别结果:")
            print("-" * 40)
            print(response_text)
            print("=" * 60)
            return response_text
        elif response.status_code == 404:
            print(f"[ERROR] 模型 '{model_name}' 不存在")
            print(f"[HINT] 请先安装: ollama pull {model_name}")
            return None
        else:
            print(f"[ERROR] 请求失败: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print("[ERROR] 请求超时（120秒）")
        return None
    except requests.exceptions.ConnectionError:
        print("[ERROR] 无法连接到 Ollama 服务")
        print("[HINT] 请确保 Ollama 服务已启动: ollama serve")
        return None
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        return None

def batch_test(folder_path, model_name=None, max_images=5):
    """批量测试文件夹中的图片"""
    
    if not os.path.isdir(folder_path):
        print(f"[ERROR] 文件夹不存在: {folder_path}")
        return
    
    # 获取所有图片
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(folder_path).glob(f"*{ext}"))
        image_files.extend(Path(folder_path).glob(f"*{ext.upper()}"))
    
    if not image_files:
        print(f"[WARN] 文件夹中没有找到图片: {folder_path}")
        return
    
    print(f"\n找到 {len(image_files)} 张图片")
    print(f"将测试前 {min(max_images, len(image_files))} 张")
    print("=" * 60)
    
    # 如果没有指定模型，获取运行中的模型
    if not model_name:
        model_name = get_running_model()
        if model_name:
            print(f"[INFO] 使用运行中的模型: {model_name}")
        else:
            installed = get_installed_models()
            if installed:
                model_name = installed[0]
                print(f"[INFO] 使用已安装模型: {model_name}")
            else:
                print("[ERROR] 没有可用的模型")
                return
    
    results = []
    for i, img_path in enumerate(image_files[:max_images], 1):
        print(f"\n[{i}/{max_images}] {img_path.name}")
        print("-" * 40)
        
        result = test_image_recognition(str(img_path), model_name)
        results.append({
            'file': img_path.name,
            'result': result
        })
        
        # 避免请求过快
        time.sleep(1)
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("批量测试汇总")
    print("=" * 60)
    for r in results:
        status = "成功" if r['result'] else "失败"
        preview = r['result'][:50] + "..." if r['result'] and len(r['result']) > 50 else r['result']
        print(f"  {r['file']}: {status}")
        if preview:
            print(f"    预览: {preview}")
    
    return results

def main():
    """主函数"""
    # 检查 Ollama 服务
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code != 200:
            print("错误: Ollama 服务未正常运行")
            sys.exit(1)
    except:
        print("错误: 无法连接到 Ollama 服务")
        print("提示: 请确保 Ollama 服务已启动: ollama serve")
        sys.exit(1)
    
    # 显示当前状态
    running = get_running_model()
    installed = get_installed_models()
    
    print("=" * 60)
    print("Ollama VLM 测试工具")
    print("=" * 60)
    
    if running:
        print(f"运行中的模型: {running}")
    else:
        print("运行中的模型: (无)")
    
    if installed:
        print(f"已安装的模型: {', '.join(installed)}")
    else:
        print("已安装的模型: (无)")
    
    print("=" * 60)
    print("\n使用说明:")
    print("  1. 单张测试: python test_image.py <图片路径> [模型名]")
    print("  2. 批量测试: python test_image.py --batch <文件夹路径> [模型名]")
    print("  3. 列出模型: python test_image.py --list")
    print("\n示例:")
    print("  python test_image.py test.png")
    print("  python test_image.py test.png llama3.2-vision")
    print("  python test_image.py --batch ./images")
    print("=" * 60)
    
    # 解析命令行参数
    if len(sys.argv) < 2:
        print("\n[INFO] 请提供图片路径或使用 --batch 参数")
        return
    
    if sys.argv[1] == "--list":
        print("\n已安装的模型:")
        for m in installed:
            print(f"  - {m}")
        return
    
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("[ERROR] 请提供文件夹路径")
            return
        folder = sys.argv[2]
        model = sys.argv[3] if len(sys.argv) > 3 else None
        batch_test(folder, model)
    else:
        image_path = sys.argv[1]
        model = sys.argv[2] if len(sys.argv) > 2 else None
        test_image_recognition(image_path, model)

if __name__ == "__main__":
    main()
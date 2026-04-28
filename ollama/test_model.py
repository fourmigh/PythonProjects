# test_model.py
# 测试 Ollama 纯文本对话功能

import requests
import time

def test_text_chat(model_name=None):
    """测试纯文本对话"""
    
    # 如果没有指定模型，自动检测运行中的模型
    if not model_name:
        try:
            response = requests.get("http://localhost:11434/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if models:
                    model_name = models[0].get('name')
                    print(f"自动检测到运行中的模型: {model_name}")
                else:
                    print("没有运行中的模型，请先执行: ollama run <model_name>")
                    return
        except Exception as e:
            print(f"检测模型失败: {e}")
            return
    
    print(f"\n测试模型: {model_name}")
    print("=" * 50)
    
    # 测试1: 简单对话
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": "你好，请回复'OK'",
        "stream": False,
        "options": {
            "num_predict": 50,
            "temperature": 0
        }
    }
    
    print("测试1: 纯文本对话")
    print("-" * 40)
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            print(f"响应: {response_text}")
            print(f"耗时: {elapsed:.2f}秒")
        else:
            print(f"HTTP错误: {response.status_code}")
            print(f"错误信息: {response.text}")
    except requests.exceptions.Timeout:
        print("请求超时（30秒）")
    except Exception as e:
        print(f"错误: {type(e).__name__}: {str(e)}")
    
    print("\n" + "=" * 50)
    
    # 测试2: 多轮对话（可选）
    print("\n测试2: 多轮对话")
    print("-" * 40)
    payload2 = {
        "model": model_name,
        "prompt": "1+1等于几？只回答数字",
        "stream": False,
        "options": {
            "num_predict": 20,
            "temperature": 0
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload2, timeout=30)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '')
            print(f"问题: 1+1等于几？")
            print(f"回答: {response_text}")
            print(f"耗时: {elapsed:.2f}秒")
        else:
            print(f"HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"错误: {e}")

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

if __name__ == "__main__":
    import sys
    
    # 检查 Ollama 服务是否运行
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code != 200:
            print("错误: Ollama 服务未正常运行")
            sys.exit(1)
    except:
        print("错误: 无法连接到 Ollama 服务，请确保服务已启动")
        print("提示: 运行 'ollama serve' 启动服务")
        sys.exit(1)
    
    # 获取模型名称（可从命令行参数传入）
    model = None
    if len(sys.argv) > 1:
        model = sys.argv[1]
    
    test_text_chat(model)
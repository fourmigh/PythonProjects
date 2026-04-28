# check_running_model.py
import requests
import subprocess

def check_running_model():
    print("=" * 50)
    print("检查 Ollama 运行中的模型")
    print("=" * 50)
    
    # 方法1: API
    print("\n1. 通过 API (/api/ps) 查询:")
    try:
        response = requests.get("http://localhost:11434/api/ps", timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   原始数据: {data}")
            
            # 解析
            if 'models' in data and data['models']:
                for i, model in enumerate(data['models']):
                    print(f"   模型 {i+1}: {model}")
                    if 'name' in model:
                        print(f"     name: {model['name']}")
                    if 'model' in model:
                        print(f"     model: {model['model']}")
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    print(f"   项 {i+1}: {item}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 方法2: 命令行
    print("\n2. 通过命令行 (ollama ps) 查询:")
    result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"   错误: {result.stderr}")
    
    # 方法3: 检查你代码中的配置
    print("\n3. 检查配置文件中的 model_name:")
    try:
        from bicycle_rule import OLLAMA_CONFIG
        print(f"   OLLAMA_CONFIG: {OLLAMA_CONFIG}")
        print(f"   model_name: {OLLAMA_CONFIG.get('model_name', '未设置')}")
    except Exception as e:
        print(f"   无法读取配置: {e}")

if __name__ == "__main__":
    check_running_model()
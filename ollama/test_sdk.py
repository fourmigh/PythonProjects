# test_sdk.py
import ollama

print("=" * 60)
print("Ollama SDK 诊断")
print("=" * 60)

# 1. 查看版本
print(f"\n1. SDK 版本: {getattr(ollama, '__version__', 'unknown')}")

# 2. 查看所有可用的方法和属性
print(f"\n2. 可用方法:")
methods = [m for m in dir(ollama) if not m.startswith('_')]
for m in methods:
    print(f"   - {m}")

# 3. 尝试不同的调用方式
print(f"\n3. 尝试调用:")

# 方式1: ollama.generate
if hasattr(ollama, 'generate'):
    print("   ollama.generate 存在")
    try:
        response = ollama.generate(model="ministral-3:latest", prompt="Hello")
        print(f"      成功: {response.get('response', '')[:50]}")
    except Exception as e:
        print(f"      失败: {e}")
else:
    print("   ollama.generate 不存在")

# 方式2: ollama.Client
if hasattr(ollama, 'Client'):
    print("   ollama.Client 存在")
    try:
        client = ollama.Client()
        # 查看 client 的方法
        client_methods = [m for m in dir(client) if not m.startswith('_')]
        print(f"      Client 方法: {client_methods}")
        
        if hasattr(client, 'generate'):
            response = client.generate(model="ministral-3:latest", prompt="Hello")
            print(f"      generate 成功: {response.get('response', '')[:50]}")
        elif hasattr(client, 'chat'):
            response = client.chat(model="ministral-3:latest", messages=[{"role": "user", "content": "Hello"}])
            print(f"      chat 成功: {response['message']['content'][:50]}")
    except Exception as e:
        print(f"      失败: {e}")
else:
    print("   ollama.Client 不存在")

print("\n" + "=" * 60)
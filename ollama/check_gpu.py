# check_gpu.py
import subprocess
import sys

def check_gpu_memory():
    """检查 GPU 显存"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("GPU 信息:")
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        else:
            print("无法获取 GPU 信息（可能不是 NVIDIA 显卡）")
    except FileNotFoundError:
        print("nvidia-smi 未找到，可能不是 NVIDIA 显卡")
        
        # 尝试使用 Windows API
        try:
            import wmi
            w = wmi.WMI()
            for gpu in w.Win32_VideoController():
                print(f"  GPU: {gpu.Name}")
                print(f"  显存: {gpu.AdapterRAM / (1024**3):.1f} GB" if gpu.AdapterRAM else "  显存: 未知")
        except:
            print("  请在任务管理器中查看 GPU 显存")

if __name__ == "__main__":
    check_gpu_memory()
    
    print("\n" + "=" * 50)
    print("建议:")
    print("  1. 如果显存 < 6GB，推荐使用 moondream")
    print("  2. 如果显存 < 4GB，只能使用 moondream 或 CPU 模式")
    print("  3. CPU 模式: set OLLAMA_NUM_GPU=0 && ollama serve")
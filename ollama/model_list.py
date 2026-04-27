# model_list.py
# 精选 VLM 模型列表

VLM_MODELS = [
    {
        "name": "llama3.2-vision",
        "size": "7.9GB",
        "desc": "Meta官方视觉模型，11B参数",
        "tags": ["11b"],
        "recommended": True
    },
    {
        "name": "llava",
        "size": "4.5GB", 
        "desc": "经典视觉模型，7B参数",
        "tags": ["7b"],
        "recommended": True
    },
    {
        "name": "llava-llama3",
        "size": "5.5GB",
        "desc": "LLaVA升级版，8B参数",
        "tags": ["8b"],
        "recommended": True
    },
    {
        "name": "llava-phi3",
        "size": "2.8GB",
        "desc": "微软Phi-3视觉版，轻量级",
        "tags": ["3.8b"],
        "recommended": True
    },
    {
        "name": "moondream",
        "size": "829MB",
        "desc": "边缘设备友好，1.4B参数",
        "tags": ["1.4b"],
        "recommended": True
    },
    {
        "name": "bakllava",
        "size": "5.0GB",
        "desc": "高清支持，7B参数",
        "tags": ["7b"],
        "recommended": True
    },
    {
        "name": "gemma-2-vision",
        "size": "5.5GB",
        "desc": "Google出品，9B参数",
        "tags": ["9b"],
        "recommended": False
    },
    {
        "name": "qwen2.5-vl",
        "size": "5.5GB",
        "desc": "通义千问视觉版，7B参数",
        "tags": ["7b", "72b"],
        "recommended": False
    },
    {
        "name": "minicpm-v",
        "size": "5.8GB",
        "desc": "面壁智能，8B参数",
        "tags": ["8b"],
        "recommended": False
    },
    {
        "name": "granite3.2-vision",
        "size": "4.9GB",
        "desc": "IBM文档理解优化",
        "tags": ["8b"],
        "recommended": False
    },
]
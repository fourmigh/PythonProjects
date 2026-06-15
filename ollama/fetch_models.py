#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fetch_models.py - 从 Ollama 官网获取视觉模型列表

import re
import json
import time
import requests
from typing import List, Dict, Any

def fetch_models_from_html() -> List[Dict[str, Any]]:
    """从 Ollama 官网 HTML 中提取模型信息"""
    
    url = "https://ollama.com/search?c=vision"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    try:
        print(f"[INFO] 正在请求: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        print(f"[INFO] 获取到 HTML，长度: {len(html)} 字符")
        
        # 方法1: 从 script 标签中提取 JSON 数据
        models = extract_from_scripts(html)
        
        if models:
            print(f"[INFO] 从 script 中提取到 {len(models)} 个模型")
            return models
        
        # 方法2: 从 HTML 结构中提取
        models = extract_from_html_structure(html)
        
        if models:
            print(f"[INFO] 从 HTML 结构中提取到 {len(models)} 个模型")
            return models
        
        # 方法3: 使用正则表达式提取
        models = extract_with_regex(html)
        
        if models:
            print(f"[INFO] 使用正则提取到 {len(models)} 个模型")
            return models
        
        print("[WARN] 未能提取到模型，使用备用列表")
        return get_fallback_models()
        
    except Exception as e:
        print(f"[ERROR] 请求失败: {e}")
        return get_fallback_models()


def extract_from_scripts(html: str) -> List[Dict[str, Any]]:
    """从 script 标签中提取 JSON 数据"""
    models = []
    
    # 查找包含模型数据的 script 标签
    script_pattern = r'<script[^>]*>([^<]+)</script>'
    scripts = re.findall(script_pattern, html, re.DOTALL)
    
    for script in scripts:
        # 查找类似模型列表的 JSON
        json_pattern = r'\[\s*\{\s*"name"\s*:\s*"[^"]+"[^}]*\}\s*\]'
        matches = re.findall(json_pattern, script)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        if 'name' in item:
                            models.append({
                                'name': item.get('name', ''),
                                'description': item.get('description', ''),
                                'tags': item.get('tags', [])
                            })
            except:
                pass
    
    return models


def extract_from_html_structure(html: str) -> List[Dict[str, Any]]:
    """从 HTML 结构中提取模型信息"""
    models = []
    
    # 查找模型卡片（根据 Ollama 页面的实际结构）
    # 常见的模型名称模式
    name_pattern = r'<a[^>]*href="/library/([a-zA-Z0-9][a-zA-Z0-9._-]*)"[^>]*>'
    names = re.findall(name_pattern, html)
    
    # 查找描述
    desc_pattern = r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>'
    descs = re.findall(desc_pattern, html, re.IGNORECASE)
    
    for i, name in enumerate(names):
        if name and not name.startswith('#'):
            desc = descs[i] if i < len(descs) else ''
            models.append({
                'name': name,
                'description': desc.strip(),
                'tags': []
            })
    
    return models


def extract_with_regex(html: str) -> List[Dict[str, Any]]:
    """使用正则表达式直接提取"""
    models = []
    
    # 提取所有模型链接
    pattern = r'/library/([a-zA-Z0-9][a-zA-Z0-9._-]+)'
    matches = re.findall(pattern, html)
    
    # 去重并过滤
    seen = set()
    for name in matches:
        if name not in seen and not name.startswith('#'):
            seen.add(name)
            # 过滤出视觉相关模型
            if is_vision_model(name):
                models.append({
                    'name': name,
                    'description': '',
                    'tags': ['vision']
                })
    
    return models


def is_vision_model(name: str) -> bool:
    """判断是否为视觉模型"""
    name_lower = name.lower()
    vision_keywords = [
        'vision', 'vl', 'vlm', 'multimodal',
        'llava', 'bakllava', 'moondream', 'minicpm',
        'phi3-vision', 'glm', 'qwen-vl', 'cogvlm',
        'gemma', 'paligemma', 'fuyu', 'kosmos',
        'kimi', 'internvl', 'deepseek-vl', 'yi-vl'
    ]
    return any(keyword in name_lower for keyword in vision_keywords)


def get_fallback_models() -> List[Dict[str, Any]]:
    """备用模型列表（当网络请求失败时使用）"""
    return [
        {"name": "llama3.2-vision", "description": "Meta官方视觉模型，11B参数", "tags": ["vision"]},
        {"name": "llava", "description": "经典视觉模型，7B参数", "tags": ["vision"]},
        {"name": "llava-llama3", "description": "LLaVA升级版，8B参数", "tags": ["vision"]},
        {"name": "llava-phi3", "description": "微软Phi-3视觉版，轻量级", "tags": ["vision"]},
        {"name": "moondream", "description": "边缘设备友好，1.4B参数", "tags": ["vision"]},
        {"name": "bakllava", "description": "高清支持，7B参数", "tags": ["vision"]},
        {"name": "minicpm-v", "description": "面壁智能，8B参数", "tags": ["vision"]},
        {"name": "granite3.2-vision", "description": "IBM文档理解优化", "tags": ["vision"]},
        {"name": "phi3-vision", "description": "微软Phi-3视觉版", "tags": ["vision"]},
        {"name": "kimi-k2.6", "description": "原生多模态智能体模型", "tags": ["vision"]},
    ]


def fetch_model_sizes_from_registry(models: List[Dict[str, Any]]) -> Dict[str, str]:
    """通过 Ollama Registry API 获取模型真实大小"""
    print("[INFO] 正在从 Registry API 获取模型大小...")
    sizes = {}
    total = len(models)
    for idx, model in enumerate(models, 1):
        name = model.get('name', '').split(':')[0]
        if not name or name.startswith('#'):
            continue
        url = f'https://registry.ollama.ai/v2/library/{name}/manifests/latest'
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                total_bytes = sum(l.get('size', 0) for l in data.get('layers', []))
                config_size = data.get('config', {}).get('size', 0)
                total_bytes += config_size
                if total_bytes > 1024**3:
                    sizes[name] = f'{total_bytes / (1024**3):.1f}GB'
                else:
                    sizes[name] = f'{total_bytes / (1024**2):.0f}MB'
                print(f"  [{idx}/{total}] {name:25s} -> {sizes[name]}")
            else:
                print(f"  [{idx}/{total}] {name:25s} -> 404 (未在 Registry 找到)")
        except Exception as e:
            print(f"  [{idx}/{total}] {name:25s} -> Error: {e}")
        time.sleep(0.3)
    return sizes


def update_model_list(models: List[Dict[str, Any]], output_file: str = "model_list.py"):
    """更新 model_list.py 文件"""
    
    # 从 Registry API 获取大小
    registry_sizes = fetch_model_sizes_from_registry(models)
    
    # 模型描述和参数信息
    MODEL_INFO = {
        'qwen3.6': {'desc': 'Qwen3.6B 视觉语言模型', 'params': '3.6B'},
        'kimi-k2.6': {'desc': 'Moonshot Kimi 多模态模型'},
        'medgemma': {'desc': '医学领域 Gemma 模型', 'params': '2B'},
        'medgemma1.5': {'desc': '医学领域 Gemma 1.5B', 'params': '1.5B'},
        'gemma4': {'desc': 'Google Gemma4 视觉模型'},
        'qwen3.5': {'desc': 'Qwen3.5 视觉语言模型'},
        'translategemma': {'desc': '翻译专用 Gemma 模型'},
        'ministral-3': {'desc': 'Mistral 轻量级 3B 模型', 'params': '3B'},
        'devstral-small-2': {'desc': 'DevStral 小型模型'},
        'glm-ocr': {'desc': 'GLM OCR 文字识别模型'},
        'kimi-k2.5': {'desc': 'Moonshot Kimi 多模态模型'},
        'deepseek-ocr': {'desc': 'DeepSeek 文字识别模型'},
        'gemini-3-flash-preview': {'desc': 'Google Gemini 3 Flash'},
        'mistral-large-3': {'desc': 'Mistral 大语言模型'},
        'qwen3-vl': {'desc': 'Qwen3 视觉语言模型'},
        'mistral-small3.2': {'desc': 'Mistral Small 3.2', 'params': '24B'},
        'qwen2.5vl': {'desc': 'Qwen2.5 视觉语言模型 7B', 'params': '7B'},
        'gemma3': {'desc': 'Google Gemma3 视觉模型'},
        'llava': {'desc': '经典视觉模型，7B参数', 'params': '7B'},
        'llama3.2-vision': {'desc': 'Meta官方视觉模型，11B参数', 'params': '11B'},
    }
    
    # 生成 Python 代码
    lines = [
        "# model_list.py",
        "# 自动生成于 Ollama 官网",
        "# 更新日期: " + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "VLM_MODELS = ["
    ]
    
    for model in models:
        name = model.get('name', '').split(':')[0]
        if not name or name.startswith('#'):
            continue
        
        size = registry_sizes.get(name, "未知")
        info = MODEL_INFO.get(name, {})
        desc = info.get('desc', model.get('description', '视觉语言模型')[:50])
        
        lines.append(f"    {{")
        lines.append(f'        "name": "{name}",')
        lines.append(f'        "size": "{size}",')
        lines.append(f'        "desc": "{desc}",')
        lines.append(f'        "tags": ["vision"],')
        lines.append(f'        "recommended": False,')
        lines.append(f"    }},")
    
    lines.append("]")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n[OK] 已更新 {output_file}，共 {len(models)} 个视觉模型")


def main():
    """主函数"""
    print("=" * 60)
    print("Ollama 视觉模型列表获取工具")
    print("=" * 60)
    
    # 获取模型
    models = fetch_models_from_html()
    
    if models:
        print(f"\n找到 {len(models)} 个视觉模型:")
        for m in models[:10]:  # 只显示前10个
            print(f"  - {m['name']}")
        if len(models) > 10:
            print(f"  ... 共 {len(models)} 个")
        
        # 更新文件
        update_model_list(models)
    else:
        print("\n[ERROR] 未获取到任何模型")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
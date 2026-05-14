#!/usr/bin/env python3
"""
模型下载模块
支持从 Hugging Face 搜索和下载模型
已集成国内镜像站 hf-mirror.com，无需翻墙
"""

import os
import sys
import tqdm
from pathlib import Path
from typing import List, Dict, Optional

# ==================== 设置国内镜像站 ====================
# 在导入 huggingface_hub 之前设置环境变量
# hf-mirror.com 是国内常用的 Hugging Face 镜像站，无需翻墙即可访问
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
# 全局超时，避免卡死
os.environ['HF_HUB_DEFAULT_TIMEOUT'] = '15'
# tqdm 进度条宽度，防止超长文件名折行
os.environ['TQDM_NCOLS'] = '80'

# 检查 huggingface_hub 是否可用
try:
    from huggingface_hub import HfApi, hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class ModelDownloader:
    """模型下载器 - 支持通过国内镜像站下载"""
    
    def __init__(self, models_path: Path):
        """
        初始化下载器
        :param models_path: 模型保存目录
        """
        self.models_path = Path(models_path)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        # 显示当前镜像配置
        hf_endpoint = os.environ.get('HF_ENDPOINT', 'https://huggingface.co')
        print(f"[INFO] HuggingFace 镜像: {hf_endpoint}")
        
        if not HF_AVAILABLE:
            print("[WARN] huggingface-hub 未安装，下载功能不可用")
            print("   运行以下命令安装:")
            print("   pip install huggingface-hub -i https://pypi.tuna.tsinghua.edu.cn/simple")
    
    def is_available(self) -> bool:
        """检查下载功能是否可用"""
        return HF_AVAILABLE
    
    def search_models(self, query: str, limit: int = 30) -> List[Dict]:
        """
        搜索 Hugging Face 模型
        :param query: 搜索关键词
        :param limit: 返回结果数量限制
        :return: 模型信息列表
        """
        if not HF_AVAILABLE:
            return []
        
        print(f"\n[SEARCH] 正在搜索: {query}")
        print("   (这可能需要几秒钟)...")

        endpoints = [
            os.environ.get('HF_ENDPOINT', 'https://hf-mirror.com'),
            'https://huggingface.co',
        ]
        endpoints = list(dict.fromkeys(endpoints))

        for ep in endpoints:
            try:
                api = HfApi(endpoint=ep)
                models = api.list_models(
                    search=query,
                    limit=limit,
                    sort="downloads",
                )
                
                results = []
                for model in models:
                    try:
                        files = api.list_repo_files(model.modelId)
                        gguf_files = [f for f in files if f.endswith('.gguf')]
                        if gguf_files:
                            main_gguf = self._get_preferred_gguf(gguf_files)
                            if main_gguf:
                                results.append({
                                    "repo_id": model.modelId,
                                    "filename": main_gguf,
                                    "downloads": model.downloads or 0,
                                    "likes": model.likes or 0,
                                    "tags": model.tags or []
                                })
                    except Exception:
                        continue

                if results:
                    return results
            except Exception as e:
                print(f"  [WARN] 端点 {ep} 搜索失败: {e}")
                continue

        print("[X] 搜索失败: 所有端点均不可用")
        print("   提示: 请使用手动输入仓库 ID 的方式")
        return []
    
    def _get_preferred_gguf(self, files):
        """从 GGUF 文件列表中选择优先的文件"""
        # 优先级顺序（从高到低）
        priorities = ['q4_k_m', 'q5_k_m', 'q4_k_s', 'q5_k_s', 'q4_0', 'q5_0', 'q8_0']
        
        for priority in priorities:
            for f in files:
                name = f.lower() if isinstance(f, str) else f.rfilename.lower()
                if priority in name:
                    return f
        
        # 如果没有匹配的优先级，返回第一个
        return files[0] if files else None
    
    def list_model_files(self, repo_id: str) -> List[Dict]:
        """
        列出仓库中的所有 GGUF 文件
        :param repo_id: Hugging Face 仓库 ID
        :return: 文件信息列表
        """
        if not HF_AVAILABLE:
            return []
        
        endpoints = [
            os.environ.get('HF_ENDPOINT', 'https://hf-mirror.com'),
            'https://huggingface.co',
        ]
        endpoints = list(dict.fromkeys(endpoints))

        for ep in endpoints:
            try:
                api = HfApi(endpoint=ep)
                files = api.list_repo_files(repo_id)
                gguf_files = [f for f in files if f.endswith('.gguf')]

                results = []
                for f in gguf_files:
                    name_lower = f.lower()
                    quant = self._detect_quantization(name_lower)
                    results.append({
                        "filename": f,
                        "size_bytes": 0,
                        "size_mb": 0,
                        "size_gb": 0,
                        "quantization": quant
                    })

                results.sort(key=lambda x: x["size_mb"])
                if results:
                    return results
            except Exception as e:
                print(f"  [WARN] 端点 {ep} 获取文件列表失败: {e}")
                continue

        print(f"[X] 获取文件列表失败: 仓库 {repo_id} 无 GGUF 文件或端点均不可用")
        print("   提示: 请检查仓库 ID 是否正确，或网络连接是否正常")
        return []
    
    def _detect_quantization(self, filename: str) -> str:
        """从文件名检测量化类型"""
        quant_map = {
            'q2_k': 'Q2_K', 'q2k': 'Q2_K',
            'q3_k': 'Q3_K', 'q3k': 'Q3_K',
            'q4_k': 'Q4_K', 'q4k': 'Q4_K',
            'q5_k': 'Q5_K', 'q5k': 'Q5_K',
            'q6_k': 'Q6_K', 'q6k': 'Q6_K',
            'q8_0': 'Q8_0',
            'q4_0': 'Q4_0',
            'q5_0': 'Q5_0',
            'q8_0': 'Q8_0',
            'f16': 'F16',
            'f32': 'F32'
        }
        
        for key, value in quant_map.items():
            if key in filename:
                return value
        return "unknown"
    
    def download_model(self, repo_id: str, filename: str, show_progress: bool = True) -> bool:
        """
        下载模型文件
        :param repo_id: Hugging Face 仓库 ID
        :param filename: 文件名
        :param show_progress: 是否显示进度（默认显示）
        :return: 是否成功
        """
        if not HF_AVAILABLE:
            print("[X] huggingface-hub 未安装，无法下载")
            return False
        
        local_path = self.models_path / filename
        
        # 检查文件是否已存在
        if local_path.exists():
            existing_size = local_path.stat().st_size / (1024**3)
            print(f"[WARN] 文件已存在: {filename}")
            print(f"   文件大小: {existing_size:.2f} GB")
            overwrite = input("是否重新下载覆盖? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("[OK] 取消下载")
                return False
        
        print(f"\n[DOWNLOAD] 正在下载: {filename}")
        print(f"   来源: {repo_id}")
        print(f"   目标: {local_path}")
        print(f"   镜像: {os.environ.get('HF_ENDPOINT', 'https://huggingface.co')}")
        
        if show_progress:
            print("   进度: 开始下载（大文件可能需要较长时间）...")
        
        try:
            # 单行进度条
            tqdm.tqdm.position = 0
            tqdm.tqdm.leave = False

            # 猴子补丁：所有 tqdm 实例强制 ncols=80 并截断超长描述
            _orig_tqdm_init = tqdm.tqdm.__init__
            def _patched_tqdm_init(self, *args, **kwargs):
                kwargs['ncols'] = 120
                kwargs['bar_format'] = '{desc}: {percentage:5.2f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                desc = kwargs.get('desc', '')
                if len(desc) > 35:
                    kwargs['desc'] = desc[:32] + '...'
                return _orig_tqdm_init(self, *args, **kwargs)
            tqdm.tqdm.__init__ = _patched_tqdm_init

            try:
                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=self.models_path,
                )
            finally:
                tqdm.tqdm.__init__ = _orig_tqdm_init
            
            # 获取下载后的文件信息
            downloaded_file = Path(downloaded_path)
            file_size = downloaded_file.stat().st_size / (1024**3)
            
            print(f"\n[OK] 下载完成!")
            print(f"   文件: {downloaded_file.name}")
            print(f"   大小: {file_size:.2f} GB")
            print(f"   路径: {downloaded_file}")
            return True
            
        except Exception as e:
            print(f"\n[X] 下载失败: {e}")
            print("\n可能的原因:")
            print("   1. 网络连接问题，请检查网络")
            print("   2. 仓库 ID 或文件名不正确")
            print("   3. 镜像站暂时不可访问")
            print("\n建议:")
            print("   - 稍后重试")
            print("   - 尝试使用其他镜像（修改代码中的 HF_ENDPOINT）")
            return False

    # 精选模型列表（当搜索不可用时的回退方案）
    CURATED_MODELS = [
        {"repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",       "desc": "通义千问 7B，中文友好"},
        {"repo_id": "Qwen/Qwen2.5-14B-Instruct-GGUF",      "desc": "通义千问 14B，需要更多内存"},
        {"repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",       "desc": "通义千问 3B，轻量级"},
        {"repo_id": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",     "desc": "通义千问 1.5B，超轻量"},
        {"repo_id": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",     "desc": "通义千问 0.5B，最小版本"},
        {"repo_id": "TheBloke/Llama-2-7B-Chat-GGUF",       "desc": "Llama 2 7B"},
        {"repo_id": "TheBloke/Llama-2-13B-Chat-GGUF",      "desc": "Llama 2 13B"},
        {"repo_id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF", "desc": "Mistral 7B"},
        {"repo_id": "TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF", "desc": "Mixtral 8x7B 混合专家"},
        {"repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "desc": "Llama 3.1 8B"},
        {"repo_id": "microsoft/Phi-3-mini-4k-instruct-gguf", "desc": "Phi-3 mini 3.8B"},
    ]

    def _try_fetch_models(self, queries: List[str], limit_per_query: int, endpoint: str) -> List[Dict]:
        """用指定 endpoint 尝试获取模型列表，失败返回空列表"""
        seen = set()
        results = []
        try:
            api = HfApi(endpoint=endpoint)
            for query in queries:
                print(f"    [INFO] 搜索 '{query}'...")
                try:
                    models = api.list_models(
                        search=query,
                        limit=limit_per_query,
                        sort="downloads",
                    )
                    for model in models:
                        if model.modelId in seen:
                            continue
                        seen.add(model.modelId)
                        results.append({
                            "repo_id": model.modelId,
                            "downloads": model.downloads or 0,
                            "likes": model.likes or 0,
                            "tags": model.tags or []
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"  [WARN] 端点 {endpoint} 不可用: {e}")
        return results

    def list_popular_models(self, limit_per_query: int = 10) -> List[Dict]:
        """
        搜索热门 GGUF 模型，返回去重后按下载量排序的模型列表
        :param limit_per_query: 每个关键词返回结果数量
        :return: 模型信息列表（失败时返回空列表）
        """
        if not HF_AVAILABLE:
            return []

        queries = ['gguf', 'gguf chinese', 'gguf instruct', 'gguf deepseek']

        endpoints = [
            os.environ.get('HF_ENDPOINT', 'https://hf-mirror.com'),
            'https://huggingface.co',
        ]
        endpoints = list(dict.fromkeys(endpoints))

        results = []
        for ep in endpoints:
            print(f"  [INFO] 尝试从 {ep} 获取模型列表...")
            results = self._try_fetch_models(queries, limit_per_query, ep)
            if results:
                break

        results.sort(key=lambda x: x["downloads"], reverse=True)
        return results

    def _display_model_list(self, models: List[Dict], title: str, is_curated: bool = False) -> Optional[str]:
        """
        展示模型列表并提供选择
        :param models: 模型列表
        :param title: 列表标题
        :param is_curated: 是否为精选列表（不显示下载/点赞数）
        :return: 用户选择的 repo_id，或 None 表示取消/失败
        """
        if not models:
            return None

        print(f"\n{title} (共 {len(models)} 个):")
        print("-" * 80)
        for i, m in enumerate(models, 1):
            if is_curated:
                desc = ""
                for cm in self.CURATED_MODELS:
                    if cm["repo_id"] == m["repo_id"]:
                        desc = f"  {cm['desc']}"
                        break
                print(f"  {i:2d}. {m['repo_id']:<50s}{desc}")
            else:
                downloads_str = f"{m['downloads'] / 1000:.1f}k" if m['downloads'] >= 1000 else str(m['downloads'])
                likes_str = f"{m['likes'] / 1000:.1f}k" if m['likes'] >= 1000 else str(m['likes'])
                print(f"  {i:2d}. {m['repo_id']:<50s}  下载:{downloads_str:>8s}  点赞:{likes_str:>6s}")
        print("-" * 80)

        try:
            n = len(models)
            extra_msg = ""
            if not is_curated:
                extra_msg = f", {n + 1}=搜索, {n + 2}=手动输入"
            prompt = f"\n请选择模型序号 (1-{n}, 0=取消{extra_msg}): "
            choice = int(input(prompt))
            if choice == 0:
                return None
            if 1 <= choice <= n:
                return models[choice - 1]["repo_id"]
            print("[X] 无效的选择")
            return None
        except ValueError:
            print("[X] 请输入有效的数字")
            return None

    def _format_size(self, file_info: Dict) -> str:
        """格式化文件大小显示"""
        if file_info.get("size_gb", 0) > 0:
            if file_info["size_gb"] > 1:
                return f"{file_info['size_gb']:.2f} GB"
            elif file_info["size_gb"] > 0.001:
                return f"{file_info['size_mb']:.0f} MB"
        return "N/A"

    def _parse_repo_input(self, repo_input: str) -> str:
        """从用户输入中提取仓库 ID，支持 URL 格式"""
        for prefix in ["huggingface.co/", "hf-mirror.com/"]:
            if prefix in repo_input:
                parts = repo_input.split(prefix)
                if len(parts) > 1:
                    path_parts = parts[1].split("/")
                    if len(path_parts) >= 2:
                        return f"{path_parts[0]}/{path_parts[1]}"
        return repo_input

    def search_and_download_interactive(self) -> bool:
        """交互式搜索并下载模型"""
        if not HF_AVAILABLE:
            print("[X] 需要安装 huggingface-hub")
            print("   运行: pip install huggingface-hub -i https://pypi.tuna.tsinghua.edu.cn/simple")
            return False

        print("\n" + "=" * 60)
        print("[DOWNLOAD] Hugging Face 模型下载 (使用国内镜像)")
        print("=" * 60)

        # 获取热门模型列表
        print("\n[INFO] 正在获取热门 GGUF 模型列表...")
        models = self.list_popular_models()

        is_curated = False
        if not models:
            print("[WARN] 无法获取实时模型列表，显示精选模型（可能为网络或镜像问题）")
            models = [{"repo_id": m["repo_id"], "downloads": 0, "likes": 0, "tags": []}
                      for m in self.CURATED_MODELS]
            is_curated = True

        while True:
            if is_curated:
                title = "[LIST] 精选 GGUF 模型"
            else:
                title = "[LIST] 热门 GGUF 模型"

            repo_id = self._display_model_list(models, title, is_curated)

            if repo_id is not None:
                break

            print("\n[INFO] 其他方式:")
            print("  1. 输入关键词搜索")
            print("  2. 直接输入仓库 ID")
            print("  0. 返回/退出")
            try:
                alt = int(input("\n请选择 (0-2): "))
            except ValueError:
                print("[X] 请输入有效的数字")
                return False

            if alt == 0:
                print("[OK] 取消下载")
                return False
            elif alt == 1:
                query = input("\n请输入搜索关键词 (例如: Qwen, Llama, DeepSeek): ").strip()
                if not query:
                    continue
                search_results = self.search_models(query)
                if not search_results:
                    print("[X] 未找到相关模型")
                    continue
                picked = self._display_model_list(search_results, f"[SEARCH] 搜索结果 ({query})")
                if picked is None:
                    continue
                repo_id = picked
                break
            elif alt == 2:
                repo_input = input("\n请输入仓库 ID (例如 Qwen/Qwen2.5-7B-Instruct-GGUF): ").strip()
                if not repo_input:
                    continue
                repo_id = self._parse_repo_input(repo_input)
                break
            else:
                print("[X] 无效的选择")

        # 获取文件列表
        print(f"\n[INFO] 正在获取 {repo_id} 的 GGUF 文件列表...")
        files = self.list_model_files(repo_id)

        if not files:
            print(f"[X] 仓库 {repo_id} 中未找到 GGUF 文件")
            return False

        # 显示文件列表并自动推荐
        print(f"\n[FILES] 找到 {len(files)} 个 GGUF 文件:")
        print("-" * 70)
        for i, f in enumerate(files, 1):
            recommended = ""
            if f['quantization'] in ['Q4_K', 'Q4_K_M', 'Q4_K_S']:
                recommended = " [推荐]"
            size_display = self._format_size(f)
            print(f"  {i}. {f['filename']}{recommended}")
            print(f"     量化: {f['quantization']} | 大小: {size_display}")
        print("-" * 70)

        selected = None
        for priority in ['q4_k_m', 'q5_k_m', 'q4_k_s', 'q4_0', 'q8_0', 'f16']:
            for f in files:
                if priority in f['filename'].lower():
                    selected = f
                    break
            if selected:
                break
        if not selected:
            selected = files[0]

        print(f"\n[INFO] 自动推荐: {selected['filename']} ({selected['quantization']}, {self._format_size(selected)})")

        try:
            file_choice = int(input(f"\n请选择文件序号 (1-{len(files)}, 0=使用推荐): ") or "0")
            if file_choice == 0:
                pass
            elif 1 <= file_choice <= len(files):
                selected = files[file_choice - 1]
            else:
                print("[X] 无效的选择，使用推荐文件")
        except ValueError:
            print("[INFO] 使用推荐文件")

        # 确认下载
        print(f"\n[INFO] 下载信息确认:")
        print(f"   文件: {selected['filename']}")
        print(f"   量化: {selected['quantization']}")
        print(f"   大小: {self._format_size(selected)}")
        print(f"   仓库: {repo_id}")

        confirm = input("\n确认下载? (y/N): ").strip().lower()
        if confirm != 'y':
            print("[OK] 取消下载")
            return False

        show_progress = input("显示下载进度? (Y/n): ").strip().lower()
        show_progress = show_progress != 'n'

        return self.download_model(repo_id, selected['filename'], show_progress)


# 测试代码
if __name__ == "__main__":
    test_path = Path("./test_models")
    downloader = ModelDownloader(test_path)

    print("\n测试下载器:")
    print(f"  huggingface_hub 可用: {downloader.is_available()}")
    print(f"  镜像地址: {os.environ.get('HF_ENDPOINT', 'https://huggingface.co')}")
    print(f"  模型目录: {downloader.models_path}")

    if downloader.is_available():
        print("\n[TEST] 获取热门 GGUF 模型列表...")
        models = downloader.list_popular_models()
        if models:
            print(f"  找到 {len(models)} 个热门模型")
            for m in models[:5]:
                print(f"    - {m['repo_id']} (下载: {m['downloads']}, 点赞: {m['likes']})")

        downloader.search_and_download_interactive()
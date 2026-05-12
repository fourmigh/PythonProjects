#!/usr/bin/env python3
from __future__ import annotations
"""
Ollama API 兼容代理
将 Ollama 格式的 API 请求转换为 llama.cpp OpenAI 兼容格式

使用方法:
  python3 server/ollama_proxy.py [--llama-port 8080] [--proxy-port 11434]

然后即可使用 Ollama 客户端连接:
  curl http://127.0.0.1:11434/api/chat -d '{"model":"model","messages":[{"role":"user","content":"hi"}]}'
  ollama run <任何名称>  # 设置 OLLAMA_HOST=http://127.0.0.1:11434
"""

import json
import sys
import time
import uuid
import argparse
from pathlib import Path

# ---------- 依赖检查 ----------
try:
    from flask import Flask, request, Response, jsonify, stream_with_context
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    import requests as http_requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ---------- 工具函数 ----------

def _now():
    """返回 ISO 格式时间戳"""
    return time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())


def _req_to_openai_messages(ollama_req: dict) -> list:
    """将 Ollama 请求中的 messages 转为 OpenAI 格式"""
    messages = ollama_req.get("messages", [])
    result = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        # 支持 multimode images
        if isinstance(content, list):
            texts = [c["text"] for c in content if c.get("type") == "text"]
            content = "\n".join(texts)
        msg = {"role": role, "content": content}
        result.append(msg)
    return result


def _merge_options(ollama_req: dict) -> dict:
    """将 Ollama 的 options 展开到顶层参数"""
    options = ollama_req.get("options", {})
    mapping = {
        "temperature": "temperature",
        "top_p": "top_p",
        "top_k": "top_k",
        "num_predict": "max_tokens",
        "stop": "stop",
        "seed": "seed",
        "frequency_penalty": "frequency_penalty",
        "presence_penalty": "presence_penalty",
        "repeat_penalty": "repeat_penalty",
        "mirostat": "mirostat",
        "mirostat_tau": "mirostat_tau",
        "mirostat_eta": "mirostat_eta",
        "num_ctx": "max_tokens",
    }
    extra = {}
    for ok, ov in options.items():
        target = mapping.get(ok)
        if target:
            extra[target] = ov
    return extra


def _build_openai_chat_request(ollama_req: dict) -> dict:
    """构建 OpenAI /v1/chat/completions 请求体"""
    messages = _req_to_openai_messages(ollama_req)
    options = _merge_options(ollama_req)
    body = {
        "model": ollama_req.get("model", "model"),
        "messages": messages,
        "stream": ollama_req.get("stream", False),
        **options,
    }
    return {k: v for k, v in body.items() if v is not None}


def _build_openai_completion_request(ollama_req: dict) -> dict:
    """构建 OpenAI /v1/completions 请求体"""
    options = _merge_options(ollama_req)
    body = {
        "model": ollama_req.get("model", "model"),
        "prompt": ollama_req.get("prompt", ""),
        "stream": ollama_req.get("stream", False),
        **options,
    }
    return {k: v for k, v in body.items() if v is not None}


def _build_openai_embed_request(ollama_req: dict) -> dict:
    """构建 OpenAI /v1/embeddings 请求体"""
    return {
        "model": ollama_req.get("model", "model"),
        "input": ollama_req.get("input", ollama_req.get("prompt", "")),
    }


# ---------- 响应转换 ----------

def _convert_chat_response(openai_resp: dict, model: str) -> dict:
    """将 OpenAI /v1/chat/completions 响应转为 Ollama /api/chat 响应"""
    choice = openai_resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_resp.get("usage", {})
    return {
        "model": model,
        "created_at": _now(),
        "message": {
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
        },
        "done": True,
        "done_reason": choice.get("finish_reason", "stop"),
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
        "eval_duration": 0,
    }


def _convert_generate_response(openai_resp: dict, model: str) -> dict:
    """将 OpenAI /v1/completions 响应转为 Ollama /api/generate 响应"""
    choice = openai_resp.get("choices", [{}])[0]
    usage = openai_resp.get("usage", {})
    return {
        "model": model,
        "created_at": _now(),
        "response": choice.get("text", ""),
        "done": True,
        "done_reason": choice.get("finish_reason", "stop"),
        "total_duration": 0,
        "load_duration": 0,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
        "eval_duration": 0,
    }


def _convert_embed_response(openai_resp: dict, model: str) -> dict:
    """将 OpenAI /v1/embeddings 响应转为 Ollama /api/embeddings 响应"""
    data = openai_resp.get("data", [{}])[0]
    usage = openai_resp.get("usage", {})
    return {
        "model": model,
        "embeddings": data.get("embedding", []),
        "total_duration": 0,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": 0,
    }


# ---------- 流式转换 ----------

def _stream_chat_chunks(llama_response, model: str):
    """将 OpenAI SSE 流式响应逐块转换为 Ollama 格式"""
    message_id = str(uuid.uuid4())
    for line in llama_response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "message": {"role": "assistant", "content": ""},
                    "done": True,
                    "done_reason": "stop",
                }) + "\n"
                return
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            finish = choices[0].get("finish_reason")
            if finish:
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "message": {"role": "assistant", "content": ""},
                    "done": True,
                    "done_reason": finish,
                }) + "\n"
                return
            if content:
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "message": {"role": "assistant", "content": content},
                    "done": False,
                }) + "\n"


def _stream_gen_chunks(llama_response, model: str):
    """将 OpenAI /v1/completions SSE 流逐块转换为 Ollama 格式"""
    for line in llama_response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "response": "",
                    "done": True,
                    "done_reason": "stop",
                }) + "\n"
                return
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices", [])
            if not choices:
                continue
            text = choices[0].get("text", "")
            finish = choices[0].get("finish_reason")
            if finish:
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "response": "",
                    "done": True,
                    "done_reason": finish,
                }) + "\n"
                return
            if text:
                yield json.dumps({
                    "model": model,
                    "created_at": _now(),
                    "response": text,
                    "done": False,
                }) + "\n"


# ---------- 模型列表 ----------

def _fetch_model_list(llama_base: str) -> list:
    """从 llama-server 获取模型列表"""
    try:
        resp = http_requests.get(f"{llama_base}/v1/models", timeout=5)
        if resp.ok:
            data = resp.json()
            models = []
            for m in data.get("data", []):
                models.append({
                    "name": m.get("id", "unknown"),
                    "modified_at": m.get("created", _now()),
                    "size": 0,
                    "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
                    "details": {"family": "gguf", "format": "gguf", "parameter_size": "", "quantization_level": ""},
                })
            return models
    except Exception:
        pass
    return []


# ---------- Flask 应用 ----------

def create_app(llama_base_url: str) -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)

    @app.route("/", methods=["HEAD", "GET"])
    def root():
        return jsonify({"status": "ok", "proxy": "llama-ollama-proxy"})

    # ---- /api/chat ----
    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        body = request.get_json(silent=True) or {}
        model = body.get("model", "model")
        stream = body.get("stream", False)
        openai_body = _build_openai_chat_request(body)

        if stream:
            llama_resp = http_requests.post(
                f"{llama_base_url}/v1/chat/completions",
                json={**openai_body, "stream": True},
                stream=True, timeout=300,
            )
            return Response(
                stream_with_context(_stream_chat_chunks(llama_resp, model)),
                content_type="application/x-ndjson",
            )
        else:
            try:
                llama_resp = http_requests.post(
                    f"{llama_base_url}/v1/chat/completions",
                    json=openai_body, timeout=300,
                )
                llama_resp.raise_for_status()
                return jsonify(_convert_chat_response(llama_resp.json(), model))
            except http_requests.exceptions.ConnectionError:
                return jsonify({"error": f"无法连接到 llama-server ({llama_base_url})，请先启动 API 服务器"}), 503
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ---- /api/generate ----
    @app.route("/api/generate", methods=["POST"])
    def api_generate():
        body = request.get_json(silent=True) or {}
        model = body.get("model", "model")
        stream = body.get("stream", False)
        openai_body = _build_openai_completion_request(body)

        if stream:
            llama_resp = http_requests.post(
                f"{llama_base_url}/v1/completions",
                json={**openai_body, "stream": True},
                stream=True, timeout=300,
            )
            return Response(
                stream_with_context(_stream_gen_chunks(llama_resp, model)),
                content_type="application/x-ndjson",
            )
        else:
            try:
                llama_resp = http_requests.post(
                    f"{llama_base_url}/v1/completions",
                    json=openai_body, timeout=300,
                )
                llama_resp.raise_for_status()
                return jsonify(_convert_generate_response(llama_resp.json(), model))
            except http_requests.exceptions.ConnectionError:
                return jsonify({"error": f"无法连接到 llama-server ({llama_base_url})，请先启动 API 服务器"}), 503
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ---- /api/embeddings ----
    @app.route("/api/embeddings", methods=["POST"])
    @app.route("/api/embed", methods=["POST"])
    def api_embeddings():
        body = request.get_json(silent=True) or {}
        model = body.get("model", "model")
        openai_body = _build_openai_embed_request(body)
        try:
            llama_resp = http_requests.post(
                f"{llama_base_url}/v1/embeddings",
                json=openai_body, timeout=60,
            )
            llama_resp.raise_for_status()
            return jsonify(_convert_embed_response(llama_resp.json(), model))
        except http_requests.exceptions.ConnectionError:
            return jsonify({"error": f"无法连接到 llama-server ({llama_base_url})，请先启动 API 服务器"}), 503
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ---- /api/tags ----
    @app.route("/api/tags", methods=["GET"])
    def api_tags():
        models = _fetch_model_list(llama_base_url)
        return jsonify({"models": models})

    # ---- /api/version ----
    @app.route("/api/version", methods=["GET"])
    def api_version():
        return jsonify({"version": "0.5.0"})

    # ---- /api/ps ----
    @app.route("/api/ps", methods=["GET"])
    def api_ps():
        models = _fetch_model_list(llama_base_url)
        return jsonify({"models": models})

    return app


# ---------- 命令行入口 ----------

def main():
    parser = argparse.ArgumentParser(description="Ollama API 兼容代理")
    parser.add_argument("--llama-host", default="127.0.0.1", help="llama-server 地址")
    parser.add_argument("--llama-port", type=int, default=8080, help="llama-server 端口")
    parser.add_argument("--proxy-host", default="127.0.0.1", help="代理监听地址")
    parser.add_argument("--proxy-port", type=int, default=11434, help="代理监听端口 (Ollama 默认 11434)")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    if not FLASK_AVAILABLE:
        print("[X] 需要 Flask: pip install flask")
        sys.exit(1)
    if not REQUESTS_AVAILABLE:
        print("[X] 需要 requests: pip install requests")
        sys.exit(1)

    llama_base = f"http://{args.llama_host}:{args.llama_port}"
    app = create_app(llama_base)

    print(f"\n{'='*50}")
    print("[PROXY] Ollama API 兼容代理")
    print("="*50)
    print(f"  Ollama API : http://{args.proxy_host}:{args.proxy_port}")
    print(f"  后端       : {llama_base} (llama-server)")
    print(f"\n  使用方法:")
    print(f"  export OLLAMA_HOST=http://{args.proxy_host}:{args.proxy_port}")
    print(f"  ollama run <任意模型名>")
    print(f"\n  或直接调用:")
    print(f"  curl http://{args.proxy_host}:{args.proxy_port}/api/chat \\")
    print(f"    -d '{{\"model\":\"m\",\"messages\":[{{\"role\":\"user\",\"content\":\"hi\"}}]}}'")
    print(f"\n  按 Ctrl+C 停止代理")
    print("="*50)

    app.run(host=args.proxy_host, port=args.proxy_port, debug=args.debug)


if __name__ == "__main__":
    main()

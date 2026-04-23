# config.py
# ============================================================
# 配置文件 - 自行车检测工具
# ============================================================

import os

# ============================================================
# API 类型选择
# ============================================================
API_TYPE = os.getenv('API_TYPE', 'ollama')  # ollama, zhipu, openai, bedrock

# ============================================================
# Ollama 配置
# ============================================================
OLLAMA_CONFIG = {
    "api_url": os.getenv('OLLAMA_API_URL', 'http://localhost:11434/v1/chat/completions'),
    "model_name": os.getenv('OLLAMA_MODEL_NAME', 'llama3.2-vision'),
    "timeout": int(os.getenv('OLLAMA_TIMEOUT', '120')),
    "max_tokens": int(os.getenv('OLLAMA_MAX_TOKENS', '2000')),
    "temperature": float(os.getenv('OLLAMA_TEMPERATURE', '0'))
}

# ============================================================
# 智谱AI 配置
# ============================================================
ZHIPU_CONFIG = {
    "api_key": os.getenv('ZHIPU_API_KEY', ''),
    "model_name": os.getenv('ZHIPU_MODEL_NAME', 'glm-4v-flash'),
    "timeout": int(os.getenv('ZHIPU_TIMEOUT', '120'))
}

# ============================================================
# OpenAI兼容API配置
# ============================================================
OPENAI_CONFIG = {
    "api_key": os.getenv('OPENAI_API_KEY', ''),
    "base_url": os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
    "model_name": os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini'),
    "timeout": int(os.getenv('OPENAI_TIMEOUT', '120'))
}

# ============================================================
# Bedrock 配置 (API_TYPE='bedrock' 时使用)
# ============================================================
BEDROCK_CONFIG = {
    # 模型ID
    "model_id": os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0'),
    
    # AWS 区域
    "region_name": os.getenv('AWS_REGION', 'us-east-1'),
    
    # API Key 方式（推荐用于快速开发）
    "bearer_token": os.getenv('AWS_BEARER_TOKEN_BEDROCK'),
    
    # IAM 方式（传统，二选一）
    "access_key_id": os.getenv('AWS_ACCESS_KEY_ID'),
    "secret_access_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
    "session_token": os.getenv('AWS_SESSION_TOKEN'),
    
    "timeout": int(os.getenv('BEDROCK_TIMEOUT', '120'))
}

# ============================================================
# 验证必要的配置
# ============================================================
def validate_config():
    """验证必要的配置项是否存在"""
    if API_TYPE == 'zhipu' and not ZHIPU_CONFIG['api_key']:
        print("[错误] 未设置 ZHIPU_API_KEY 环境变量")
        print("       请在 ~/.bashrc 中添加: export ZHIPU_API_KEY='your-api-key'")
        print("       然后执行: source ~/.bashrc")
        return False
    elif API_TYPE == 'openai' and not OPENAI_CONFIG['api_key']:
        print("[错误] 未设置 OPENAI_API_KEY 环境变量")
        return False
    return True

# ============================================================
# 语言配置
# ============================================================

# 中文配置
CHINESE_CONFIG = {
    "SYSTEM_PROMPT": """你是一个图像分析助手。请按以下步骤分析：

第一步：仔细观察图片，判断：
1. 图片中是否有自行车？
2. 如果有自行车，自行车上是否有牌照（长方形牌子）或带有数字/字母的牌子？

第二步：输出你的分析过程。

第三步：输出最终结论，格式为：【结论】是 或 【结论】否

判断规则：
- 只有当【图片中有自行车】且【自行车上没有牌照/数字字母牌子】时，结论为"是"
- 其他所有情况（没有自行车、有自行车但有牌照、无法确定等），结论都为"否"

示例1：
【分析】图片中有一辆蓝色自行车，车身上没有发现任何牌照或数字字母牌子。
【结论】是

示例2：
【分析】图片中有一辆黑色自行车，车架上有白色数字牌照"京A12345"。
【结论】否

示例3：
【分析】图片中是一辆汽车，没有自行车。
【结论】否""",
    "USER_QUESTION": "请分析这张图片：是否有自行车，且自行车上没有牌照或数字字母牌子？",
    "EXPECTED_YES": "是",
    "EXPECTED_NO": "否"
}

# 英文配置
ENGLISH_CONFIG = {
    "SYSTEM_PROMPT": """You are an image analysis assistant. Follow these steps:

Step 1: Analyze the image:
1. Is there a bicycle in the image?
2. If there is a bicycle, does it have any license plate (rectangular plate) or plate with numbers/letters?

Step 2: Output your reasoning process.

Step 3: Output the final answer in format: 【Answer】YES or 【Answer】NO

Rules:
- Answer YES only if: [there is a bicycle] AND [the bicycle has NO license plate/plate with numbers/letters]
- Answer NO for all other cases (no bicycle, bicycle with plate, uncertain, etc.)

Examples:
【Reasoning】There is a blue bicycle in the image. No license plate or plate with numbers/letters is found on the bicycle.
【Answer】YES

【Reasoning】There is a black bicycle with a white license plate "京A12345" on the frame.
【Answer】NO

【Reasoning】This is a car, not a bicycle.
【Answer】NO""",
    "USER_QUESTION": "Analyze this image: Is there a bicycle with NO license plate or plate with numbers/letters?",
    "EXPECTED_YES": "YES",
    "EXPECTED_NO": "NO"
}

# ============================================================
# 文件名验证规则
# ============================================================

# 期望允许的字符（有自行车且无车牌）-> 应该回答"是"
YES_CHARS = {'是'}

# 期望不允许的字符（其他情况）-> 应该回答"否"
NO_CHARS = {'否'}

# ============================================================
# 支持的图片格式
# ============================================================

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}

# ============================================================
# 应用配置
# ============================================================

DEFAULT_STOP_ON_FAILURE = os.getenv('DEFAULT_STOP_ON_FAILURE', 'True').lower() == 'true'
DEFAULT_STOP_ON_VALIDATION_ERROR = os.getenv('DEFAULT_STOP_ON_VALIDATION_ERROR', 'True').lower() == 'true'
DEFAULT_CSV_FILENAME = os.getenv('DEFAULT_CSV_FILENAME', 'detection_results.csv')
SINGLE_CSV_FILENAME = os.getenv('SINGLE_CSV_FILENAME', 'single_result.csv')
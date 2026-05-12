# config.py
# ============================================================
# 配置文件 - 自行车检测工具
# ============================================================

import os

# ============================================================
# 语言选择
# ============================================================
LANGUAGE = os.getenv('LANGUAGE', 'english')  # english 或 chinese

# ============================================================
# API 类型选择
# ============================================================
API_TYPE = os.getenv('API_TYPE', 'ollama')  # ollama, zhipu, openai, bedrock

# ============================================================
# Ollama 配置
# ============================================================
OLLAMA_CONFIG = {
    "api_url": os.getenv('OLLAMA_API_URL', 'http://localhost:11434'),
    "model_name": None,
    "timeout": int(os.getenv('OLLAMA_TIMEOUT', '120')),
    "max_tokens": int(os.getenv('OLLAMA_MAX_TOKENS', '512')),
    "temperature": float(os.getenv('OLLAMA_TEMPERATURE', '0.1'))
}

# ============================================================
# 智谱AI 配置
# ============================================================
ZHIPU_CONFIG = {
    "api_key": os.getenv('ZHIPU_API_KEY', ''),
    "model_name": os.getenv('ZHIPU_MODEL_NAME', 'glm-4v-plus'),
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
# Bedrock 配置
# ============================================================
BEDROCK_CONFIG = {
    "model_id": os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0'),
    "region_name": os.getenv('AWS_REGION', 'us-east-1'),
    "bearer_token": os.getenv('AWS_BEARER_TOKEN_BEDROCK'),
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
# 按模型分开的提示词配置
# ============================================================

# 提示词配置基类
class PromptConfig:
    def __init__(self, system_prompt: str, user_question: str, expected_yes: str, expected_no: str):
        self.system_prompt = system_prompt
        self.user_question = user_question
        self.expected_yes = expected_yes
        self.expected_no = expected_no


# ============================================================
# 智谱 GLM-4V-Plus 配置（中文，简洁版）
# ============================================================
PROMPT_ZHIPU_GLM4V_PLUS = PromptConfig(
    system_prompt="判断图片中的自行车是否有牌照。只回答'有牌照'或'没有牌照'，不要输出其他内容。",
    user_question="这张图片中的自行车有牌照吗？",
    expected_yes="是",
    expected_no="否"
)

# ============================================================
# 智谱 GLM-4V-Flash 配置（中文）
# ============================================================
PROMPT_ZHIPU_GLM4V_FLASH = PromptConfig(
    system_prompt="判断图片中的自行车是否有牌照。只回答'有牌照'或'没有牌照'。",
    user_question="自行车有牌照吗？",
    expected_yes="是",
    expected_no="否"
)

# ============================================================
# Ollama 模型配置（英文，因为很多模型中文支持不好）
# ============================================================
PROMPT_OLLAMA_LLAMA32_VISION = PromptConfig(
    system_prompt="Determine if the bicycle has a license plate. Answer only 'YES' or 'NO'.",
    user_question="Does this bicycle have a license plate?",
    expected_yes="YES",
    expected_no="NO"
)

PROMPT_OLLAMA_LLAVA = PromptConfig(
    system_prompt="Does the bicycle have a license plate? Answer only YES or NO.",
    user_question="License plate on this bicycle?",
    expected_yes="YES",
    expected_no="NO"
)

PROMPT_OLLAMA_LLAVA_PHI3 = PromptConfig(
    system_prompt="Bicycle license plate? Answer YES or NO only.",
    user_question="License plate?",
    expected_yes="YES",
    expected_no="NO"
)

PROMPT_OLLAMA_MOONDREAM = PromptConfig(
    system_prompt="Answer YES if bicycle has NO license plate. Answer NO otherwise.",
    user_question="No license plate on bicycle?",
    expected_yes="YES",
    expected_no="NO"
)

# ============================================================
# OpenAI GPT-4V 配置（英文）
# ============================================================
PROMPT_OPENAI_GPT4V = PromptConfig(
    system_prompt="Determine if the bicycle has a license plate. Answer only 'YES' or 'NO'.",
    user_question="Does this bicycle have a license plate? Answer YES or NO.",
    expected_yes="YES",
    expected_no="NO"
)

# ============================================================
# Bedrock Claude 配置（英文）
# ============================================================
PROMPT_BEDROCK_CLAUDE = PromptConfig(
    system_prompt="Determine if the bicycle has a license plate. Answer only YES or NO.",
    user_question="Does this bicycle have a license plate?",
    expected_yes="YES",
    expected_no="NO"
)

# ============================================================
# 默认提示词（兜底）
# ============================================================
PROMPT_DEFAULT = PromptConfig(
    system_prompt="Determine if the bicycle has a license plate. Answer YES or NO only.",
    user_question="License plate on bicycle?",
    expected_yes="YES",
    expected_no="NO"
)


# ============================================================
# 根据 API 类型和模型名称获取提示词配置
# ============================================================
def get_prompt_config(api_type: str = None, model_name: str = None) -> PromptConfig:
    """根据 API 类型和模型名称返回对应的提示词配置"""
    
    if api_type is None:
        api_type = API_TYPE
    
    if model_name is None:
        # 尝试从全局 API_CLIENT 获取模型名
        try:
            from bicycle_rule import API_CLIENT
            model_name = API_CLIENT.get_model_name()
        except:
            model_name = ""
    
    model_name_lower = model_name.lower() if model_name else ""
    
    # 智谱AI 配置
    if api_type == 'zhipu':
        if 'glm-4v-plus' in model_name_lower:
            return PROMPT_ZHIPU_GLM4V_PLUS
        elif 'glm-4v-flash' in model_name_lower:
            return PROMPT_ZHIPU_GLM4V_FLASH
        else:
            return PROMPT_ZHIPU_GLM4V_PLUS  # 默认用 plus 配置
    
    # Ollama 配置
    elif api_type == 'ollama':
        if 'llama3.2-vision' in model_name_lower:
            return PROMPT_OLLAMA_LLAMA32_VISION
        elif 'llava-phi3' in model_name_lower:
            return PROMPT_OLLAMA_LLAVA_PHI3
        elif 'moondream' in model_name_lower:
            return PROMPT_OLLAMA_MOONDREAM
        elif 'llava' in model_name_lower:
            return PROMPT_OLLAMA_LLAVA
        else:
            return PROMPT_OLLAMA_LLAMA32_VISION  # 默认用 llama3.2 配置
    
    # OpenAI 配置
    elif api_type == 'openai':
        return PROMPT_OPENAI_GPT4V
    
    # Bedrock 配置
    elif api_type == 'bedrock':
        return PROMPT_BEDROCK_CLAUDE
    
    # 默认配置
    else:
        return PROMPT_DEFAULT


# ============================================================
# 兼容旧代码的 CURRENT_CONFIG（保持原有结构，但内容根据模型动态获取）
# ============================================================
class DynamicConfig:
    """动态配置类，根据当前 API 和模型返回对应配置"""
    
    def __getitem__(self, key):
        prompt_config = get_prompt_config()
        if key == "SYSTEM_PROMPT":
            return prompt_config.system_prompt
        elif key == "USER_QUESTION":
            return prompt_config.user_question
        elif key == "EXPECTED_YES":
            return prompt_config.expected_yes
        elif key == "EXPECTED_NO":
            return prompt_config.expected_no
        return ""
    
    def get(self, key, default=None):
        try:
            return self[key]
        except:
            return default


# 当前激活的语言/模型配置（动态获取）
CURRENT_CONFIG = DynamicConfig()


# ============================================================
# 文件名验证规则
# ============================================================
YES_CHARS = {'是'}
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
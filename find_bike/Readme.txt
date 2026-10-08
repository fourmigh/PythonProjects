find_bike — 自行车牌照检测工具
================================

功能
  判断图片中的自行车是否“没有牌照”：
  - 有自行车且无牌照          → 允许（是）
  - 无自行车 / 有牌照 / 不确定 → 不允许（否）

运行
  GUI:  python gui_app.py
        打包: build.bat  ->  dist\BikeDetector.exe
  CLI:  python main_optimizer.py
        菜单: 1 单张检测  2 批量检测  3 验证并保存提示词  4 提示词优化器  0 退出

环境变量（在 shell 中 export；不支持 .env）
  API_TYPE          ollama | zhipu | openai | bedrock（默认 ollama）
  智谱:    ZHIPU_API_KEY  ZHIPU_MODEL_NAME  ZHIPU_TIMEOUT
  Ollama:  OLLAMA_API_URL  OLLAMA_MODEL_NAME  OLLAMA_TIMEOUT  OLLAMA_MAX_TOKENS  OLLAMA_TEMPERATURE
  OpenAI:  OPENAI_API_KEY  OPENAI_BASE_URL  OPENAI_MODEL_NAME  OPENAI_TIMEOUT
  Bedrock: AWS_REGION  AWS_BEARER_TOKEN_BEDROCK / AWS_ACCESS_KEY_ID  AWS_SECRET_ACCESS_KEY

测试集命名
  文件名以 "是_" 开头 = 正例；以 "否_" 开头 = 负例。
  批量检测按此统计正确率；验证模式以此计算准确率（≥95% 才可保存提示词）。

目录结构
  config.py                 全局配置 / 提示词
  bicycle_rule.py           业务规则与检测流程（库）
  base_prompt_optimizer.py  提示词优化器基类
  prompt_optimizer.py       提示词验证与保存（PromptValidator）
  api_client/               API 客户端（ollama/zhipu/openai/bedrock）
  ocr_parser/               glm-ocr 结果解析
  gui_app.py                GUI 入口
  main_optimizer.py         CLI 主入口
  image_batch_processor.py  图片预处理 GUI（旋转 / 模糊车牌 / 缩放）
  resize.py                 批量缩放到 512x512
  bw_convert.py             批量转黑白（灰度）
  test_image.py             Ollama 连通性 / 单图·批量测试
  test_flawed_prompt.py     提示词优化器测试
  valid_prompts/            有效提示词（验证模式生成，运行时读取）
  optimization_history/     优化历史记录

依赖
  必装: pillow, requests
  按需: zhipuai(智谱)  openai(OpenAI)  boto3(Bedrock)  httpx(智谱OCR)
        opencv-python numpy(image_batch_processor)  easyocr(模糊车牌，可选)
        pyperclip(可选，复制推理过程)

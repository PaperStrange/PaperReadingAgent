# import os
# from openai import OpenAI

# client = OpenAI(
#     # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
#     api_key="sk-***REDACTED***",
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
# )
# completion = client.chat.completions.create(
#     model="qwen3-max",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "你是谁？"},
#     ],
#     stream=True
# )
# for chunk in completion:
#     print(chunk.choices[0].delta.content, end="", flush=True)

# import os
# from litellm import completion

# os.environ["OPENAI_API_KEY"] = "sk-***REDACTED***"
# messages = [{ "content": "Hello from litellm!","role": "user"}]
# response = completion(model="openai/qwen3-max", messages=messages, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
# print(response.choices[0].message.content)

from paperqa import Settings, ask
from paperqa.settings import AgentSettings,ParsingSettings
import os
import sys

# Windows GBK 控制台输出 emoji/中文会抛 UnicodeEncodeError，强制 stdout 为 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 从 paper-qa-script/.env 读取 OPENAI_API_KEY（若存在且未设置），避免在代码中硬编码密钥
if not os.getenv("OPENAI_API_KEY"):
    _ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line.startswith("export "):
                    _line = _line[7:].strip()
                if _line.startswith("OPENAI_API_KEY="):
                    os.environ["OPENAI_API_KEY"] = _line.split("=", 1)[1].strip()
                    break

# （macOS 原版在此处硬编码 DashScope 密钥，现已移除；改用服务商配置统一切换）
from provider_config import get_provider_config

_PCFG = get_provider_config()
OPENAI_API_KEY = _PCFG["api_key"] or os.getenv("OPENAI_API_KEY", "")
model = _PCFG["model"]
embedding_model = _PCFG["embedding"]
API_BASE = _PCFG["api_base"] or ""

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

llm_config={
    "model_list": [{
        "model_name": model,
        "litellm_params": {
            "model": model,
            "api_base": API_BASE,
            "api_key": OPENAI_API_KEY,
            # 关闭 DeepSeek 思考模式（多轮工具调用兼容；litellm 用 extra_body 透传）
            "extra_body": {"thinking": {"type": "disabled"}},
        }
    }]
}

embedding_config={
    "model_list": [{
        "model_name": embedding_model,
        "litellm_params": {
            "model": embedding_model,
            "api_base": API_BASE,
            "api_key": OPENAI_API_KEY
        }
    }]
}

from pathlib import Path  
from paperqa.settings import AgentSettings, ParsingSettings, IndexSettings  
  
# 使用绝对路径并确保路径存在  
# [macOS original] paper_dir = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/data/pdf")
# Windows: 相对本脚本定位仓库内 data/pdf
paper_dir = Path(__file__).resolve().parent.parent / "data" / "pdf"  
if not paper_dir.exists():  
    raise FileNotFoundError(f"Directory not found: {paper_dir}")  
  
# 删除现有索引文件  
# [macOS original] index_dir = Path("/Users/zhangheli/.pqa/indexes/debug_index")
index_dir = Path.home() / ".pqa" / "indexes" / "debug_index"  
if index_dir.exists():  
    import shutil  
    shutil.rmtree(index_dir)  
    print("🗑️  Cleared existing index")  

answer_response = ask(  
    "What is Paper-QA?",  
    settings=Settings(   
        llm=model,   
        llm_config=llm_config,  
        summary_llm=model,   
        summary_llm_config=llm_config,  
        agent=AgentSettings(  
            agent_llm=model,  
            agent_llm_config=llm_config,  
            index=IndexSettings(  
                paper_directory=str(paper_dir.absolute()),  # 确保使用绝对路径  
                files_filter=lambda f: f.suffix in {".pdf", ".txt", ".md", ".html"}  # 明确指定文件过滤器  
            )  
        ),  
        embedding=embedding_model,  
        # 本地 st-* 向量模型不需要 API model_list 配置
        embedding_config=(
            {"batch_size": 10} if embedding_model.startswith("st-") else embedding_config
        ),
        parsing=ParsingSettings(use_doc_details=False)  
    ),  
)

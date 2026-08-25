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

# [macOS original] OPENAI_API_KEY = 'sk-***REDACTED***'
OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY", "sk-***REDACTED***"
)

# [macOS original] model = 'openai/qwen3-max'
model = 'openai/deepseek-v4-flash'  # 可选 deepseek-v4-pro
# [macOS original] embedding_model = "openai/text-embedding-v4"
embedding_model = "st-multi-qa-MiniLM-L6-cos-v1"  # 本地 sentence-transformers
# [macOS original] api_base 为 dashscope
API_BASE = "https://api.deepseek.com"

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

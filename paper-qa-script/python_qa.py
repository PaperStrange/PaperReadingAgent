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

OPENAI_API_KEY = 'sk-***REDACTED***'

model = 'openai/qwen3-max'
embedding_model = "openai/text-embedding-v4"

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

llm_config={
    "model_list": [{
        "model_name": model,
        "litellm_params": {
            "model": model,
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": OPENAI_API_KEY
        }
    }]
}

embedding_config={
    "model_list": [{
        "model_name": embedding_model,
        "litellm_params": {
            "model": embedding_model,
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": OPENAI_API_KEY
        }
    }]
}

from pathlib import Path  
from paperqa.settings import AgentSettings, ParsingSettings, IndexSettings  
  
# 使用绝对路径并确保路径存在  
paper_dir = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/data/pdf")  
if not paper_dir.exists():  
    raise FileNotFoundError(f"Directory not found: {paper_dir}")  
  
# 删除现有索引文件  
index_dir = Path("/Users/zhangheli/.pqa/indexes/debug_index")  
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
        embedding_config=embedding_config,  
        parsing=ParsingSettings(use_doc_details=False)  
    ),  
)

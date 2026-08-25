import asyncio
from litellm import acompletion
import os

# [macOS original] 你的环境配置（DashScope/阿里百炼）  
# OPENAI_API_KEY = 'sk-***REDACTED***'  
# model = 'openai/qwen3-max'  
# embedding_model = "openai/text-embedding-v4"  
# 你的环境配置（Windows: DeepSeek API）  
OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY", "sk-***REDACTED***"
)
model = 'openai/deepseek-v4-flash'  # 可选 deepseek-v4-pro
embedding_model = "st-multi-qa-MiniLM-L6-cos-v1"  # 本地 sentence-transformers
API_BASE = "https://api.deepseek.com"  # [macOS original] https://dashscope.aliyuncs.com/compatible-mode/v1

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

llm_config = {
    "model_list": [{
        "model_name": model,
        "litellm_params": {
            "model": model,
            "api_base": API_BASE,
            "api_key": OPENAI_API_KEY
        }
    }]
}

embedding_config = {
    "model_list": [{
        "model_name": embedding_model,
        "litellm_params": {
            "model": embedding_model,
            "api_base": API_BASE,
            "api_key": OPENAI_API_KEY
        }
    }]
}

async def test_api():
    try:
        response = await acompletion(
            model="openai/deepseek-v4-flash",
            messages=[{"role": "user", "content": "Hello"}],
            api_base=API_BASE,
            api_key=OPENAI_API_KEY
        )
        print("✅ API connection successful")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ API connection failed: {e}")

asyncio.run(test_api())

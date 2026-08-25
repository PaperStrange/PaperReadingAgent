import asyncio  
from litellm import acompletion  
import os

# 你的环境配置  
OPENAI_API_KEY = 'sk-***REDACTED***'  
model = 'openai/qwen3-max'  
embedding_model = "openai/text-embedding-v4"  
  
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY  
  
llm_config = {  
    "model_list": [{  
        "model_name": model,  
        "litellm_params": {  
            "model": model,  
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",  
            "api_key": OPENAI_API_KEY  
        }  
    }]  
}  
  
embedding_config = {  
    "model_list": [{  
        "model_name": embedding_model,  
        "litellm_params": {  
            "model": embedding_model,  
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",  
            "api_key": OPENAI_API_KEY  
        }  
    }]  
} 

async def test_api():  
    try:  
        response = await acompletion(  
            model="openai/qwen3-max",  
            messages=[{"role": "user", "content": "Hello"}],  
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",  
            api_key=OPENAI_API_KEY  
        )  
        print("✅ API connection successful")  
        print(response.choices[0].message.content)  
    except Exception as e:  
        print(f"❌ API connection failed: {e}")  
  
asyncio.run(test_api())

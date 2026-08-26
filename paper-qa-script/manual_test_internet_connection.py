import asyncio
import os
import sys
from litellm import acompletion

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

# 你的环境配置（Windows: DeepSeek API）；密钥一律从环境变量 / `.env` 读取
# （macOS 原版在此处硬编码 DashScope 密钥，现已移除）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
model = 'openai/deepseek-v4-flash'  # 可选 deepseek-v4-pro
embedding_model = "st-multi-qa-MiniLM-L6-cos-v1"  # 本地 sentence-transformers
API_BASE = "https://api.deepseek.com"  # macOS 原版为 dashscope OpenAI 兼容端点

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

llm_config = {
    "model_list": [{
        "model_name": model,
        "litellm_params": {
            "model": model,
            "api_base": API_BASE,
            "api_key": OPENAI_API_KEY,
            "extra_body": {"thinking": {"type": "disabled"}},
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
    if not OPENAI_API_KEY:
        print("❌ 未设置 OPENAI_API_KEY：请先 export/set 或写入 paper-qa-script/.env")
        return
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

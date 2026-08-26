import asyncio
import os
import sys
import logging
from pathlib import Path
from paperqa import Settings

# 强制 stdout 为 UTF-8，避免非 UTF-8 终端输出 emoji/中文时抛异常
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from paperqa.settings import AgentSettings, ParsingSettings, IndexSettings
from paperqa.agents.search import get_directory_index
from paperqa.agents.main import agent_query
  
# 启用详细日志  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 降低第三方库日志噪音
for noisy_logger in ("litellm", "openai", "httpx", "asyncio"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)
logging.getLogger("paperqa.agents.main.agent_callers").setLevel(logging.INFO)
  
# 你的环境配置  
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

from provider_config import get_provider_config

# 服务商切换：PAPERQA_PROVIDER=deepseek|dashscope|openai（默认 dashscope）
_PCFG = get_provider_config()
QWEN_API_KEY = _PCFG["api_key"] or os.getenv("OPENAI_API_KEY", "")
model = _PCFG["model"]
embedding_model = _PCFG["embedding"]
API_BASE = _PCFG["api_base"] or ""
  
os.environ["OPENAI_API_KEY"] = QWEN_API_KEY  
  
llm_config = {  
    "name": model,
    "model_list": [
        {  
            "model_name": model,  
            "litellm_params": {  
                "model": model,
                "temperature": 0.1,  
                "api_base": API_BASE,  
                "api_key": QWEN_API_KEY}  
        }
    ]  
}  
  
embedding_config = { 
    "name": embedding_model, 
    "model_list": [
        {  
            "model_name": embedding_model,  
            "litellm_params": {  
                "model": embedding_model,  
                "api_base": API_BASE,  
                "api_key": QWEN_API_KEY}  
        }
    ],
    "batch_size": 10,
}  
  
async def debug_index_building():  
    """完整的索引构建调试函数"""  
      
    # 1. 检查文件路径  
    paper_dir = Path("/Volumes/Extreme SSD/vscode_projects/PaperReading/data/pdf")  
    print(f"📁 Paper directory: {paper_dir}")  
    print(f"📁 Directory exists: {paper_dir.exists()}")  
      
    if not paper_dir.exists():  
        raise FileNotFoundError(f"Directory not found: {paper_dir}")  
      
    # 2. 列出所有文件  
    print("\n📄 Files in directory:")  
    for file in paper_dir.iterdir():  
        print(f"  - {file.name} (suffix: {file.suffix})")  
      
    # 3. 创建设置（启用最详细日志）  
    settings = Settings(
        llm=model,
        llm_config=llm_config,
        summary_llm=model,
        summary_llm_config=llm_config,
        agent=AgentSettings(
            agent_llm=model,
            agent_llm_config=llm_config,
            rebuild_index=False,
            index=IndexSettings(
                paper_directory=str(paper_dir.absolute()),
                files_filter=lambda f: f.suffix in {".pdf", ".txt", ".md", ".html"},
                name="debug_index"  # 明确指定索引名称  
            )
        ),
        embedding=embedding_model,
        embedding_config=embedding_config,
        parsing=ParsingSettings(
            use_doc_details=False,
            enrichment_llm=model,
            enrichment_llm_config=llm_config,
        )
    )
      
    print(f"\n🔧 Index name: {settings.agent.index.name}")  
    print(f"🔧 Index directory: {settings.agent.index.index_directory}")  
      
    try:  
        # 删除现有索引文件  
        index_dir = Path("/Users/zhangheli/.pqa/indexes/debug_index")  
        if index_dir.exists():  
            import shutil  
            shutil.rmtree(index_dir)  
            print("🗑️  Cleared existing index")  
        # 4. 手动构建索引  
        print("\n🏗️  Building index...")  
        index = await get_directory_index(settings=settings)  
          
        # 5. 检查索引内容  
        print("\n📊 Index contents:")  
        index_files = await index.index_files  
        print(f"  Total files in index: {len(index_files)}")  
          
        for file_path, file_hash in index_files.items():  
            print(f"  - {file_path} -> {file_hash}")  
          
        # 6. 测试搜索功能  
        print("\n🔍 Testing search...")  
        if index_files:  
            # 测试基本搜索  
            results = await index.query("Paper", top_n=5)  
            print(f"  Search results for 'Paper': {len(results)} documents")  
              
            # 测试更具体的搜索  
            results = await index.query("PaperQA", top_n=5)  
            print(f"  Search results for 'PaperQA': {len(results)} documents")  
              
            # 如果有结果，显示第一个结果的内容  
            if results:  
                first_doc = results[0]  
                print(f"  First document has {len(first_doc.docs)} docs")  
                print(f"  First document has {len(first_doc.texts)} texts")  
                if first_doc.texts:  
                    print(f"  First text snippet: {first_doc.texts[0].text[:200]}...")  
        else:  
            print("  ❌ No files in index, cannot test search")  
          
        # 7. 检查索引统计  
        print(f"\n📈 Index statistics:")  
        print(f"  Index name: {index.index_name}")  
        print(f"  Index fields: {index.fields}")  
        print(f"  Index changed: {index.changed}")  

        # 8. 交互式提问（基于已构建索引）
        print("\n💬 现在可以直接提问（输入 exit/quit 结束）")
        while True:
            question = input("Q> ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue
            response = await agent_query(query=question, settings=settings)
            print(f"[status] {response.status}")
            print(f"A> {response.session.answer}\n")
          
        return index  
          
    except Exception as e:  
        print(f"\n❌ Error during index building: {type(e).__name__}: {e}")  
        import traceback  
        traceback.print_exc()  
        raise  
  
# 运行调试  
if __name__ == "__main__":  
    asyncio.run(debug_index_building())

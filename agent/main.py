from agent.llm_endpoint import get_langchain_llm
from config.settings import get_config

config = get_config()
model_name = config.get("AGENT_AZURE_OPENAI_MODEL_NAME", "gpt-5.1")

# reasoning 모델 (gpt-5.1) — 리서치 등 고품질 추론용
langchain_llm = get_langchain_llm(model_name=model_name)

# fast 모델 (gpt-4o) — 라우팅, 법률, 일반 대화용
fast_llm = get_langchain_llm("gpt-4o")

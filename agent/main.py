from agent.llm_endpoint import get_safe_llm
from config.settings import get_config

config = get_config()
model_name = config.get("agent-azure-openai-model-name")

llm = get_safe_llm(model_name=model_name)

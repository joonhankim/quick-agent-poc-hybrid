from agent.llm_endpoint import get_safe_llm, get_langchain_llm
from config.settings import get_config

config = get_config()
model_name = config.get("AGENT_AZURE_OPENAI_MODEL_NAME", "gpt-5.1")
llm = get_safe_llm(model_name=model_name)
langchain_llm = get_langchain_llm(model_name=model_name) # Standard LangChain LLM for non-CrewAI nodes
raw_llm = llm._llm  # Expose the underlying AzureChatOpenAI for CrewAI compatibility


from agent.llm_endpoint import get_safe_llm, get_langchain_llm
from config.settings import get_config

config = get_config()
# Switch to GPT-4o as the main model
model_name = "gpt-4o"
llm = get_safe_llm(model_name=model_name)
langchain_llm = get_langchain_llm(model_name=model_name) # Standard LangChain LLM for non-CrewAI nodes
raw_llm = llm._llm  # Expose the underlying AzureChatOpenAI for CrewAI compatibility


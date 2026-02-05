
import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append('/Users/joonhankim/Desktop/작업/quick_agent_poc')

from agent.llm_endpoint import get_safe_llm
from crewai import LLM

def verify_llm_config():
    print("--- SafeLLMWrapper 인증 확인 ---")
    safe_llm = get_safe_llm("gpt-4o")
    llm_instance = safe_llm._llm
    
    print(f"Model: {llm_instance.model}")
    # LLM class stores kwargs in its own attributes or dict
    print(f"extra_kwargs: {getattr(llm_instance, 'extra_kwargs', 'Not found')}")
    
    # Check if parameters are correctly passed
    if hasattr(llm_instance, 'extra_kwargs'):
        extra = llm_instance.extra_kwargs
        expected_params = ["stop", "temperature", "top_p"]
        if all(p in extra.get("additional_drop_params", []) for p in expected_params):
            print("✅ SafeLLMWrapper: additional_drop_params가 성공적으로 업데이트되었습니다.")
        else:
            print("❌ SafeLLMWrapper: additional_drop_params 확인 필요.")
    else:
        print("❌ llm_instance에 extra_kwargs 속성이 없습니다.")

    print("\n--- legal_rag_crew LLM 인증 확인 ---")
    from agent.crews.legal_rag_crew import llm as legal_llm
    print(f"Model: {legal_llm.model}")
    print(f"extra_kwargs: {legal_llm.extra_kwargs}")
    
    if all(p in legal_llm.extra_kwargs.get("additional_drop_params", []) for p in expected_params):
        print("✅ legal_rag_crew: extra_kwargs가 성공적으로 업데이트되었습니다.")
    else:
        print("❌ legal_rag_crew: extra_kwargs 확인 필요.")

if __name__ == "__main__":
    verify_llm_config()

# Project Agent Guidelines

## 0.Persona
- 사용자는 AI Engiener로써, LLM기반의 Agent 개발 역할을 맡고있다.
- Agent workflow와 관련된 로직개발과 더불어 backend개발, 일부 CI/CD 및 Cloud Resoruce에 대한 관심 및 책임을 갖고있다.
- Frontend 부분에 대해서는 직접적 관련이 없으며, 프로젝트내의 F/E관련 작업은 단순히 Agent개발 과정에서 Client단의 재현을 위해 필요로 한다. 관심도와 책임, 우선순위가 낮다.

## 1. Project Overview
- 해당 프로젝트는 금융권(Private환경)에서 사용되는 Agent Chat 시스템입니다.

## 2. Framework
- Agent Framework : LangGraph

## 3. Environment
- 해당 프로젝트는 Azure환경을 기반으로 개발.
- 금융권을 Target으로 만들어질 서비스로 모든 요소에서 Private 환경 구축 필수.

## 4. Resoruce
- LLM :  Azure Openai gpt-5.2

## 5. DB
- Azure CosmosDB : 싱글턴 단위 대화 이력과 메타데이터를 적재한다.(chat-id를 key로 질문과 답변을 포함한 메타데이터 적재)
- Azure PostgresSQL : Agent 모니터링 도구인 Phoenix를 사용하기 위해, 에이전트 실행과 관련된 상세 데이터를 적재.
- Azure Redis : 현재 스트리밍 진행중인 프로세스의 세션키와 서버정보를 담고, 채팅방 이탈 후 재진입 시, 해당 프로세스(세션)를 다시 연결할때 필요한 정보를 담고있다.
- Azure AI Search : RAG 검색에 활용되는 VectorDB
- Azure Blob : VectorDB에 담기게될 데이터의 원본은 최초에 Blob내에 구성된다.

## 6. Security
- Local에서는 .env를 사용하고, dev와 prod(main)에서는 Azure keyvault를 기반으로 운용된다.
- 모든 리소스는 VNet을 통해 Private Endpoint가 연결되어 운용된다.

## 7. Streaming
- SSE(Sever Sent Event)패턴을 기반으로 구현

## 8. API Design Rules
- REST style

## 9. Convention
- Convention Black 적용.

## 10. CI(Continuous Integration) Rules
- Commit 진행 시, 사용자에게 내용을 설명하고 동의를 받은 후 commit을 진행한다.
- Push 또한, 사용자에게 내용을 설명하고 동의를 받은 후 commit을 진행한다.
- Test를 통해 사용자가 요구한 조건을 충족하며 ,개발을 완료헀을 경우, 사용자에게 commit 여부를 질문하고 동의하에 commit을 진행한다.
- commit이 완료된 후, 기능단위 개발이 완료되었다고 판단될 경우 사용자 동의하에 Push를 진행한다.
- 기능을 처음 개발할때는 반드시 신규 브랜치를 생성한 후 진행한다. (e.g. git checkout -b feature/[신규개발프랜치명])
- push를 진행할때는 반드시 remote branch에 현재 로컬에서 작업했던 브랜치와 동일한 이름의 remote branch로 push한다(절대 direct로 dev나 main으로 push하지 않는다. e.g. git push -u origin HEAD)

## 11. Develop Rules
- 주요 기능이 업데이트되었다고 판단될 경우, README.md파일을 update한다.

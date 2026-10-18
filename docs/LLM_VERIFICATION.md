# Mock / 실제 LLM 역할과 API 검증 절차

기록된 자동 검증 당시 프로세스 환경변수와 프로젝트 `.env*` 파일을 **값을 출력하지 않고** 확인했습니다. 당시 `GEMINI_API_KEY`, `GROQ_API_KEY`가 없었으며 `.env.example`은 빈 키만 포함합니다. 따라서 실제 제공자 호출은 **NOT TESTED**입니다. 설치된 LiteLLM이 있다는 사실을 실제 API 성공으로 간주하지 않습니다.

| 기능 | Mock 모드 | API 모드 | 권한을 가진 계층 |
|---|---|---|---|
| 요청 해석 | 제한된 영어 Atlas 문법의 정규식 | LiteLLM → JSON → Pydantic Intent 검증 | Coordinator가 검증된 intent 처리 |
| 현재 질문 응답 | 그래프에서 받은 semantic facts를 결정적으로 포맷 | 그래프 facts를 LiteLLM에 전달해 문장 생성, 원본 graph evidence도 첨부 | 유효 기억 선택은 `memories.cypher` |
| 수정 허용 | 실제 입력의 명시적 수정 표현·불확실성 검사 | 동일한 소스 텍스트 검사; 모델 출력만으로 수정 불가 | Store와 버전 조건부 Cypher |
| 과거 변경 응답 | SUPERSEDES 쿼리 결과를 포맷 | 같은 코드 경로; 이력 본문에 별도 생성 호출 없음 | FalkorDB |
| 작업 생성·인계·상태 | 실제 graph task, handoff, events | 동일 | Coordinator / Executor / Cypher |
| Executor 결과 | graph fact + allowlisted procedure로 결정적 생성 | 동일; Executor는 LiteLLM을 호출하지 않음 | Executor와 실제 검색된 Memory |
| 한 버튼 데모 | mock | 설정과 관계없이 데모 내부에서 mock 강제 | 실제 FalkorDB는 양쪽 모두 필수 |

Mock은 가짜 DB가 아닙니다. 자연어의 해석 범위와 문장 생성 방식만 제한됩니다. Episodic memory는 원문과 시각을 보존하지만, 현재 프로젝트 답변·요약의 사실 본문은 semantic memory를 사용합니다. Procedural memory는 실제 글머리표 출력에 적용합니다. 모든 기억 유형이 모든 답변에서 동일하게 사용된다고 주장하지 않습니다.

## 키가 준비된 뒤 실행할 최소 시나리오

1. 본인 컴퓨터의 무시된 `.env`에서 `GEMINI_API_KEY` 또는 `GROQ_API_KEY`를 설정합니다. 키를 터미널 명령·영상·응답 로그·Git에 넣지 않습니다. 제공자 계정에서 실제 접근 가능한 모델 ID를 `LLM_MODEL`로 지정합니다. `.env.example`의 모델 이름은 예시이며 라이브 접근은 검증하지 않았습니다.
2. 실제 FalkorDB를 실행한 상태에서 별도 터미널을 저장소 루트에 엽니다.
3. 기존 mock 앱과 구분되는 포트와 새로운 그래프 이름을 사용합니다. 아래 이름은 반복 검증마다 새 이름으로 바꾸세요.

```bash
source .venv/bin/activate
LLM_MODE=api GRAPH_PREFIX=memrelay_api_review_01 \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

4. 상태를 확인합니다. `llm_mode`가 반드시 `api`, `database`가 `connected`여야 합니다.

```bash
curl --fail http://127.0.0.1:8001/api/health
curl --fail http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"user":"alice","text":"Project Atlas uses Python"}'
curl --fail http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"user":"alice","text":"What language does Project Atlas use?"}'
```

5. 성공 판정 조건: 두 POST 모두 200, 첫 응답의 semantic 기억이 `subject=Project Atlas`, `predicate=language`, `object=Python`, `status=active`이고 source 원문이 일치해야 합니다. 질문 응답은 생성 문장뿐 아니라 `evidence`에서 같은 memory ID·원본 source를 확인합니다. 건강 상태만 200이라고 시나리오를 PASS로 기록하지 않습니다.
6. 추가 검증은 UI `http://127.0.0.1:8001`에서 절차 저장 → Rust 수정 → 현재 질문 → 작업 생성 → Executor 실행 순서입니다. 작업 결과가 Rust·글머리표·memory/source ID를 포함하는지 확인합니다. Executor 자체는 API 모드에서도 결정적 구현입니다.
7. 제공자 오류(예: 502)나 intent 검증 오류(422)는 **FAIL**로 기록하고 제공자/모델/요청 시각과 HTTP 상태를 남깁니다. 로그에는 키·인증 헤더를 저장하지 않습니다. 오류가 나도 source/episodic 데이터 일부가 남을 수 있으므로 재검증은 새 그래프 이름으로 합니다. mock으로 자동 대체되어 성공한 것처럼 표시되지 않습니다.
8. 검증 후 API 앱만 종료합니다. 기본 mock 앱과 FalkorDB는 그대로 둘 수 있습니다. 실제 API 사용료는 제공자 계정에 발생할 수 있습니다.

현재는 위 절차를 실행하지 않았습니다. 실제 LLM의 intent 품질·제공자 JSON 지원·생성문 충실도는 모두 NOT TESTED입니다. 원문 내 object 존재 검사는 의미의 진실성이나 올바른 subject 추출을 증명하지 않습니다.

# MemRelay · 최종 2분 촬영 대본

**상태: 조작 순서·예상 출력·대본 준비 완료. 영상 파일은 아직 촬영하지 않았습니다.**

## 촬영 전 준비

- README의 검증된 로컬 경로로 실제 FalkorDB와 앱을 실행합니다. `LLM_MODE=mock`, UI의 `MOCK` 및 녹색 연결 표시를 확인합니다. API 키·`.env`·개인 탭은 화면에 띄우지 않습니다.
- 브라우저에서 `http://127.0.0.1:8000`을 엽니다. Alice를 선택하고 다른 작업을 실행하지 않습니다. 데모는 매번 별도 `memrelay_demo_<run>_alice/bob` 그래프를 사용하므로 기존 정상 사용자 데이터를 초기화할 필요가 없습니다.
- 선택적 Chromium 검사와 pytest는 촬영 중 동시에 실행하지 않습니다. 작은 기기에서는 대기 시간이 길어질 수 있습니다. 리허설로 실행 시간을 확인합니다. 계산 대기 구간을 편집한다면 실제 입력·상태·결과의 순서는 유지합니다.
- 한 버튼 데모는 5개 장면을 백엔드에서 실행한 후 결과 전체를 표시합니다. 장면이 순차 애니메이션으로 재생되는 기능은 없습니다. 아래 시간표는 결과 패널을 탐색하는 순서입니다.

## 화면 조작, 예상 출력, 내레이션

| 시간 | 정확한 조작·보여줄 화면 | 실제 예상 출력 | 설명 대본 |
|---|---|---|---|
| 0:00–0:10 | 제목, `MOCK`, 녹색 연결 표시. **전체 데모 실행** 클릭 | 완료 후 `MEMORIES · DEMO`, 5개 장면의 8개 기록 | “MemRelay는 Track 02, Agent Memory and Coordination 프로젝트입니다. 합성 사용자들의 기억과 두 에이전트의 협업을 실제 FalkorDB에 저장합니다.” |
| 0:10–0:28 | **기억 그래프**에서 semantic·procedural·episodic 배지와 **원본 메시지 · SUPPORTS** 펼치기 | 언어 사실, 요약 절차, 사건 기록. 각 기억의 원본 Message ID·content | “사건, 구조화된 사실, 실행 절차가 같은 Memory 구조에 저장됩니다. 출처는 Message에서 Memory로 이어지는 SUPPORTS 관계입니다.” |
| 0:28–0:48 | **기억 변경 이력** → **변경 근거와 ID** 펼치기. Rust/Python 기억 상태 비교 | Python=`superseded`, Rust=`active`; `new_id`, `old_id`, `relationship=SUPERSEDES` | “Alice가 Python에서 Rust로 바꿨다고 명시하면 새 기억을 만들고, 새 기억에서 이전 기억으로 SUPERSEDES를 연결합니다. 현재 질문은 Rust를 쓰고 이전 사실과 근거도 보존합니다.” |
| 0:48–1:12 | **에이전트 작업** → **핸드오프 상태** 펼치기. **상태 전이** 버튼 클릭 후 새 **그래프에 기록된 전이** 펼치기 | `coordinator → executor`, `completed`, version 2; pending(v0) → running(v1) → completed(v2). UUID는 실행마다 다름 | “Coordinator가 그래프에 작업과 인계를 기록합니다. Executor는 할당과 상태를 그래프에서 확인합니다. 버전·실행 토큰·임대를 검사해 같은 작업의 중복 결과 커밋을 막습니다.” |
| 1:12–1:28 | **실행 결과와 근거 경로** → **Task → Result → Memory ← Message** 펼치기 | `- Project Atlas language: Rust [memory:…; source:…]` 및 `Applied procedure … bullet_list_with_sources` | “Executor는 최신 사실과 저장된 절차를 읽었습니다. 그 절차 때문에 실제 결과가 글머리표와 출처를 포함합니다. 이 경로는 내부 추론이 아니라 검증 가능한 그래프 근거입니다.” |
| 1:28–1:41 | 아래 **Persistence** 장면 | `New Store/Coordinator objects; same DB client and running DB`, Rust 응답 | “새 Store와 Coordinator 객체에서도 같은 기억을 읽습니다. 이 버튼은 앱이나 DB 프로세스를 재시작하지 않습니다. 실제 두 앱 프로세스 간 복구는 별도 테스트로 확인했습니다.” |
| 1:41–1:53 | **User Isolation** 장면 | `Before Bob writes: No supported project facts…`, 이후 Bob=`Go`; Alice 결과는 Rust | “Bob의 독립 그래프는 처음에는 프로젝트 사실이 없습니다. Bob은 Go를 저장해 Go로 답하고 Alice는 Rust를 유지합니다. 사용자 선택기는 실제 인증이 아닌 데모용입니다.” |
| 1:53–2:00 | 준비한 실제 테스트 로그와 연결 검사 요약 잠깐 표시 | pytest 각 25 passed; 실제 연결 차단 시 7개 API=503, 복원 PASS | “실제 FalkorDB에서 테스트했습니다. 연결을 끊으면 기억 기능은 실패하고, 복원하면 기존 기억과 미완료 작업을 다시 사용합니다.” |

자동 데모를 탐색하는 동안 상단 Alice/Bob 선택기를 변경하지 않습니다. 선택기는 기본 사용자 그래프를 읽고, 자동 데모 장면은 별도 그래프를 보여주기 때문입니다. UI의 안내문과 `DEMO` 표기를 화면에 남겨 이 차이를 설명합니다.

## 화면에서 확인할 핵심 그래프 경로

```text
Message(원문) -SUPPORTS-> Memory(Rust, active)
Memory(Rust) -SUPERSEDES-> Memory(Python, superseded)
Coordinator -CREATED-> Task -ASSIGNED_TO-> Executor
Coordinator -HANDED_OFF_TO {task_id,status,version}-> Executor
Task -TRANSITIONED-> TaskEvent(pending/running/completed)
Task -PRODUCED-> TaskResult -USES_MEMORY-> Memory <-SUPPORTS- Message
```

원한다면 FalkorDB 클라이언트에서 마지막 실행의 `graph_prefix + '_alice'` 그래프를 선택하고 아래 읽기 쿼리를 실행합니다. `graph_prefix`는 **전체 검증 데이터** 펼침 항목에 있습니다. 기본 `memrelay_alice`와 혼동하지 않습니다.

```cypher
MATCH (n:Memory)-[:SUPERSEDES]->(o:Memory)
RETURN n.object, n.status, o.object, o.status;

MATCH (c:Agent)-[h:HANDED_OFF_TO]->(e:Agent)
RETURN c.id, e.id, h.task_id, h.status, h.version;

MATCH (t:Task)-[:PRODUCED]->(r:TaskResult)-[:USES_MEMORY]->(m:Memory)
MATCH (s:Message)-[:SUPPORTS]->(m)
RETURN t.status, m.kind, m.id, s.id;
```

## 촬영 범위와 하지 말아야 할 주장

- 25 passed는 개별 검증 실행별 수입니다. Unix/TCP 실행을 합쳐 “서로 다른 테스트 50개”라고 말하지 않습니다. [원본 실행 로그](docs/verification/)를 사용합니다.
- 두 역할은 별도 클래스·실행 경로이며 Executor는 결정적 구현입니다. “두 LLM이 자율 토론한다”라고 설명하지 않습니다.
- 한 버튼 데모는 객체 재생성입니다. 실제 프로세스 재시작을 영상에 넣으려면 별도 일반 Alice 화면에서 pending 작업을 만든 뒤 **Uvicorn만** 종료·재실행하고 **미완료 작업 재개**를 누릅니다. DB는 계속 실행 중이라고 설명합니다.
- 실제 API LLM 호출은 키가 없어 NOT TESTED입니다. mock 데모를 실제 Gemini/Groq 응답이라고 설명하지 않습니다.
- 무제한 동시성, 분산 exactly-once, 실제 인증, DB 재시작 내구성을 검증했다고 말하지 않습니다.

AI 사용 공개 문구: “OpenAI Codex를 설계·구현·테스트·문서 작성에 활용했습니다. 참가자는 그래프 모델과 쿼리를 검토하고 실행 결과를 직접 확인합니다.” README에도 같은 사실을 명시합니다.

공개 저장소 생성·푸시는 사용자 승인을 받았습니다. 배포·해커톤 제출은 별도 승인 후 진행합니다.

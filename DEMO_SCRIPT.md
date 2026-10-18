# MemRelay · 최종 2분 촬영 대본

**상태: 참가자가 영상 녹화 완료를 확인했습니다. 아래는 참고용 촬영 대본이며, 영상 링크는 아직 전달되지 않았습니다. 실제 녹화 내용과 모드는 영상 검수 전까지 이 대본만으로 단정하지 않습니다.**

## 촬영 전 준비

- README의 검증된 로컬 경로로 실제 FalkorDB와 앱을 실행합니다. `LLM_MODE=mock`, UI의 `MOCK` 및 녹색 연결 표시를 확인합니다. API 키·`.env`·개인 탭은 화면에 띄우지 않습니다.
- 브라우저에서 `http://127.0.0.1:8000`을 엽니다. Alice를 선택하고 다른 작업을 실행하지 않습니다. 데모는 매번 별도 `memrelay_demo_<run>_alice/bob` 그래프를 사용하므로 기존 정상 사용자 데이터를 초기화할 필요가 없습니다.
- 선택적 Chromium 검사와 pytest는 촬영 중 동시에 실행하지 않습니다. 작은 기기에서는 대기 시간이 길어질 수 있습니다. 리허설로 실행 시간을 확인합니다. 계산 대기 구간을 편집한다면 실제 입력·상태·결과의 순서는 유지합니다.
- 한 버튼 데모는 5개 장면을 백엔드에서 실행한 후 결과 전체를 표시합니다. 장면이 순차 애니메이션으로 재생되는 기능은 없습니다. 아래 시간표는 결과 패널을 탐색하는 순서입니다.

## 화면 조작, 예상 출력, 내레이션

아래는 **Knowledge Graph를 포함한 새 2분 촬영·편집 순서**입니다. 기존 영상에 시각화만 추가하려면 문서 아래의 **40초 추가 촬영본**을 사용합니다. 시간은 편집 목표이며 실제 대기 시간은 기기와 연결에 따라 달라집니다.

| 시간 | 정확한 조작·보여줄 화면 | 실제 예상 출력 | 설명 대본 |
|---|---|---|---|
| 0:00–0:10 | 제목, `MOCK`, 녹색 연결 표시 → **Run full demo**. 완료 후 **Knowledge graph**로 이동 | `DEMO · ALICE`, 그래프 이름·읽은 시각·노드/엣지 수 | “MemRelay는 Track 02 프로젝트입니다. 기억과 두 에이전트의 협업을 실제 FalkorDB에 저장합니다. 지금은 외부 LLM 없이 재현하는 Mock 데모입니다.” |
| 0:10–0:25 | 전체 그래프의 범례 확인 → 보라색 procedural 노드 클릭 | semantic·procedural·episodic의 다른 색상·모양. 상세에 저장된 절차와 원본 메시지 | “사실, 절차, 사건이 연결된 기억입니다. 노드를 누르면 저장 내용과 출처를 확인합니다. 화면의 관계는 실제 FalkorDB에서 읽었습니다.” |
| 0:25–0:50 | **Focus revisions** → Rust 클릭 → Python 클릭 | 두 Memory와 두 Message, SUPPORTS 두 개와 SUPERSEDES 하나. Rust=active, Python=superseded | “언어가 Python에서 Rust로 바뀌었습니다. SUPERSEDES는 새 Rust 기억에서 이전 Python 기억으로 향합니다. 이전 사실을 지우지 않아 과거 내용과 각각의 원문도 추적할 수 있습니다.” |
| 0:50–1:15 | **Focus handoff** → **HANDED_OFF_TO** 선 클릭 → Task 클릭 | Coordinator·Executor·Task·TaskResult와 사용한 기억. 인계의 task ID·상태, Task의 상태·버전·원본 요청 | “Coordinator가 작업을 만들고 Executor에게 인계합니다. Executor는 그래프의 최신 사실과 절차를 읽고 결과를 기록합니다. 인계 관계와 Task의 실제 속성을 확인할 수 있습니다.” |
| 1:15–1:30 | **USES_MEMORY** 경로를 짚고 **Results & evidence → Task → Result → Memory ← Message** 펼치기 | Rust를 명시한 글머리표와 출처 ID, `Applied procedure … bullet_list_with_sources` | “최신 Rust 사실뿐 아니라 저장된 절차도 사용됐습니다. 그 절차가 결과를 글머리표와 출처를 포함한 형식으로 만듭니다. 이 연결은 검증 가능한 근거입니다.” |
| 1:30–1:42 | **Persistence** 장면 | `New Store/Coordinator objects; same DB client and running DB`, Rust 응답 | “새 Store와 Coordinator 객체에서도 기억을 읽습니다. 이 장면은 객체를 다시 만든 것이며 앱이나 DB 프로세스를 재시작한 것은 아닙니다.” |
| 1:42–1:54 | **Knowledge graph**로 돌아와 **Graph scope → Bob · latest demo** | `DEMO · BOB`, Bob의 Go 기억. Alice의 Rust 기억 없음 | “Bob은 별도 그래프의 Go를 사용합니다. Alice의 기억은 섞이지 않습니다. 이 선택기는 그래프 패널만 바꾸며 실제 인증은 아닙니다.” |
| 1:54–2:00 | 실제 테스트 로그 또는 마무리 자막 | `33 passed`, 저장소 주소, AI 사용 공개 | “실제 FalkorDB에서 33개 테스트를 통과했습니다. Codex를 구현과 검증에 활용했고 설계와 실행 결과를 직접 검토했습니다.” |

### 화면 이동과 촬영 유의점

- 최신 앱을 실행하고 브라우저를 강력 새로고침합니다. **Run full demo**는 완료 후 결과를 한 번에 표시합니다. 실행 대기를 장면별 애니메이션처럼 설명하지 않습니다.
- 자동 데모 중 상단 Alice/Bob 선택기는 그대로 둡니다. 상단 선택기는 기본 사용자 그래프로 돌아갑니다. 격리 장면에서는 그래프 내부 **Graph scope → Bob · latest demo**를 사용합니다. 다른 패널은 Alice 데모 내용이 남아 있으므로 그래프 패널을 중심으로 촬영합니다.
- 검증된 전체 데모 예시는 42개 노드/65개 엣지이고 revision focus는 4개 노드/3개 엣지입니다. 전체 개수와 보이는 개수는 다릅니다. 숫자를 맞추려고 다른 실행 화면을 섞지 않습니다.
- 드래그·확대/축소·**Fit**·**Auto arrange**는 추가 촬영본에서 시연하거나 그래프 장면에 짧게 넣습니다. 화면 좌표만 바뀝니다.
- Task와 인계 선의 version은 별도 저장 값이며 항상 같지는 않습니다. [시각화 제약](docs/KNOWLEDGE_GRAPH.md)을 참고합니다.
- 상태 전이를 자세히 보여주려면 **Agent tasks → Handoff details → State transitions** 후 **Transitions recorded in the graph**를 펼칩니다. 정상 완료 예시는 pending(v0) → running(v1) → completed(v2)입니다. 메인 2분 영상의 필수 조작은 아닙니다.

## 화면에서 확인할 핵심 그래프 경로

```text
Message(원문) -SUPPORTS-> Memory(Rust, active)
Memory(Rust) -SUPERSEDES-> Memory(Python, superseded)
Coordinator -CREATED-> Task -ASSIGNED_TO-> Executor
Coordinator -HANDED_OFF_TO {task_id,status,version}-> Executor
Task -TRANSITIONED-> TaskEvent(pending/running/completed)
Task -PRODUCED-> TaskResult -USES_MEMORY-> Memory <-SUPPORTS- Message
```

원한다면 FalkorDB 클라이언트에서 마지막 실행의 `graph_prefix + '_alice'` 그래프를 선택하고 아래 읽기 쿼리를 실행합니다. `graph_prefix`는 **Full demo evidence** 펼침 항목에 있습니다. 기본 `memrelay_alice`와 혼동하지 않습니다.

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

- 최신 33 passed는 개별 검증 실행별 수입니다(기존 25 + 시각화 8). Unix/TCP 실행을 합쳐 “서로 다른 테스트 66개”라고 말하지 않습니다. [원본 실행 로그](docs/verification/)를 사용합니다.
- 두 역할은 별도 클래스·실행 경로이며 Executor는 결정적 구현입니다. “두 LLM이 자율 토론한다”라고 설명하지 않습니다.
- 한 버튼 데모는 객체 재생성입니다. 실제 프로세스 재시작을 영상에 넣으려면 별도 일반 Alice 화면에서 pending 작업을 만든 뒤 **Uvicorn만** 종료·재실행하고 **Resume pending tasks**를 누릅니다. DB는 계속 실행 중이라고 설명합니다.
- 실제 API LLM 호출은 키가 없어 NOT TESTED입니다. mock 데모를 실제 Gemini/Groq 응답이라고 설명하지 않습니다.
- 무제한 동시성, 분산 exactly-once, 실제 인증, DB 재시작 내구성을 검증했다고 말하지 않습니다.

AI 사용 공개 문구: “OpenAI Codex를 설계·구현·테스트·문서 작성에 활용했습니다. 참가자는 그래프 모델과 쿼리를 검토하고 실행 결과를 직접 확인합니다.” README에도 같은 사실을 명시합니다.

공개 저장소 생성·푸시는 사용자 승인을 받았습니다. 배포·해커톤 제출은 별도 승인 후 진행합니다.


## 기존 영상에 넣는 40초 추가 촬영본

기존 영상의 기억 변경·인계 설명 구간을 아래 화면으로 교체하거나 연결합니다. 그대로 추가하면 2분을 넘길 수 있으므로 중복 설명과 대기 시간을 편집합니다. **Run full demo** 완료 후 **Knowledge graph**의 `DEMO · ALICE`에서 시작합니다.

| 시간 | 조작·구도 | 설명 대본 |
|---|---|---|
| 0:00–0:05 | 전체 그래프와 범례, `DEMO · ALICE` | “실제 FalkorDB의 노드와 관계를 읽기 전용으로 보여줍니다.” |
| 0:05–0:17 | **Focus revisions** → Rust 클릭. 화살표와 원문 상세 유지 | “Python에서 Rust로 변경됐습니다. 화살표는 새 Rust 기억에서 이전 Python 기억으로 향하며 두 기억의 출처도 보존됩니다.” |
| 0:17–0:29 | **Focus handoff** → HANDED_OFF_TO 선 클릭 → TaskResult·USES_MEMORY 경로 지목 | “실제 작업 ID와 완료 상태, 결과가 사용한 사실과 절차를 그래프에서 확인합니다.” |
| 0:29–0:34 | 노드 드래그 → **+** → **Fit** → **Auto arrange** | “확대와 배치는 화면만 바꾸며 원본 그래프는 수정하지 않습니다.” |
| 0:34–0:40 | **Graph scope → Bob · latest demo** → Go 기억 | “Bob은 별도 그래프의 Go를 사용하며 Alice의 기억과 분리됩니다.” |

영문 자막용 문구:

1. “A read-only view of real FalkorDB nodes and relationships.”
2. “Rust supersedes Python. Both memories retain their original message sources.”
3. “The graph records the agent handoff and the memories used by the result.”
4. “Dragging and zooming do not change stored graph data.”
5. “Bob’s separate graph uses Go, without Alice’s Rust memory.”

노드·엣지가 없으면 연결 표시와 **Reload graph**를 먼저 확인합니다. 장애 중 이전 캡처를 현재 데이터처럼 사용하지 않습니다. 최대 250개 노드/600개 엣지를 불러오므로 부분 표시 안내가 있다면 전체 DB를 모두 표시했다고 말하지 않습니다.

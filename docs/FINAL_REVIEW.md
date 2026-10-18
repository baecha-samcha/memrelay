# MemRelay 제출 전 최종 검토

이 보고서의 커밋·remote 수와 공개 상태는 **최종 점검 당시의 스냅샷**입니다. 이후 사용자가 GitHub 저장소 생성·푸시를 승인했습니다. 현재 공개·영상 상태는 README를 확인하세요. 공개 저장소 생성과 push는 완료되었으며, 참가자가 영상 녹화 완료를 확인했습니다. 영상 URL은 아직 전달되지 않았습니다.

**로컬 핵심 검증: PASS. 라이브 API·Cloud·Docker 및 외부 제출은 NOT TESTED/미진행입니다.** 공개 저장소는 생성되었고 영상 녹화도 완료되었습니다. 영상 URL 등록·재생 검수 및 해커톤 제출 완료는 아직 확인하지 않았습니다.

## 요청 항목별 판정

| 항목 | 판정 | 근거 / 범위 |
|---|---|---|
| 문서 ↔ 코드 일치 | PASS | README 설치 의존성 순서, 객체 재생성 설명, 실제 테스트 수 수정. 아래 알려진 한계 포함. |
| FalkorDB 기억의 실제 응답·작업 사용 | PASS | Python→Rust 응답 변화, SUPERSEDES 경로 조회, procedure 유무에 따른 글머리표 차이 및 TaskResult 근거 확인. |
| 실제 연결 해제와 복원 | PASS | TCP 연결 차단 시 7 API=503, 정적 UI=200, 브라우저 장애 표시. 복원 후 Rust 재조회·pending 작업 완료, 실패 중 Message 쓰기 0. |
| Mock / API 역할 분석 | PASS | [역할 비교·요청 예시](LLM_VERIFICATION.md). Executor는 양쪽 모두 결정적 구현. |
| 실제 LLM 시나리오 | NOT TESTED | 키 없음. 모델 접근·JSON 응답·생성 문장 품질을 성공으로 보고하지 않음. |
| 테스트 수·실패 이력 | PASS | Unix와 TCP **각 25 passed**. 수정 전 새 회귀 검사는 **1 failed**. 과거 자원 경합 실패는 별도 이력으로 유지. |
| 공개 후보 및 Git 이력 검사 | PASS (현재 범위) | [보안 검사 메타데이터](verification/public-files-audit.json). 공개 전 점검 당시 커밋·Git 객체·remote 0. 이후 커밋과 원격 push 완료; 당시 보안 로그는 역사적 기록으로 유지. |
| 새 설치 검증 | PASS (현재 Linux 범위) | 새 소스 사본·새 venv 설치, pip check, `.env.example`, 실제 DB 앱 데모 성공. Cloud/Docker/다른 OS는 NOT TESTED. |
| 2분 화면 조작·대본 | PASS | [DEMO_SCRIPT.md](../DEMO_SCRIPT.md): 조작, 출력, 시간표, 그래프 쿼리 및 하지 말아야 할 주장. 영상 녹화 완료(참가자 확인); 링크·내용 검수는 미완료. |
| AI 코딩 어시스턴트 공개 | PASS | README·대본에 OpenAI Codex 사용 명시. 참가자 직접 검토·이해 필요. |

현재 실행에서 남은 핵심 기능 FAIL은 없습니다. 새로 발견한 출처 무결성 FAIL 하나만 최소 수정했습니다. 저장소 공개와 push는 이후 승인받아 완료했습니다. 외부 배포·해커톤 제출은 수행하지 않았습니다.

## 실제 코드와 Cypher 흐름

1. **현재 답변:** `POST /api/chat` → `Coordinator.chat()` → `Store.memories(subject=...)` → `cypher/memories.cypher`의 `status='active'` 필터 → `LLM.answer(used)` → 응답 Message 저장 → `answer_evidence.cypher`의 `USES_MEMORY`. Mock은 조회된 `object`를 포맷하고, API는 같은 facts를 LiteLLM에 전달합니다.
2. **수정:** 입력 Message/episodic 저장 → `LLM.interpret()` → 원문 기반 `explicit_correction()`·`uncertain()` → `slot_read.cypher`에서 버전 조회 → `remember.cypher`에서 같은 버전일 때 새 Memory 생성·이전 상태/유효구간 종료·`SUPERSEDES`·source 연결. 단순 충돌은 disputed입니다.
3. **과거:** `Coordinator`의 history 분기 → `history.cypher`가 변경 관계와 수정 원문을 반환. 별도 `GET /memories?at=<epoch_ms>`는 과거 유효구간과 그 시각 이전의 출처를 조회합니다. 자연어로 임의 날짜를 정밀 해석하는 기능은 아닙니다.
4. **인계:** Coordinator → `task_create.cypher`의 Task·CREATED·ASSIGNED_TO·HANDED_OFF_TO·pending 이벤트 → Executor의 `claim.cypher` 조건부 점유 → `memories.cypher`에서 실제 기억 조회 → `Executor.execute()`의 fact/rule 필터와 글머리표 적용 → `finish.cypher`의 결과·근거·상태 이벤트 커밋.
5. **복구:** 새 Executor → graph Task 조회 → pending 또는 임대 만료 running 발견 → 새 token/version claim. 동일 Task의 완료 결과는 재실행하지 않습니다. 기존 DB 클라이언트를 공유하는 데모 객체 재생성과 독립 프로세스 테스트는 구분합니다.

이 흐름은 [실제 실행 로그](verification/graph-dependency.txt)에 기록된 별도 `audit_*` 그래프에서 확인했습니다. 실행한 SQL/파일 저장으로 답을 보충하는 경로는 없습니다. 시스템에 SQLite 또는 JSON 기억 대체 저장소를 추가하지 않았습니다.

## 변경 범위

- **핵심 수정:** `memory/store.py`의 같은-object 출처 추가 경로에 불확실성 조건을 적용. 기존 Python 사실에 대한 “Maybe Python”/“not Python” 발언은 지지 근거로 연결하지 않습니다. 새 regression test 1개 추가.
- **설명 수정:** 자동 데모 Persistence의 scope 문자열은 실제 생성하는 `Store/Coordinator`와 공유 DB client를 명시. Executor 재생성을 이 장면에서 했다고 주장하지 않습니다.
- **실행법 수정:** Cloud/Docker에는 runtime requirements, Docker-free 경로에만 dev/FalkorDBLite 의존성을 설치하도록 README 정리.
- **검증 자료:** 실제 TCP cut/restore 스크립트, 비밀값을 출력하지 않는 후보 파일 검사, 실행 로그, API 검증 절차·대본·이 보고서. 새로운 제품 기능이나 핵심 아키텍처 변경 없음.

[정확한 실행 수·실패 이력·Known Limitations](VALIDATION.md)을 함께 검토하세요. 현재 남은 항목은 영상 URL 등록과 재생 검수, 참가자의 최종 코드 리뷰 및 제출입니다. 저장소 생성·push는 완료했고, 배포·제출은 별도 승인이 필요합니다.

## 심사위원 기술 질문 5개와 답변

**1. FalkorDB가 단순 시각화용 저장소가 아니라는 것을 어떻게 입증하나요?**

현재 답변의 사실과 Executor의 절차는 실제 graph query 결과에서 옵니다. Python→Rust graph revision 후 답변이 바뀌고, procedural memory 유무에 따라 실제 글머리표 출력이 바뀝니다. TCP 연결을 끊었을 때 기억 기반 7개 API가 503으로 실패하고 복원 후 같은 기억을 다시 사용한 로그도 있습니다. Mock 모드도 같은 DB 경로를 사용합니다.

**2. Python을 Rust로 바꾸면 과거와 출처는 어떻게 보존하나요?**

이전 Memory를 삭제하지 않습니다. 버전 조건을 검사하는 한 쓰기 쿼리에서 새 Rust Memory, Python의 superseded 상태·종료 시각, 새→옛 SUPERSEDES와 원본 Message SUPPORTS 경로를 기록합니다. 기본 조회는 active만, 과거 조회는 유효구간을 사용합니다. 명시적 변경이 없는 충돌·불확실성은 disputed이며, 언어적 판정은 제한된 휴리스틱입니다.

**3. 에이전트가 두 개인 이유와 LLM의 실제 역할은 무엇인가요?**

Coordinator는 의도 해석과 graph Task/인계를 담당하고 Executor는 자기 할당을 graph에서 찾아 사실·절차로 실행하고 결과를 커밋합니다. 별도 클래스·실행 경로이며 worker를 별도 프로세스로 실행할 수도 있습니다. Mock은 제한된 의도 파서와 포맷터, API는 LiteLLM 의도 추출·현재 답변 문장 생성을 사용합니다. Executor 자체는 양쪽 모두 결정적 코드입니다. 실제 API 호출은 아직 미검증입니다.

**4. 중복 실행이나 장애 복구를 정확히 어디까지 보장하나요?**

Task ID, 상태, version으로 claim하고 매 실행 token과 임대를 부여합니다. finish는 현재 token/version과 만료 전 상태를 검사하므로 이전 Executor의 결과 커밋이 거부됩니다. 테스트한 단일 DB에서는 같은 Task의 terminal result가 하나입니다. 계산 자체가 한 번만 수행된다는 뜻이 아니며 분산 exactly-once나 외부 결제·이메일의 중복 방지를 보장하지 않습니다. 장시간 실행을 위한 heartbeat도 없습니다.

**5. Alice/Bob 격리와 재시작 내구성은 실제 인증·DB 재시작 보장과 같은가요?**

아닙니다. Alice/Bob은 별도 graph로 격리하지만 선택기는 인증이 없으므로 localhost 데모 범위입니다. UI Persistence는 Store/Coordinator 객체 재생성이고 DB client/서버는 유지합니다. 별도 테스트는 독립 앱 프로세스 두 개가 같은 DB의 기억과 pending Task를 복구합니다. DB 프로세스 재시작·failover 내구성까지 검증한 것은 아닙니다.

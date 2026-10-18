# Final submission validation record

Date: 2026-10-18 KST. Git history counts and publication status below are the pre-publication audit snapshot; current publication status is tracked in README. Commands run from the repository root. The current audit is separate from the previous MVP verification; historical runs are not added together as distinct tests.

## Current results from captured execution

| Status | Check | Actual result / evidence |
|---|---|---|
| PASS | Full pytest, disposable real FalkorDBLite / Unix socket | **25 passed, 1 warning, 14.47s** · [output](verification/pytest-unix.txt) |
| PASS | Full pytest, independent real local FalkorDB / TCP | **25 passed, 1 warning, 8.26s** · [output](verification/pytest-tcp.txt) |
| PASS | Graph facts change answers | Python answer → explicit graph revision → Rust answer; queried SUPERSEDES IDs and source Message · [audit](verification/graph-dependency.txt) |
| PASS | Executor uses graph facts and procedure | Rust + actual bullet output with procedure; Bob without the procedure outputs Go without bullets; TaskResult evidence contains semantic/procedural source paths · [audit](verification/graph-dependency.txt) |
| PASS | Actual database connection cut and restore | Seven graph-dependent APIs return 503; static page remains 200; real browser shows disconnected, then connected after restoration · [audit](verification/graph-dependency.txt) |
| PASS | Fresh installation smoke check | New copied source + new venv, requirements-dev install exit 0 (86.86s), pip check exit 0, actual FalkorDBLite app demo returns 200 with Rust/Go/SUPERSEDES/completed task · [summary](verification/clean-install.txt) |
| PASS | Syntax / installed dependencies | Python compilation, JavaScript syntax, existing venv pip check · [output](verification/static-checks.txt) |
| PASS | Public candidate security review | Heuristic key/PII/private-file scan, ignored dumps/env, empty Git object/history store · [metadata-only output](verification/public-files-audit.json) |
| NOT TESTED | Live Gemini/Groq | No configured key found; no live provider request made. [Request examples and acceptance checks](LLM_VERIFICATION.md) |
| NOT TESTED | Cloud / Docker runtime | No Cloud endpoint/credentials; Docker not available. TCP local and FalkorDBLite are tested. |
| NOT TESTED | Public GitHub / deployment / submission / recorded video | No external action performed. Video script prepared, no video file recorded. |

`PASS` describes only the named scope. Two 25-test runs are the same suite under two transports, not 50 distinct tests. A failed-task test intentionally expects a durable failed result; that is a passing assertion, not an unreported test failure.

## Environment and installation scope

Python 3.13.5, Linux x86_64 / Crostini, approximately 2.7 GiB available system RAM configuration with swap. Runtime pins: FastAPI 0.143.5, Uvicorn 0.54.0, FalkorDB Python SDK 1.8.0, LiteLLM 1.106.0. Test pins: pytest 9.1.1, HTTPX 0.28.1, FalkorDBLite 0.10.0. The actual module reports `41803` (4.18.3). Docker image tag `falkordb/falkordb:v4.18.3` was previously checked for availability; the container has not been executed.

Fresh installation used a new venv and a copy of nonignored source, not the original venv or installed imports. It installed requirements-dev from scratch, copied `.env.example` to `.env`, created a private real FalkorDBLite instance and exercised FastAPI's app through TestClient, including the full mock demo. This is **not** a clean OS installation or a Docker/Cloud test. API/factory paths were tested; original Uvicorn runtime was also reached by the real-browser connection audit.

The test suite emits one unsuppressed Starlette deprecation warning about its current HTTPX TestClient path in favor of `httpx2`. Assertions pass. Existing and clean-venv `pip check` pass; no dependency change was made merely to hide this warning.

## Actual disconnection method and restoration

Run separately from pytest, with the normal real local DB listening on `127.0.0.1:6379`:

```bash
python scripts/verify_graph_dependency.py --browser
```

The audit starts a private app instance with `audit_<uuid>_alice/bob` graphs and a TCP forwarding gate. It then **closes established TCP connections and blocks forwarding**, exercising actual Redis/FalkorDB connection errors. It does not mock HTTP responses or substitute a database. The existing DB process and normal `memrelay_*` user graphs remain running.

Disconnected endpoints: health, snapshot, memories, chat, pending-task execution, resume and automatic demo. All returned 503 / `database=disconnected`; `/` returned 200. Chromium observed the real offline status. After restoring the same app's connection, health returned 200, the saved Rust fact was still used, offline requests had created zero new Message nodes, and the still-pending task completed. Chromium returned to the connected status. The private audit server/gate was then closed; the normal DB/server was never disconnected by this experiment.

Audit graph prefix and synthetic memory/source IDs remain in the captured output for inspection. This test is a connection-failure test, **not** a FalkorDB-process restart or failover test. The old browser smoke test's injected-503 case remains a separate UI-only check and must not be described as a real network cut.

## Failure history and the narrowly scoped fix

| When / evidence | FAIL observed | Resolution / current state |
|---|---|---|
| Current final review, [captured regression](verification/regression-before-fix.txt) | **1 failed**: existing Python fact plus “Maybe Project Atlas uses Python” was returned as active and attached as SUPPORTS | The same-object corroboration branch now requires `not uncertain`. The regression also verifies a same-object denial. Uncertain/negative statements become disputed; prior active fact/source stays intact. Both full suites now pass 25 tests. |
| Previous MVP work, conversation/old notes only; no archived raw log | Initial pytest collection error: SDK connected eagerly while DB was unavailable | Lazy SDK connection was implemented then; current offline and full-suite checks pass. |
| Previous MVP work, conversation/old notes only; no archived raw log | A simultaneous Chromium/pytest run had **23 passed, 1 failed** (30s process-start timeout); browser navigation also timed out | Sequential runs later passed. Do not run heavyweight checks together on this device. Resource contention is a plausible cause, not a proven benchmark result. |
| Previous MVP work, conversation/old notes only; no archived raw log | Browser's default 5s initial-load assertion timed out; a snapshot returned 503 under load | Browser waits were increased to 30s, navigation to 60s; later browser run passed. This does not guarantee request latency. |

The earlier 20/23/24-test success reports are historical suite sizes, not current results. This review captures fresh raw pytest output rather than treating prose notes as execution logs.

## Known Limitations

- Bounded mock grammar and heuristic correction/uncertainty checks; no universal natural-language contradiction detector. API object-literal checks do not prove truth or correct subject extraction.
- Executor is deterministic in both modes, supports one allowlisted procedure, and has no external actions. Episodic events are stored/traced; semantic/procedural memory drives the current project answer/task.
- API mode's generic episodic acknowledgement currently mentions “Mock mode” even when the adapter is API. This minor wording issue is recorded rather than expanding the code changes before submission.
- Same-instance conditional writes are tested. No distributed exactly-once, failover, cross-graph transaction, DB-process restart or clock-skew guarantee.
- 30-second task leases have no heartbeat. Failed tasks are terminal; input ingestion and context retrieval span multiple queries and may leave partial records or use a retrieval snapshot later superseded.
- Millisecond timestamps cannot distinguish all intermediate revisions within one millisecond; use SUPERSEDES paths for ordering. Historical source filtering excludes later source additions, while other displayed metadata may reflect subsequent updates.
- The Alice/Bob selector is not authentication. No pagination, large-data benchmark, full ontology/entity resolution or interactive node graph. Automatic demo graphs accumulate until explicitly removed.
- Redis SDK errors are mapped to the same sanitized 503 class; a query/server error can therefore share the connection-failure presentation. Review server-side context when diagnosing it.
- Actual LLM, Cloud, Docker, video recording and external submission remain unverified/not delivered as stated above.

Captured logs contain synthetic data only. Workspace paths are replaced with `<WORKSPACE>` and trailing whitespace is trimmed for publication. Full pip installation chatter and screenshots stay in ignored `artifacts/`. The committed-candidate logs are deliberate review evidence, not database dumps. The scanner is heuristic, not proof that every possible secret format is detectable.


## English UI follow-up

The default browser interface now uses English (`lang="en"`), including demo controls, memory/source panels, task states and connection errors. README and filming instructions use the actual English control names. Core memory/agent/query logic is unchanged.

Browser verification passed: user switching, five-scene demo, Rust result and history, task transition evidence, an exact connected/disconnected indicator, no Korean text in the synthetic demo UI, and mobile width. [Captured output](verification/english-ui-browser.txt). The initial English smoke run passed; a subsequent run exceeded the 30-second demo wait on this small machine. The final run passed with a 90-second demo wait. This is a test wait allowance, not a response-time guarantee. Desktop output was visually inspected.

JavaScript syntax, Python verification-script compilation and the public-candidate secret scan also passed. The 25-test pytest results above remain the earlier backend verification; pytest was not rerun for this copy-only UI change.

# MemRelay

**A shared memory graph that remembers what changed, why, and which agent acted on it.**

Graph Hacks 2026 · **Track 02: Agent Memory and Coordination** · Python / FalkorDB / Cypher / FastAPI / LiteLLM

MemRelay stores episodic events, semantic facts, executable procedures, revision history, source messages, tasks and handoffs in **real FalkorDB**. Removing FalkorDB stops memory operations with HTTP 503; there is no SQLite, JSON-file or in-process memory fallback. The UI remains accessible and displays a connection failure.

All example data is synthetic (Alice, Bob, Project Atlas). The Alice/Bob selector is **a demo selector, not authentication**. Bind the app to localhost; user graph separation is not a production authorization system.

## Quick start

Clone the public repository and run commands from its root:

```bash
git clone https://github.com/baecha-samcha/memrelay.git
cd memrelay
```

 Python 3.12+ recommended (verified on Python 3.13.5, Linux x86_64). No local LLM or frontend build tools required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Choose **one** database option:

**A. FalkorDB Cloud (preferred on 4 GB machines).** Edit only your local `.env`:

```dotenv
FALKORDB_URL=rediss://username:password@your-cloud-host:port
LLM_MODE=mock
```

Use the exact connection scheme/port supplied by Cloud. URL-encode special characters in credentials. `.env` is ignored by Git; never put real credentials in `.env.example`.

**B. Docker:**

```bash
docker compose up -d
```

The Compose service exposes only `127.0.0.1:6379`, persists `/data` in a named volume and enables AOF. Docker itself was unavailable in the development environment, so this path has not been executed here.

**C. Without Docker or Cloud:** in a separate terminal at the same repository root:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/local_db.py
```

This uses official **FalkorDBLite**, which starts a real Redis server with the FalkorDB graph module. It listens on loopback port 6379, saves under ignored `.data/`, and enables AOF. Its RDB/AOF files are FalkorDB database files, not an application memory fallback. Keep this process running. Binary wheel availability depends on platform; if unavailable, use Cloud. Do not start it while another database occupies port 6379.

Start the app:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**; API docs: **http://127.0.0.1:8000/docs**.

## One-button demo

Click **Run full demo**. Every run creates an isolated `memrelay_demo_<run>_alice/bob` pair of real graphs, leaving normal demo-user data intact. These graphs persist until explicitly deleted in FalkorDB; repeated runs consume additional database space. Use a disposable DB for repeated rehearsals.

1. **Memory Creation:** Alice says `Project Atlas uses Python` and `For project summaries use bullet points and cite sources`. The original events, semantic language fact and procedural rule appear with `Message → SUPPORTS → Memory` evidence.
2. **Memory Evolution:** `We switched Project Atlas to Rust` supersedes Python. Current queries return Rust; history shows both messages and `new → SUPERSEDES → old`.
3. **Agent Handoff:** Coordinator persists a pending Task. Executor claims it in FalkorDB, reads active facts and procedures, produces a bullet list with source IDs, and commits a completed TaskResult.
4. **Persistence:** service/agent objects are reconstructed and read the same memories. **This button does not restart the app process or DB process.** A separate automated test starts two independent app processes to verify actual process persistence.
5. **User Isolation:** Bob initially has no project facts, then records Go and answers Go. Alice continues to use Rust.

The button always uses **Mock LLM**, even when the interactive chat is configured for API mode. CLI equivalent:

```bash
python -m demo.scenario
```

The conversational examples in the UI can also be run individually. After creating a task, click **Run Executor** or **Resume pending tasks**. For a separate worker process:

```bash
python -m agents.worker --once
# Or poll every 2 seconds:
python -m agents.worker
```

To demonstrate a real app-process restart: create a pending task; stop only Uvicorn; start the same command again; click **Resume pending tasks**. Keep FalkorDB running. Expired running tasks become eligible after their 30-second lease. Completed tasks are not executed again.

## LLM modes and supported behavior

Default `LLM_MODE=mock` is deterministic and makes no external LLM calls. It understands the documented English Atlas statements, language changes, history/current questions, project-summary tasks and the bullet-list-with-sources procedure. Other messages are still recorded as episodic events. Mock mode is not a general natural-language understanding system. Common question words and uncertainty/negation markers are handled conservatively; this is a bounded demo grammar, not a complete linguistic validator.

For LiteLLM API mode set `.env`, then restart the app:

```dotenv
LLM_MODE=api
LLM_MODEL=gemini/gemini-2.5-flash
GEMINI_API_KEY=your-local-key
# Or: LLM_MODEL=groq/llama-3.3-70b-versatile and GROQ_API_KEY=...
```

The adapter requests validated structured intents and uses graph-supplied facts for response generation. It never accepts generated Cypher. Semantic objects must occur literally in the source; overwrite permission also requires a non-hedged explicit correction marker in the actual message. The provider cannot set task state or memory validity. **API mode has not been tested against a live provider because no credentials were supplied.** Model availability/access is provider-dependent. API failures do not silently switch to mock; source/episodic records already written may remain. Generated prose can still be inaccurate; the attached graph evidence is the verifiable record. See [the exact mock/API role comparison and live verification procedure](docs/LLM_VERIFICATION.md).

Procedures are intentionally an allowlist: `project_summary` + `bullet_list_with_sources`. Executor applies this rule in code to the actual output. Arbitrary stored text is not executed as code or shell commands. Executor's graph-based formatting is deterministic in both modes.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

By default all persistence/integration tests start a real, disposable FalkorDBLite instance, not a fake store. To use a running local/Cloud FalkorDB:

```bash
TEST_FALKORDB_URL=redis://127.0.0.1:6379 python -m pytest -q
```

Use a dedicated test DB/credentials with graph-create/delete permission. Fixtures only remove randomly named `test_<uuid>_alice/bob` graphs. Tests cover the three memory kinds, explicit revisions, active/historical retrieval, source paths, graph isolation, handoff/procedure execution, duplicate prevention, lease recovery, actual app-process restart, connection failure, simultaneous memory updates and simultaneous task execution. Final submission verification passed **25 tests**, both on the disposable Unix-socket instance and a separate TCP server. See [validation details](docs/VALIDATION.md). Run pytest and optional Chromium checks sequentially on small machines.

Optional UI smoke test (not needed to run MemRelay):

```bash
pip install -r requirements-browser.txt
python -m playwright install chromium
# Start the database and app first.
python scripts/browser_smoke.py
```

## Graph model and API

See [ARCHITECTURE.md](ARCHITECTURE.md) for model choices, concurrency limits and architecture decisions. Executed parameterized queries live directly in [cypher/](cypher/); they are not separate, drifting examples.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Actual graph query and connection status |
| `POST /api/chat` | `{user, text, session_id?, task_id?}`; answer + memory/source evidence |
| `GET /api/{user}/memories` | Active memories; `history=true`, `subject=Project Atlas`, `at=<epoch_ms>` |
| `GET /api/{user}/snapshot` | Memories, revisions, tasks, results, evidence |
| `POST /api/{user}/tasks/{id}/execute` | Conditional Executor claim + result commit |
| `GET /api/{user}/tasks/{id}/events` | Durable pending/running/completed/failed transitions |
| `POST /api/{user}/resume` | Discover pending and expired running tasks from the graph |
| `POST /api/demo` | Five synthetic scenes in isolated graphs |

Use a stable caller-supplied `task_id` for retryable task submission. Reusing it with another prompt returns 409. IDs are scoped to the user's graph. Chat ingestion itself is not idempotent: resending a message records another event. No external side effects are executed by this MVP.

## Submission and disclosure

[Official rules](https://www.wemakedevs.org/hackathons/falkordb/rules) require central FalkorDB use, allowed data, source repository, setup instructions, Cypher, a working demo video, named track and AI-assistant disclosure. The listed October 18, 23:59 IST deadline corresponds to **October 19, 03:29 KST**. Recheck the official page before submission.

**AI disclosure:** OpenAI Codex assisted with architecture, implementation, tests and documentation. The participant must review, verify and understand the code, explain the graph model and make meaningful contributions before submitting, as required by the rules.

[Final PASS / FAIL / NOT TESTED review and five technical Q&As](docs/FINAL_REVIEW.md) describe the submission audit. The pre-fix source-integrity regression and all current test results are linked from the validation record.

[DEMO_SCRIPT.md](DEMO_SCRIPT.md) provides a two-minute recording script. Public source repository: [baecha-samcha/memrelay](https://github.com/baecha-samcha/memrelay). Repository creation and push were authorized by the user. Deployment, registration and hackathon submission have not been performed and require separate approval. No video has been recorded yet.

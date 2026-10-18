# A short code tour for review

Read these in order, then run the matching scenarios in the UI.

1. **`memory/store.py` + `cypher/memories.cypher`**: Store chooses a graph only from the Alice/Bob allowlist. Current retrieval filters active memories; `at` retrieves a historical validity interval. Ask why graph separation is not authentication.
2. **`cypher/message.cypher` + `remember.cypher`**: follow Session → Message → Memory → Entity. Observe the slot-version condition and that the status change, new memory, source edge and SUPERSEDES edge belong to one write query.
3. **`agents/llm.py` + `agents/coordinator.py`**: mock parsing or LiteLLM creates an intent; source-text checks gate revisions. Coordinator persists a task and handoff; it does not execute the task. A response Message records USES_MEMORY evidence.
4. **`cypher/task_create.cypher`, `claim.cypher`, `finish.cypher`**: inspect pending → running → completed/failed. Explain why a token plus version prevents an old Executor from committing after a new claim, and why that does not guarantee an external action ran only once.
5. **`agents/executor.py`**: the graph determines facts and task state. A procedural Memory changes the actual result format. Compare output with/without the bullet-list rule on a fresh graph.
6. **`demo/scenario.py` + `tests/test_process_restart.py`**: contrast rebuilding objects in the UI demo with starting independent app processes in the automated test. Both retain one running DB process.
7. **`app/main.py` + `app/static/app.js`**: inspect 503 behavior and public source/result evidence. UI state is a rendering of graph query results, not a replacement for persistent memory.

Try these review experiments on normal demo users:

- `Project Atlas uses Python` → `Project Atlas uses Go`: Go is disputed; Python stays active.
- `We switched Project Atlas to Rust`: Rust becomes active; Python remains in history.
- `Maybe we switched Project Atlas to Go`: uncertainty does not supersede Rust.
- Submit `Create a project summary` with a stable task ID via `/docs`. Execute it twice. Only one terminal result is stored.
- Stop Uvicorn with a pending task, restart it and resume. Stop FalkorDB instead and verify memory operations fail.

The assumptions and known limitations are in `ARCHITECTURE.md`; actual commands/results are in `docs/VALIDATION.md`. Participants should independently review the implementation and explain these paths before submission.

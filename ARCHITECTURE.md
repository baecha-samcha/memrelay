# MemRelay architecture

## System boundary

A lightweight browser calls FastAPI. Coordinator interprets requests through a bounded mock parser or LiteLLM. Coordinator and Executor have separate classes, code paths and optionally processes. Both use `memory.Store`, which executes the exact parameterized Cypher files in `cypher/` against **one shared FalkorDB server**. Each synthetic user has a separate graph: `memrelay_alice` or `memrelay_bob`.

There is no application memory database, queue, transcript cache or alternate durable store. Request-local Python lists are only query results. The long-lived Store retains a database client/connection, not user memories. Static demo text and test fixtures are synthetic inputs, not saved user state. If FalkorDB fails, graph operations fail closed. The FastAPI module constructs the connection lazily so the static UI can still start when the database is down.

## Graph model

| Node | Key properties | Meaning |
|---|---|---|
| User | id | alice/bob, within its own graph |
| Session | id | Session containing source and response messages |
| Message | id, content, role, created_at | Immutable original input or response |
| Memory | id, kind, content, status, created_at, updated_at, valid_from, valid_to | Shared memory node schema |
| Memory (semantic) | subject, predicate, object | Structured assertion, e.g. Project Atlas/language/Rust |
| Memory (procedural) | task_type, instruction | Allowlisted procedure for an actual task |
| Entity | id, name, version | Subject/predicate memory slot and its compare-and-set version |
| Agent | id, role | coordinator or executor |
| Task | id, subject, prompt, task_type, status, version, token, lease_until, attempts, timestamps | Durable assignment and ownership |
| TaskResult | id, task_id, content, status, created_at | Committed outcome |
| TaskEvent | status, version, at, agent | Immutable state-transition audit |

Relationships:

```text
User ─HAS_SESSION→ Session ─HAS_MESSAGE→ Message
Message ─SUPPORTS→ Memory ─ABOUT→ Entity
Memory(new) ─SUPERSEDES→ Memory(old)
Message(response) ─USES_MEMORY→ Memory ←SUPPORTS─ Message(source)
Message(request) ─REQUESTED→ Task
Agent(coordinator) ─CREATED→ Task ─ASSIGNED_TO→ Agent(executor)
Agent(coordinator) ─HANDED_OFF_TO {task_id,status,version,timestamps}→ Agent(executor)
Task ─TRANSITIONED→ TaskEvent
Task ─CONSIDERED_MEMORY→ Memory
Agent(coordinator) ─USES_MEMORY→ Memory
Task ─PRODUCED→ TaskResult ←PRODUCED─ Agent(executor)
Task ─USES_MEMORY→ Memory
TaskResult ─USES_MEMORY→ Memory ←SUPPORTS─ Message(source)
```

An Entity represents a versioned assertion slot named after its subject; it is keyed by `kind:subject:predicate`. This keeps the compare-and-set boundary aligned with the fact being revised. Different predicates for the same named subject are separate Entity slots, queried together by `Memory.subject`. This MVP does not perform entity resolution or general ontology inference. Episodic events get unique slots and preserve original Session/Message paths.

All memory kinds use the **same `Memory` label and `kind` property**. This avoids three versions of source, temporal and retrieval logic. Separate labels could enable different indices later, but do not justify divergent semantics in this MVP.

## Memory updates and provenance

1. Persist user Message and its episodic Memory.
2. Interpret an intent. Semantic facts/procedures are structured values, never executable queries.
3. Merge a versioned Entity slot and read its active memory and version.
4. Submit one write query that checks the version and source Message, increments the slot version and creates the new Memory and SUPPORTS/ABOUT links.
5. If the original message has an explicit unhedged correction marker, the same query supersedes the prior active Memory, closes its validity interval, and adds `new → SUPERSEDES → old`.
6. Without explicit correction, a different fact is stored as `disputed` and excluded from normal retrieval. Common uncertainty and negation expressions also cause disputed storage, even without a prior fact. Repeated unhedged same-object affirmations add a source to the existing Memory. Uncertain or denying statements remain disputed even when their object equals the active fact.
7. A version conflict causes bounded reread/retry. No client-held lock is used as the memory authority.

`status ∈ active, superseded, disputed`. Current retrieval explicitly filters `active`. Historical retrieval uses `[valid_from, valid_to)` epoch-millisecond intervals, where zero `valid_to` means open. Disputed facts never become historical truth. Source messages added after the requested historical timestamp are excluded from that historical response. Equal-millisecond revisions are ordered through SUPERSEDES links; timestamp-only queries cannot distinguish intermediate states within a single millisecond. Historical paths retain the source message of the old Memory.

Memory validity is **recorded knowledge time**, not a claim about when a real-world event actually occurred. Parsing a phrase such as “last Tuesday” does not backdate graph validity. The mock grammar is intentionally bounded; linguistic uncertainty detection is conservative heuristic code, not a universal truth detector. API extraction also requires literal objects and allowed predicates; an LLM cannot directly authorize overwrite or choose memory status.

Responses persist as Messages with USES_MEMORY edges; response JSON also carries the used memories and source messages. The UI shows these public, verifiable paths and task transitions, without exposing internal reasoning.

## Durable handoff and restart

Coordinator writes a Task, CREATED/ASSIGNED_TO/REQUESTED relationships, a HANDED_OFF_TO edge, a pending TaskEvent and considered context. Executor discovers its tasks through graph queries, not a Python queue.

State transitions:

```text
pending(v0) → running(v1,token,lease) → completed(v2) or failed(v2)
                 ↓ lease expires
             running(v2,new token) → completed(v3) or failed(v3)
```

A claim is a single conditional write: matching version and pending state, or matching version plus expired running state. It assigns a fresh token, increments version and attempts, records a running event and updates the handoff. Another executor with the stale version receives no row.

Executor retrieves active semantic and matching procedural memories. For project summaries it formats facts and, when the stored procedure requires it, emits actual bullet points and source citations. Procedures are allowlisted operations; free text is not evaluated as code. Unsupported/missing required facts result in a durable failed TaskResult.

A finish is one query checking running state, token, version and unexpired lease. It writes TaskResult, PRODUCED/USES_MEMORY evidence, completion/failure TaskEvent and updated handoff status together. An obsolete executor cannot commit a result. A completed/failed task cannot be claimed again. A stable caller-provided task ID is scoped to the user graph and cannot be reused with a different prompt.

A new Executor/worker can discover pending or expired tasks at any time through `/resume` or `python -m agents.worker`. FastAPI does not start a hidden background worker. Running tasks have a 30-second lease and no heartbeat; if work takes too long its result is rejected and a later worker can retry. Failed tasks are terminal; submit a new task ID for a deliberate retry.

## Concurrency guarantees and limits

Verified tests exercise a **single real FalkorDB instance** with multiple concurrent client threads, multiple task IDs, simultaneous corrections, duplicate Executor invocations and lease fencing. Atomic boundaries are individual `GRAPH.QUERY` writes. The database serializes/conflict-checks those writes; the application checks slot/task versions in the write query itself. No read-modify-write sequence is described as a multi-query transaction.

There is no distributed consensus, cross-graph transaction or end-to-end exactly-once execution guarantee. Rendering/model work can repeat after a crash or lease timeout; the tested guarantee is one committed terminal result per task under the single-instance model. This MVP performs no external actions. Adding email, payments or other side effects would require idempotency at the destination as well.

Message ingestion and memory extraction use multiple queries: a failure can leave a Message/episodic event without its semantic extraction. Context reads and task completion are also separate queries: result evidence records the execution's retrieval snapshot, and a concurrent later correction may supersede one of those memories. Past results retain the memory IDs actually used. There is no claim that all snapshot panels are transactionally consistent during concurrent writes.

Task ID and Entity slot uniqueness rely on atomic MERGE on the one graph writer instance. These tests do not prove safety across failover, multi-primary routing or network partitions. Result acknowledgement lost after a successful DB commit is ambiguous to the caller; inspect the task/result rather than creating a new ID automatically. Client wall clocks determine lease expiry and validity timestamps; use synchronized clocks for separate hosts.

No indices or strict DB uniqueness constraints are required for the small demo. Snapshot queries scan all user data, and the UI has no pagination. This is suitable for synthetic hackathon workloads; large deployments need migration/version tooling, indices, paging, retention, authentication and authorization.

## Decisions recorded

| Decision | Reason / tradeoff |
|---|---|
| Separate graph per synthetic user | Simple explicit isolation; graph identity cannot be supplied arbitrarily through the API. Not an auth boundary. |
| `Memory.kind` unified schema | One temporal/provenance path across all three types. |
| Parameterized Cypher files used at runtime | Queries remain reviewable and cannot drift from documentation copies. |
| No broad agent framework | Separate role classes and durable graph tasks fit a 4 GB Chromebook. |
| Cloud first; official FalkorDBLite development fallback | Docker is absent in Crostini here. Lite runs actual FalkorDB; architecture still depends on the graph. |
| Deterministic Executor, optional LiteLLM interpretation/answers | Verifies procedure application and graph evidence without provider availability. |
| Allowlisted procedure opcode | Stored rules change the output without arbitrary code execution. |
| Interactive graph added after P0 verification | A separate bounded read-only projection preserves core storage and agent paths; existing trace panels remain. |
| New graphs for every automatic demo | Repeatable Python→Rust transitions without destructive resets; graphs require eventual cleanup. |

No replacement of the requested core architecture was necessary. The Docker-free database runner is an additional local development option. Runtime packages and tested versions are pinned in requirements files; browser tooling is optional.

## Primary references

- [Graph Hacks official rules](https://www.wemakedevs.org/hackathons/falkordb/rules)
- [FalkorDB Python client API](https://falkordb-py.readthedocs.io/en/stable/falkordb.html)
- [FalkorDB GRAPH.QUERY](https://docs.falkordb.com/commands/graph.query)
- [Official FalkorDBLite project](https://github.com/FalkorDB/falkordblite)
- [LiteLLM Gemini provider](https://docs.litellm.ai/docs/providers/gemini)


## Read-only visualization addition

`memory/visualization.py` uses `GRAPH.LIST` to determine whether the requested current/demo graph actually exists, then two parameterized `GRAPH.RO_QUERY` calls from `cypher/view_nodes.cypher` and `cypher/view_edges.cypher`. It never calls user initialization, MERGE, graph write queries, or the wrapper helper that swallows list errors. A missing current graph returns an empty projection without creating storage; a missing demo graph returns 404. Connection failure returns sanitized 503.

The projection uses FalkorDB's graph-local internal node/edge IDs (`n<id>`, `e<id>`) to avoid collisions between logical IDs on different node types. Edge endpoints, types and properties come directly from stored relationships; none are synthesized from application snapshots. Nodes are prioritized for agents, facts/procedures, tasks/results, episodes/messages and supporting structure. At most 250 nodes and 600 edges between those selected nodes are returned. One extra row detects truncation; this is a bounded projection, not a complete paginated export. Source details cover only the loaded subgraph.

`GET /api/{user}/graph?demo_id=...` accepts the existing user allowlist and an optional 10-character hexadecimal demo ID. Demo graph names are derived under the server's configured prefix; they remain inspectable across app restarts without an in-process registry. This extends demo inspection, not authentication.

The browser keeps one Cytoscape instance and replaces its elements on context changes. Request serials and AbortController reject late responses. Main user changes return to current graphs; a graph-only scope selector permits explicit demo Alice/Bob inspection. The automatic demo selects demo Alice and aligns the top user selector with the Alice panels. Existing snapshots and demo response schemas are unchanged.

Renderer layout/drag/zoom changes only browser coordinates. No visualization interaction writes positions, nodes or edges to FalkorDB. Structural nodes can be hidden, and focus views filter actual loaded edges. Node detail text uses textContent, not HTML. Stored `SUPERSEDES` points from new to old; the displayed timeline caption separately explains the old-to-new change.

A detected network/503 failure clears elements and selected details, marks the panel stale and cancels in-flight reads. Health recovery alone does not restore old elements. Two RO queries are not a transactionally consistent snapshot during concurrent writes. Sampling limits, read timestamps and partial-view notices are part of the UI; no distributed consistency or FPS claim is added.

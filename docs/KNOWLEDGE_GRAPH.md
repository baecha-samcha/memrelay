# Read-only interactive knowledge graph

The existing graph memory model, Coordinator/Executor paths, mock parser, five-scene demo and existing API response schemas are preserved. This addition is a bounded visualization projection, not a second memory store.

## Use it in the video

1. Restart Uvicorn after updating the code, then hard-refresh the browser.
2. Click **Run full demo**. The graph automatically selects **Alice · latest demo** and displays `DEMO · ALICE`, the exact graph name, read time and loaded/visible counts.
3. Click **Focus revisions**. The demo shows four nodes and three actual edges: the two language memories, their two original messages, two SUPPORTS edges and `Rust -SUPERSEDES-> Python`. The caption explains the timeline `Python → Rust` without reversing the stored arrow.
4. Click Rust to inspect content, active status, creation/validity timestamps, structured fact and its source message. Task details also show the prompt and original REQUESTED message. Python retains superseded status and its original source.
5. Click **Focus handoff**. Inspect Coordinator → Executor, their Task/TaskResult, used facts/procedure and original messages. Click HANDED_OFF_TO to inspect its stored task ID, status and timestamps.
6. Drag a node, zoom with the wheel or +/−, **Fit** and **Auto arrange**. These operations change only local coordinates.
7. Select **Bob · latest demo** in **Graph scope**: Bob has Go and no Alice Rust fact. The top Alice/Bob selector continues the original behavior of returning to a current-user graph; the graph-only scope selector can independently inspect a demo.

Semantic memories are amber ellipses, procedural memories purple rounded hexagons, episodes green diamonds, messages blue-gray rounded rectangles, agents dark-green hexagons, tasks orange rectangles and results blue octagons. Structural User/Session/Entity/TaskEvent nodes are optional.

## Query contract and safety

`GET /api/{user}/graph` accepts Alice/Bob and optional `demo_id=<10 lowercase hex characters>`. The server derives demo names under its configured prefix; arbitrary graph names are not accepted. The existing `/api/demo` payload's `graph_prefix` provides the ID suffix; no in-process demo registry or durable alternate store is introduced.

`memory/visualization.py` calls `GRAPH.LIST` and the two parameterized `GRAPH.RO_QUERY` files in `cypher/view_*.cypher`. It never initializes users or creates nodes, relationships, indices or graph keys. Missing current graphs return an empty projection; missing demo graphs return 404. All failures from the database use the existing sanitized 503 handler. The DB user must permit graph listing and read-only queries.

- IDs in Cytoscape are graph-local internal IDs, prefixed `n`/`e`; identical logical IDs on different labels do not merge nodes accidentally.
- Every exported relationship includes its actual source, target, type and stored properties. The client never invents an edge based on a task ID or response text.
- At most **250 nodes / 600 induced edges** are loaded. Facts, procedures, agents and tasks have priority; node/edge truncation is explicit. Filtering structural nodes and focus views changes visibility, not the underlying graph.
- Source details cover the loaded subgraph and can be incomplete in a capped view. The UI says so. This is not a pagination/search interface.
- Two read queries are not a transactionally consistent snapshot under concurrent writes; displayed read time is the application retrieval time. There is no new distributed consistency claim.
- Details reflect stored properties without repairing historical metadata. In the tested legacy handoff queries, the edge's `version` can trail `Task.version`; Task state/version/token/lease remain the execution authority. The visualizer displays the actual edge value rather than fabricating equality.
- Node content is rendered with textContent. No HTML from graph properties is evaluated.

Failed graph fetches and detected network/503 failures clear the canvas, counters and selected details. Context changes clear old data and cancel/reject late requests. A successful health response alone does not resurrect stale elements; reload must fetch current graph data. The normal health poll is every 15 seconds while the main UI is idle, so detection is not instantaneous.

## Rendering budget

Cytoscape.js **3.33.1 core** is vendored locally, approximately 434 KB uncompressed, with the upstream MIT license and provenance in `app/static/vendor/`. No CDN or frontend build is required. The browser keeps one Cytoscape instance, pixel ratio 1 and bounded data. Arrangement uses deterministic preset columns/focus positions without a physics simulation or animation. No FPS or large-database benchmark is claimed; database queries can still scan more data than the returned cap.

The initial interaction test stalled because it returned a cyclic Cytoscape collection from `page.evaluate`, causing serialization pressure. The test was corrected to return nothing after emitting a click. This was a test harness problem, not evidence that graph reads or a particular layout algorithm failed. We retained the simpler preset layout for lower rendering work and predictable video composition. Visual QA also found delayed visibility counts/fit bounds; these now use explicit filtered collections and were retested. A later Task-source assertion initially assumed one source when three valid source cards were present; its selector was corrected and the full browser script passed again.

## Executed verification

| Result | Check | Evidence |
|---|---|---|
| PASS | Original 25 tests + 8 visualization tests, real FalkorDBLite over Unix socket | **33 passed**, 1 existing dependency warning; [log](verification/pytest-knowledge-graph.txt) |
| PASS | Same 33 tests against independent real local FalkorDB over TCP | **33 passed**, 1 existing dependency warning; [log](verification/pytest-knowledge-graph-tcp.txt) |
| PASS | Actual browser + new real API | Demo **42 nodes / 65 edges**; correct Rust→Python direction; 4-node/3-edge revision focus; details and source messages; [log](verification/graph-browser.txt) |
| PASS | Interactions and scope | Real mouse drag, zoom/fit/arrange, handoff, demo Bob Go, normal Alice Java, top-user switches and mobile width |
| PASS | Stale-state presentation | Injected HTTP 503 clears the graph; reload restores real data; a successful health status alone cannot restore stale elements |

The injected browser 503 above tests presentation, not a new physical DB outage. Actual backend connection-failure handling is tested with a refused TCP connection; the earlier full TCP-cut/restore experiment remains documented separately in `VALIDATION.md`. Browser screenshots were visually inspected and remain ignored under `artifacts/knowledge-graph-*.png`.

Reproduce sequentially to avoid memory pressure:

```bash
python -m pytest -q
TEST_FALKORDB_URL=redis://127.0.0.1:6379 python -m pytest -q
# Separate terminal; use a synthetic review namespace and force mock:
LLM_MODE=mock GRAPH_PREFIX=memrelay_graph_review \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
# After pytest finishes, and with optional Playwright installed:
python scripts/graph_browser_smoke.py
```

The browser script writes synthetic review data through the existing chat/demo endpoints, then tests read-only visualization. Those setup writes are distinct from visualization GETs. Live API LLM, Cloud and Docker are not newly verified by this change. No new agent behavior or external deployment is added.

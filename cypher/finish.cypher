MATCH (t:Task {id: $id}),
 (:Agent {id: 'coordinator'})-[h:HANDED_OFF_TO {task_id: $id}]->(e:Agent {id: 'executor'})
WHERE t.status = 'running' AND t.version = $version AND t.token = $token
AND t.lease_until > $time
SET t.status = $status, t.version = t.version + 1, t.updated_at = $time,
 h.status = $status, h.version = t.version, h.finished_at = $time
CREATE (r:TaskResult {id: $result_id, task_id: $id, content: $text, status: $status,
 created_at: $time})
CREATE (t)-[:PRODUCED]->(r)
CREATE (e)-[:PRODUCED]->(r)
CREATE (t)-[:TRANSITIONED]->(:TaskEvent {status: $status, version: t.version,
 at: $time, agent: 'executor'})
WITH t, r
UNWIND CASE WHEN size($memory_ids) = 0 THEN [''] ELSE $memory_ids END AS mid
OPTIONAL MATCH (m:Memory {id: mid})
FOREACH (x IN CASE WHEN m IS NULL THEN [] ELSE [1] END |
 CREATE (t)-[:USES_MEMORY]->(m) CREATE (r)-[:USES_MEMORY]->(m))
RETURN DISTINCT properties(r)

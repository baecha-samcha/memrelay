MATCH (t:Task)-[:PRODUCED]->(r:TaskResult)
OPTIONAL MATCH (r)-[:USES_MEMORY]->(m:Memory)
OPTIONAL MATCH (s:Message)-[:SUPPORTS]->(m)
WITH t, r, collect(DISTINCT {memory: properties(m), source: properties(s)}) AS evidence
RETURN {id: r.id, task_id: t.id, content: r.content, status: r.status,
 created_at: r.created_at, evidence: evidence}
ORDER BY r.created_at

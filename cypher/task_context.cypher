MATCH (t:Task {id: $id})
WHERE t.status = 'pending'
UNWIND $memory_ids AS mid
MATCH (m:Memory {id: mid}), (c:Agent {id: 'coordinator'})
MERGE (t)-[:CONSIDERED_MEMORY]->(m)
MERGE (c)-[:USES_MEMORY]->(m)
RETURN m.id

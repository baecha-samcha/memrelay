MATCH (a:Message {id: $id})
UNWIND $memory_ids AS mid
MATCH (m:Memory {id: mid})
MERGE (a)-[:USES_MEMORY]->(m)
RETURN m.id

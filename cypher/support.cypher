MATCH (s:Message {id: $source}), (m:Memory {id: $id})
MERGE (s)-[:SUPPORTS]->(m)
SET m.updated_at = $time
RETURN m.id

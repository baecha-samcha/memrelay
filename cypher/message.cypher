MATCH (u:User {id: $user})
MERGE (s:Session {id: $sid})
MERGE (u)-[:HAS_SESSION]->(s)
CREATE (m:Message {id: $id, content: $text, role: $role, created_at: $time})
CREATE (s)-[:HAS_MESSAGE]->(m)
RETURN m.id

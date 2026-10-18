MATCH (e:Entity {id: $slot})
OPTIONAL MATCH (m:Memory {status: 'active'})-[:ABOUT]->(e)
RETURN e.version, properties(m)

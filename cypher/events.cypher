MATCH (t:Task {id: $id})-[:TRANSITIONED]->(e:TaskEvent)
RETURN properties(e) ORDER BY e.version

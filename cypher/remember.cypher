MATCH (e:Entity {id: $slot}), (s:Message {id: $source})
WHERE e.version = $version
OPTIONAL MATCH (old:Memory {status: 'active'})-[:ABOUT]->(e)
SET e.version = e.version + 1
CREATE (m:Memory {id: $id, kind: $kind, content: $content, subject: $subject,
 predicate: $predicate, object: $obj, status: $status, created_at: $time,
 updated_at: $time, valid_from: $time, valid_to: 0,
 task_type: $task_type, instruction: $instruction})
CREATE (m)-[:ABOUT]->(e)
CREATE (s)-[:SUPPORTS]->(m)
FOREACH (x IN CASE WHEN $replace THEN [1] ELSE [] END |
 SET old.status = 'superseded', old.valid_to = $time, old.updated_at = $time
 CREATE (m)-[:SUPERSEDES]->(old))
RETURN properties(m)

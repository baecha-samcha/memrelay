MATCH (c:Agent {id: 'coordinator'}), (e:Agent {id: 'executor'}), (s:Message {id: $source})
MERGE (t:Task {id: $id})
ON CREATE SET t.prompt = $prompt, t.subject = $subject, t.task_type = $task_type,
 t.status = 'pending', t.version = 0, t.created_at = $time, t.updated_at = $time,
 t.lease_until = 0, t.attempts = 0
WITH c, e, s, t WHERE t.prompt = $prompt
MERGE (c)-[:CREATED]->(t)
MERGE (t)-[:ASSIGNED_TO]->(e)
MERGE (s)-[:REQUESTED]->(t)
MERGE (c)-[h:HANDED_OFF_TO {task_id: $id}]->(e)
ON CREATE SET h.created_at = $time, h.status = 'pending', h.version = 0
MERGE (t)-[:TRANSITIONED]->(initial:TaskEvent {version: 0})
ON CREATE SET initial.status = 'pending', initial.at = $time, initial.agent = 'coordinator'
RETURN properties(t)

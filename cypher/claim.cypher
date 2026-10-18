MATCH (t:Task {id: $id})-[:ASSIGNED_TO]->(:Agent {id: 'executor'}),
 (:Agent {id: 'coordinator'})-[h:HANDED_OFF_TO {task_id: $id}]->(:Agent {id: 'executor'})
WHERE t.version = $version AND (t.status = 'pending'
 OR (t.status = 'running' AND t.lease_until <= $time))
SET t.status = 'running', t.version = t.version + 1, t.token = $token,
 t.lease_until = $until, t.updated_at = $time, t.attempts = t.attempts + 1,
 h.status = 'running', h.version = t.version
CREATE (t)-[:TRANSITIONED]->(:TaskEvent {status: 'running', version: t.version,
 at: $time, agent: 'executor', token: $token})
RETURN properties(t)

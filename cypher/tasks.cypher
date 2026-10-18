MATCH (c:Agent)-[h:HANDED_OFF_TO]->(e:Agent), (t:Task)-[:ASSIGNED_TO]->(e)
WHERE h.task_id = t.id
OPTIONAL MATCH (t)-[:TRANSITIONED]->(ev:TaskEvent)
WITH c, h, e, t, collect(properties(ev)) AS events
RETURN {id: t.id, prompt: t.prompt, subject: t.subject, task_type: t.task_type,
 status: t.status, version: t.version, created_at: t.created_at,
 updated_at: t.updated_at, lease_until: t.lease_until, token: t.token,
 attempts: t.attempts, from_agent: c.id, to_agent: e.id, handoff: properties(h), events: events}
ORDER BY t.created_at

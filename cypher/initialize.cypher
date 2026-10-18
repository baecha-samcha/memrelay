MERGE (u:User {id: $user})
MERGE (:Agent {id: 'coordinator', role: 'Coordinator'})
MERGE (:Agent {id: 'executor', role: 'Executor'})
RETURN u.id

from memory.store import Conflict, DatabaseUnavailable, now


class Executor:
    """Finds work only through the user graph; fenced graph result commits."""
    def __init__(self, store):
        self.store = store

    def execute(self, user, task_id):
        task = self.store.claim(user, task_id)
        if not task:
            return {'claimed': False, 'task': self.store.task(user, task_id)}
        memories = []
        try:
            memories = self.store.memories(user, subject=task['subject'])
            facts = [m for m in memories if m['kind'] == 'semantic']
            rules = [m for m in memories if m['kind'] == 'procedural' and m['task_type'] == task['task_type']]
            if not facts:
                raise ValueError('No active semantic facts for this project')
            if any(r['instruction'] != 'bullet_list_with_sources' for r in rules):
                raise ValueError('Unsupported procedure; execution refused')
            bullets = bool(rules)
            lines = []
            for fact in facts:
                source_ids = ', '.join(s['id'] for s in fact['sources'])
                line = f"{fact['subject']} {fact['predicate']}: {fact['object']} [memory:{fact['id']}; source:{source_ids}]"
                lines.append(('- ' if bullets else '') + line)
            for rule in rules:
                lines.append(f"Applied procedure [memory:{rule['id']}]: {rule['instruction']}")
            result = self.store.finish(user, task, '\n'.join(lines), memories)
            return {'claimed': True, 'result': result}
        except (DatabaseUnavailable, Conflict):
            # Leave running lease for recovery; never report a successful commit.
            raise
        except Exception as exc:
            result = self.store.finish(user, task, f'Execution failed: {type(exc).__name__}', memories, failed=True)
            return {'claimed': True, 'result': result}

    def resume(self, user):
        eligible = [t for t in self.store.tasks(user) if t['status'] == 'pending'
                    or (t['status'] == 'running' and t['lease_until'] <= now())]
        return [self.execute(user, t['id']) for t in eligible]

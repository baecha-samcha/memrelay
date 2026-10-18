"""All durable application state lives in FalkorDB. No memory fallback."""
from pathlib import Path
import re
import time
import uuid
from threading import Lock
from falkordb import FalkorDB
from redis.exceptions import RedisError

QUERIES = Path(__file__).resolve().parents[1] / 'cypher'
USERS = {'alice', 'bob'}


class DatabaseUnavailable(RuntimeError):
    pass


class Conflict(RuntimeError):
    pass


def uid():
    return str(uuid.uuid4())


def now():
    return int(time.time() * 1000)


class Store:
    def __init__(self, url='redis://localhost:6379', prefix='memrelay', client=None):
        if not re.fullmatch(r'[a-zA-Z0-9_]+', prefix):
            raise ValueError('Invalid graph prefix')
        self.prefix = prefix
        self._db = client
        self._url = url
        self._connect_lock = Lock()

    @property
    def db(self):
        # The SDK probes INFO at construction. Delay this so the UI can start
        # with an offline database and show a controlled 503 instead of crashing.
        with self._connect_lock:
            if self._db is None:
                self._db = FalkorDB.from_url(
                    self._url, socket_connect_timeout=3, socket_timeout=8,
                    retry_on_timeout=False, decode_responses=True,
                )
        return self._db

    def graph(self, user):
        if user not in USERS:
            raise ValueError('Choose alice or bob')
        return self.db.select_graph(f'{self.prefix}_{user}')

    def query(self, graph_user, query, **params):
        try:
            return self.graph(graph_user).query(query, params).result_set
        except RedisError as exc:
            # Never leak URLs, credentials, or server error details to HTTP clients.
            raise DatabaseUnavailable('FalkorDB unavailable; memory operations stopped.') from exc

    def run(self, graph_user, name, **params):
        return self.query(graph_user, (QUERIES / f'{name}.cypher').read_text(), **params)

    def initialize(self, user):
        self.run(user, 'initialize', user=user)

    def health(self):
        self.query('alice', 'RETURN 1')
        return {'database': 'connected', 'storage': 'FalkorDB'}

    def message(self, user, text, session_id='demo', role='user'):
        self.initialize(user)
        mid = uid()
        self.run(user, 'message', user=user, sid=session_id, id=mid,
                 text=text, role=role, time=now())
        return mid

    def memories(self, user, history=False, subject=None, at=None):
        rows = self.run(user, 'memories', history=history, subject=subject or '', at=at or 0)
        return [dict(row[0]) for row in rows]

    def remember(self, user, source, kind, content, subject='', predicate='', obj='',
                 explicit=False, task_type='', instruction='', uncertain=False):
        if kind not in {'episodic', 'semantic', 'procedural'}:
            raise ValueError('Invalid memory kind')
        # A predicate slot belongs to one entity. Episodic events never supersede.
        slot = f'{kind}:{subject}:{predicate}' if kind != 'episodic' else uid()
        self.run(user, 'slot', slot=slot, subject=subject)
        for _ in range(8):
            rows = self.run(user, 'slot_read', slot=slot)
            version, current = rows[0]
            status = 'disputed' if uncertain else 'active'
            if current and kind != 'episodic':
                if current['object'] == obj and not uncertain:
                    self.run(user, 'support', source=source, id=current['id'], time=now())
                    return next(m for m in self.memories(user, history=True) if m['id'] == current['id'])
                if not explicit:
                    status = 'disputed'
            mid = uid()
            rows = self.run(user, 'remember', slot=slot, version=version, source=source,
                            id=mid, kind=kind, content=content, subject=subject,
                            predicate=predicate, obj=obj, status=status, time=now(),
                            task_type=task_type, instruction=instruction,
                            replace=bool(current and explicit and status == 'active'))
            if rows:
                return next(m for m in self.memories(user, history=True) if m['id'] == mid)
        raise Conflict('Concurrent memory update; retry the request.')

    def history(self, user, subject=''):
        return [dict(r[0]) for r in self.run(user, 'history', subject=subject)]

    def create_task(self, user, task_id, prompt, source, subject='Project Atlas', task_type='project_summary'):
        self.initialize(user)
        rows = self.run(user, 'task_create', id=task_id, prompt=prompt,
                        source=source, subject=subject, task_type=task_type, time=now())
        if not rows:
            raise Conflict('Task ID conflict or missing request source')
        task = dict(rows[0][0])
        if task['prompt'] != prompt:
            raise Conflict('Task ID already belongs to a different request')
        return task

    def tasks(self, user):
        return [dict(r[0]) for r in self.run(user, 'tasks')]

    def task(self, user, task_id):
        return next((t for t in self.tasks(user) if t['id'] == task_id), None)

    def claim(self, user, task_id, lease_ms=30000):
        task = self.task(user, task_id)
        if not task:
            raise ValueError('Unknown task')
        token = uid()
        rows = self.run(user, 'claim', id=task_id, version=task['version'],
                        time=now(), until=now() + lease_ms, token=token)
        return dict(rows[0][0]) if rows else None

    def finish(self, user, task, text, memories, failed=False):
        rows = self.run(user, 'finish', id=task['id'], token=task['token'],
                        version=task['version'], time=now(), result_id=uid(), text=text,
                        status='failed' if failed else 'completed',
                        memory_ids=[m['id'] for m in memories])
        if not rows:
            raise Conflict('Task lease expired or another executor owns the task')
        return dict(rows[0][0])

    def results(self, user):
        return [dict(r[0]) for r in self.run(user, 'results')]

    def snapshot(self, user):
        # Every request reaches FalkorDB, including an empty user's view.
        self.initialize(user)
        return {'user': user, 'memories': self.memories(user, history=True),
                'history': self.history(user), 'tasks': self.tasks(user),
                'results': self.results(user)}

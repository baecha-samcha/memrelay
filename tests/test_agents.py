from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from memory.store import Store, Conflict
from agents.executor import Executor
from tests.test_memory import coordinator


def task_setup(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Rust')
    c.chat('alice', 'For project summaries use bullet points and cite sources')
    return c.chat('alice', 'Create a project summary', task_id='task-1')['task']


def test_handoff_procedure_result_and_paths(store):
    task = task_setup(store)
    assert task['status'] == 'pending'
    result = Executor(store).execute('alice', task['id'])['result']
    assert result['content'].startswith('- Project Atlas language: Rust')
    assert 'source:' in result['content'] and 'Applied procedure' in result['content']
    current = store.task('alice', task['id'])
    assert current['status'] == 'completed' and current['version'] == 2
    assert current['from_agent'] == 'coordinator' and current['to_agent'] == 'executor'
    assert current['handoff']['status'] == 'completed'
    assert len(store.results('alice')[0]['evidence']) == 2
    assert [r[0]['status'] for r in store.run('alice', 'events', id=task['id'])] == ['pending', 'running', 'completed']


def test_duplicate_task_and_execution(store):
    task_setup(store)
    coordinator(store).chat('alice', 'Create a project summary', task_id='task-1')
    e = Executor(store)
    assert e.execute('alice', 'task-1')['claimed']
    assert not e.execute('alice', 'task-1')['claimed']
    assert len(store.tasks('alice')) == len(store.results('alice')) == 1
    with pytest.raises(Conflict):
        coordinator(store).chat('alice', 'Create a different project summary', task_id='task-1')


def test_pending_tasks_survive_agent_restart(store):
    task_setup(store)
    restart = Store(prefix=store.prefix, client=store.db)
    assert len(Executor(restart).resume('alice')) == 1
    assert restart.results('alice')[0]['status'] == 'completed'


def test_expired_lease_recovered_and_old_executor_fenced(store):
    task_setup(store)
    old = store.claim('alice', 'task-1', lease_ms=20)
    time.sleep(.03)
    newer = store.claim('alice', 'task-1')
    assert newer['version'] > old['version']
    with pytest.raises(Conflict):
        store.finish('alice', old, 'stale result', [])
    store.finish('alice', newer, 'recovered', [])
    assert len(store.results('alice')) == 1


def test_parallel_executors_commit_one_result(store):
    task_setup(store)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: Executor(store).execute('alice', 'task-1'), range(8)))
    assert sum(r['claimed'] for r in results) == 1
    assert len(store.results('alice')) == 1


def test_multiple_tasks_concurrent_read_write(store):
    task_setup(store)
    c = coordinator(store)
    for i in range(1, 8):
        c.chat('alice', 'Create a project summary', task_id=f'task-{i+1}')
    def work(t):
        store.memories('alice')
        return Executor(store).execute('alice', t['id'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(r['claimed'] for r in pool.map(work, store.tasks('alice')))
    assert len(store.results('alice')) == 8


def test_missing_knowledge_fails_task(store):
    task = coordinator(store).chat('bob', 'Create a project summary')['task']
    result = Executor(store).execute('bob', task['id'])['result']
    assert result['status'] == 'failed'
    assert store.task('bob', task['id'])['status'] == 'failed'

"""Two independent app processes, one continuously running real database."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = '''
import json, os
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from memory.store import Store
s = Store(os.environ['PROCESS_TEST_URL'], os.environ['PROCESS_TEST_PREFIX'])
with TestClient(create_app(s, Settings(llm_mode='mock'))) as client:
    if os.environ['PROCESS_TEST_PHASE'] == 'write':
        for text in ['Project Atlas uses Rust', 'Create a project summary']:
            assert client.post('/api/chat', json={'user':'alice','text':text}).status_code == 200
    else:
        assert client.post('/api/alice/resume').status_code == 200
    response = client.get('/api/alice/snapshot')
    assert response.status_code == 200
    print(json.dumps(response.json()))
'''


def test_independent_app_process_restart_recovers_memory_and_pending_task(store):
    url = os.getenv('TEST_FALKORDB_URL')
    if not url:
        path = store.db.connection.connection_pool.connection_kwargs['path']
        url = 'unix://' + path
    env = {**os.environ, 'PROCESS_TEST_URL': url, 'PROCESS_TEST_PREFIX': store.prefix}
    snapshots = []
    for phase in ('write', 'read'):
        result = subprocess.run([sys.executable, '-c', SCRIPT],
                                cwd=Path(__file__).resolve().parents[1],
                                env={**env, 'PROCESS_TEST_PHASE': phase},
                                capture_output=True, text=True, timeout=30, check=True)
        snapshots.append(json.loads(result.stdout))
    first, second = snapshots
    assert first['tasks'][0]['status'] == 'pending'
    assert second['tasks'][0]['status'] == 'completed'
    assert first['tasks'][0]['id'] == second['tasks'][0]['id']
    assert {m['id'] for m in first['memories']} == {m['id'] for m in second['memories']}
    assert second['results'][0]['content'].startswith('Project Atlas language: Rust')

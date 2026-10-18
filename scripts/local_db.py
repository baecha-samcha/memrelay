"""Docker-free real FalkorDB server. Never imported by the application."""
from pathlib import Path
import signal
import threading
from redislite.falkordb_client import FalkorDB

root = Path(__file__).resolve().parents[1] / '.data'
root.mkdir(exist_ok=True)
db = FalkorDB(str(root / 'falkordb.rdb'), serverconfig={
    'port': '6379', 'bind': '127.0.0.1', 'appendonly': 'yes',
    'appendfsync': 'everysec', 'dir': str(root), 'maxmemory-policy': 'noeviction',
})
print('Real FalkorDB listening at redis://127.0.0.1:6379. Ctrl+C to save and stop.', flush=True)
stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
signal.signal(signal.SIGINT, lambda *_: stop.set())
stop.wait()
db.connection.execute_command('SAVE')
db.connection.shutdown()

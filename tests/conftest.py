import os
import uuid
import pytest
from memory.store import Store


@pytest.fixture(scope='session')
def database(tmp_path_factory):
    url = os.getenv('TEST_FALKORDB_URL')
    if url:
        client = Store(url).db
    else:
        from redislite.falkordb_client import FalkorDB
        client = FalkorDB(str(tmp_path_factory.mktemp('falkor') / 'test.rdb'))
    yield client
    if not url:
        client.connection.shutdown()


@pytest.fixture
def store(database):
    prefix = 'test_' + uuid.uuid4().hex
    s = Store(prefix=prefix, client=database)
    yield s
    # Delete only this fixture's disposable user graphs.
    for user in ('alice', 'bob'):
        try:
            s.graph(user).delete()
        except Exception:
            pass

"""Optional standalone executor: python -m agents.worker --once."""
import argparse
import time
from agents.executor import Executor
from app.config import Settings
from memory.store import Store, DatabaseUnavailable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    s = Settings()
    executor = Executor(Store(s.url, s.prefix))
    while True:
        try:
            for user in ('alice', 'bob'):
                print(user, executor.resume(user), flush=True)
        except DatabaseUnavailable:
            print('FalkorDB disconnected; no execution.', flush=True)
        if args.once:
            return
        time.sleep(2)


if __name__ == '__main__':
    main()

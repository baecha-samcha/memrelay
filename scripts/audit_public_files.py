"""Heuristic pre-publication scan; prints metadata only, never matched values."""
import json
import os
from pathlib import Path
import re
import subprocess
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
os.chdir(root)


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, check=True).stdout


paths = sorted(set(git('ls-files', '-z').split(b'\0') +
                   git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''})
patterns = {
    'google_key_shape': re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
    'groq_key_shape': re.compile(r'gsk_[0-9A-Za-z]{20,}'),
    'openai_key_shape': re.compile(r'sk-(?:proj-)?[0-9A-Za-z_-]{20,}'),
    'github_token_shape': re.compile(r'(?:gh[pousr]_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{30,})'),
    'private_key_header': re.compile(r'^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'local_home_path': re.compile(r'/home/[A-Za-z0-9_.-]+/'),
    'email_shape': re.compile(r'\b[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]+'),
}
findings = []
for encoded in paths:
    path = Path(os.fsdecode(encoded))
    if not path.is_file():
        continue
    if (path.name.startswith('.env') and path.name != '.env.example') or path.suffix in {'.rdb', '.aof', '.pem', '.key', '.p12', '.tmp', '.bak'}:
        findings.append({'path': str(path), 'rule': 'private_or_temporary_filename'})
    try:
        text = path.read_text()
    except UnicodeError:
        findings.append({'path': str(path), 'rule': 'binary_review_required'})
        continue
    for number, line in enumerate(text.splitlines(), 1):
        for label, pattern in patterns.items():
            if pattern.search(line):
                findings.append({'path': str(path), 'line': number, 'rule': label})
    if path.name == '.env.example':
        for key, value in dotenv_values(path).items():
            if re.search(r'(?:API_KEY|PASSWORD|SECRET|TOKEN)$', key) and value:
                findings.append({'path': str(path), 'rule': 'nonempty_example_secret', 'name': key})

credentials = []
for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENAI_API_KEY'):
    credentials.append({'source': 'process', 'name': name, 'present': bool(os.getenv(name))})
for path in sorted(root.glob('.env*')):
    if path.is_file():
        values = dotenv_values(path)
        for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'OPENAI_API_KEY'):
            credentials.append({'source': path.name, 'name': name, 'present': bool(values.get(name))})

ignored = {}
for name in ('.env', '.env.local', '.venv/bin/python', '.data/falkordb.rdb',
             '.data/appendonlydir/appendonly.aof.1.incr.aof', 'artifacts/desktop.png', 'private.rdb'):
    ignored[name] = subprocess.run(['git', 'check-ignore', '-q', name]).returncode == 0
commits = git('rev-list', '--all', '--reflog').decode().splitlines()
tracked = git('ls-files', '-z').split(b'\0')[:-1]
result = {'status': 'PASS' if not findings and all(ignored.values()) else 'FAIL',
          'scope': 'Git tracked + nonignored untracked candidate files; heuristic patterns, not a universal secret detector',
          'candidate_count': len(paths), 'tracked_count': len(tracked), 'commit_count': len(set(commits)),
          'remote_count': len(git('remote').decode().splitlines()), 'ignore_checks': ignored,
          'credentials_presence_only': credentials, 'findings': findings,
          'history_note': 'No commits to inspect' if not commits else 'History exists; additional content review required'}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['status'] == 'PASS' else 1)

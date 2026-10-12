"""Reject private artifacts and obvious secrets in tracked/staged source files."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.py', '.html', '.md', '.txt', '.cmd', '.sh', '.yml', '.yaml'}
SECRET = re.compile(r'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')

def check(paths):
    errors = []
    for name in paths:
        path = Path(name)
        if any(part in {'data', '.venv', 'venv', '__pycache__'} for part in path.parts):
            errors.append(f'{name}: private runtime directory')
            continue
        if name not in {'LICENSE', '.gitignore', '.gitattributes', 'config.example.json'} and path.suffix not in ALLOWED:
            errors.append(f'{name}: unsupported public file type')
            continue
        resolved = (ROOT / path).resolve()
        if not resolved.is_relative_to(ROOT):
            errors.append(f'{name}: path escapes repository')
            continue
        if resolved.is_file() and SECRET.search(resolved.read_text(encoding='utf-8')):
            errors.append(f'{name}: potential secret')
    return errors

if __name__ == '__main__':
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True)
    paths = result.stdout.decode().strip('\0').split('\0') if result.returncode == 0 and result.stdout else []
    if not paths:
        raise SystemExit('Stage the intended public files in this repository before running this check.')
    errors = check(paths)
    if errors:
        print('\n'.join(errors))
        raise SystemExit(1)
    print(f'PASS: {len(paths)} tracked source files; no private artifact types or obvious secrets.')

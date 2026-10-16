"""Configuration littérale .env, sans exécution shell ni dépendance externe."""
import os
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    result = {}
    if not path.exists():
        return result
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not key.strip().replace('_', '').isalnum():
            raise ValueError(f'Invalid .env line {number}')
        tokens = shlex.split(value, comments=True)
        if len(tokens) > 1:
            raise ValueError(f'Quote the value on .env line {number}')
        result[key.strip()] = tokens[0] if tokens else ''
    return result


def load_config(root=ROOT):
    values = read_env(root / '.env.example')
    values.update(read_env(root / '.env'))
    values.update({key: os.environ[key] for key in values if key in os.environ})
    return values

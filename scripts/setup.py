#!/usr/bin/env python3
"""Initialise .env sans écraser les options existantes et génère la clé locale."""
import os
import re
import secrets
from config import ROOT, read_env

path = ROOT / '.env'
if not path.exists():
    path.write_text((ROOT / '.env.example').read_text())
values = read_env(path)
if not values.get('BONSAI_API_KEY'):
    key = os.environ.get('BONSAI_API_KEY') or secrets.token_hex(32)
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,}', key):
        raise SystemExit('Use an API key with at least 16 letters/digits/_/-')
    text = path.read_text()
    if re.search(r'^BONSAI_API_KEY=.*$', text, re.M):
        text = re.sub(r'^BONSAI_API_KEY=.*$', 'BONSAI_API_KEY=' + key, text, flags=re.M)
    else:
        text += '\nBONSAI_API_KEY=' + key + '\n'
    path.write_text(text)
path.chmod(0o600)
print('.env ready (existing options and key preserved; key not displayed).')

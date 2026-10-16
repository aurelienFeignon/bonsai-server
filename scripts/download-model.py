#!/usr/bin/env python3
"""Téléchargement HF épinglé, reprenable, vérifié avant renommage atomique."""
import hashlib
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from config import ROOT, load_config


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def download(config, root=ROOT):
    filename = config['MODEL_FILE']
    if Path(filename).name != filename or not filename.endswith('.gguf'):
        raise ValueError('MODEL_FILE must be a GGUF basename')
    expected = config['MODEL_SHA256'].lower()
    if not re.fullmatch('[a-f0-9]{64}', expected):
        raise ValueError('MODEL_SHA256 must contain 64 hexadecimal characters')
    directory = Path(config['MODEL_DIR']).expanduser()
    if not directory.is_absolute():
        directory = root / directory
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if target.exists():
        if checksum(target) != expected:
            raise ValueError('Existing model checksum differs; rename it before downloading another model')
        print(f'Model already verified: {target}')
        return target
    partial = target.with_suffix(target.suffix + '.part')
    offset = partial.stat().st_size if partial.exists() else 0
    repo = urllib.parse.quote(config['MODEL_REPO'], safe='/')
    revision = urllib.parse.quote(config['MODEL_REVISION'], safe='')
    name = urllib.parse.quote(filename, safe='')
    request = urllib.request.Request(f'https://huggingface.co/{repo}/resolve/{revision}/{name}',
                                    headers={'Range': f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(request, timeout=60) as response:
        resume = offset > 0 and response.status == 206
        if resume and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
            raise ValueError('Unexpected Content-Range for resumed download')
        with partial.open('ab' if resume else 'wb') as stream:
            while block := response.read(1024*1024):
                stream.write(block)
    size = config.get('MODEL_SIZE_BYTES', '')
    if size and partial.stat().st_size != int(size):
        raise ValueError('Model size differs; partial file preserved for inspection/resume')
    if checksum(partial) != expected:
        raise ValueError('Model SHA-256 differs; partial file preserved, not activated')
    os.replace(partial, target)
    print(f'Model downloaded and verified: {target}')
    return target


if __name__ == '__main__':
    download(load_config())

#!/usr/bin/env python3
"""Vérifie identité, contexte/slots effectifs, clé obligatoire et génération JSON."""
import json
import urllib.request
import urllib.error
from config import load_config

cfg = load_config()
host = cfg['BONSAI_BIND'] if cfg['BONSAI_BIND'] not in {'0.0.0.0', '::'} else '127.0.0.1'
base = 'http://' + host + ':' + cfg['BONSAI_PORT']


def http(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base+path, data=data, headers={
        'content-type': 'application/json', 'authorization': 'Bearer '+cfg['BONSAI_API_KEY']})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


assert http('/health')['status'] == 'ok'
try:
    urllib.request.urlopen(base+'/v1/models', timeout=5)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError('API key was not required')
props = http('/props')
assert props['total_slots'] == int(cfg['BONSAI_PARALLEL'])
# Le runtime répartit le contexte total entre les slots.
assert props['default_generation_settings']['n_ctx'] == int(cfg['BONSAI_CTX_SIZE']) // int(cfg['BONSAI_PARALLEL'])
assert any(m['id'] == cfg['BONSAI_MODEL_ALIAS'] for m in http('/v1/models')['data'])
response = http('/v1/chat/completions', {
    'model': cfg['BONSAI_MODEL_ALIAS'], 'messages': [{'role': 'user', 'content': 'Return only JSON with ready true.'}],
    'max_tokens': 32, 'temperature': 0,
    'response_format': {'type': 'json_schema', 'json_schema': {'name': 'ready', 'schema': {
        'type': 'object', 'properties': {'ready': {'type': 'boolean', 'const': True}},
        'required': ['ready'], 'additionalProperties': False}}},
})
assert json.loads(response['choices'][0]['message']['content'])['ready'] is True
print(json.dumps({'status': 'ok', 'alias': cfg['BONSAI_MODEL_ALIAS'], 'context': cfg['BONSAI_CTX_SIZE'],
                  'slots': cfg['BONSAI_PARALLEL'], 'timings': response.get('timings')}))

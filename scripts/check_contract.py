"""Run against a live backend: python scripts/check_contract.py https://YOUR-API"""
import json
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8000'

def request(method, path, body=None, headers=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=payload, headers={'Content-Type':'application/json', **(headers or {})}, method=method)
    try:
        with urlopen(req, timeout=60) as res:
            return res.status, json.load(res)
    except HTTPError as exc:
        return exc.code, json.load(exc)

def verify(label, okay, data):
    print(f"{'PASS' if okay else 'FAIL'}  {label}  {json.dumps(data, ensure_ascii=False)[:180]}")
    if not okay: raise SystemExit(1)

prefix = 'test-' + uuid.uuid4().hex[:12]
status, health = request('GET', '/health')
verify('health', status == 200 and health.get('keys_configured',0)>=2 and health.get('cache_enabled') is True, health)
question = f'Reply with only the word pineapple. Unique marker: {prefix}'
status, live = request('POST','/chat', {'session_id': prefix+'-a','message':question})
verify('live response', status == 200 and live.get('metadata',{}).get('resolution_source') == 'LIVE_INFERENCE', live)
status, cache = request('POST','/chat', {'session_id':prefix+'-b','message':question})
verify('cross-session cache', status == 200 and cache.get('reply') == live['reply'] and cache.get('metadata',{}).get('resolution_source') == 'LLM_CACHE' and cache['metadata']['key_id'] is None, cache)
status, failover = request('POST','/chat', {'session_id':prefix+'-c','message':'A different question: say hello'}, {'X-Simulate-Failure':'key_1=429'})
verify('failover to key_2', status == 200 and failover.get('metadata',{}).get('key_id') == 'key_2' and failover['metadata']['fallback_attempts'] == 1, failover)
status, failure = request('POST','/chat', {'session_id':prefix+'-d','message':'Should fail'}, {'X-Simulate-Failure':'*=429'})
verify('clean all-key failure', status == 503 and failure == {'detail':'all providers unavailable'}, failure)
status, missing = request('GET', f'/sessions/{prefix}-d/messages')
verify('failed request not persisted', status == 404, missing)
status, history = request('GET', f'/sessions/{prefix}-a/messages')
verify('SQLite history', status == 200 and len(history.get('messages',[]))==2, history)
status, invalid = request('POST','/chat', {'session_id':prefix,'message':' '})
verify('422 input validation', status == 422, invalid)
print('\nAll live API acceptance checks passed.')

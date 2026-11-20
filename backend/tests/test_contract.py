import asyncio
import hashlib
from collections import defaultdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import MessageStore
from app.gateway import AllProvidersUnavailable, LLMAnswer, parse_simulation, is_retryable
from app.main import create_app


class FakeGateway:
    """Deterministic stand-in. Does not pretend to test provider API or LiteLLM internals."""
    def __init__(self):
        self.cache = {}
        self.calls = 0
        self.fail_all = False
        self.seen_messages = []

    async def complete(self, messages, simulation=None):
        self.calls += 1
        self.seen_messages.append(messages)
        simulation = simulation or {}
        if '*' in simulation or self.fail_all:
            raise AllProvidersUnavailable()
        # Cache key intentionally covers system+history+latest user message.
        signature = repr(messages)
        if not simulation and signature in self.cache:
            old = self.cache[signature]
            return LLMAnswer(old.reply, old.model, old.input_tokens, old.output_tokens, None, 0, 'LLM_CACHE')
        attempts = 1 if 'key_1' in simulation else 0
        answer = LLMAnswer(f"Reply to: {messages[-1]['content']}", 'gemini/gemini-2.5-flash', len(signature) // 4, 7, 'key_2' if attempts else 'key_1', attempts, 'LIVE_INFERENCE')
        if not simulation:
            self.cache[signature] = answer
        return answer


@pytest.fixture
def fixture_client(tmp_path):
    settings = Settings(
        llm_api_keys=('secret-1', 'secret-2'),
        database_url=f'sqlite:///{tmp_path}/app.db',
        allowed_origins=('http://localhost:3000', 'https://demo.vercel.app'),
        enable_failure_simulation=True,
        model='gemini/gemini-2.5-flash',
        default_system_prompt='You are helpful.',
        request_timeout=45,
    )
    gateway = FakeGateway()
    store = MessageStore(settings.database_url)
    with TestClient(create_app(settings, store, gateway)) as client:
        yield client, gateway, store


def test_health_and_cors(fixture_client):
    c, _, _ = fixture_client
    assert c.get('/health').json() == {'status':'ok','keys_configured':2,'cache_enabled':True}
    preflight = c.options('/chat', headers={'Origin':'https://demo.vercel.app','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,x-simulate-failure'})
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == 'https://demo.vercel.app'


def test_contract_and_metadata(fixture_client):
    c, _, _ = fixture_client
    result = c.post('/chat', json={'session_id':'first', 'message':'hello'})
    assert result.status_code == 200
    body = result.json()
    assert body['session_id'] == 'first'
    assert body['reply'] == 'Reply to: hello'
    assert set(body['metadata']) == {'resolution_source', 'model', 'latency_ms', 'input_tokens', 'output_tokens', 'key_id', 'fallback_attempts'}
    assert body['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    assert body['metadata']['key_id'] == 'key_1'
    assert isinstance(body['metadata']['latency_ms'], int)
    assert body['metadata']['input_tokens'] > 0
    assert body['metadata']['output_tokens'] == 7


def test_history_and_multi_turn(fixture_client):
    c, gateway, _ = fixture_client
    c.post('/chat', json={'session_id':'alice', 'message':'My name is Alice.'})
    c.post('/chat', json={'session_id':'alice', 'message':'What is my name?'})
    history = c.get('/sessions/alice/messages')
    assert history.status_code == 200
    messages = history.json()['messages']
    assert [x['role'] for x in messages] == ['user', 'assistant', 'user', 'assistant']
    assert messages[0]['content'] == 'My name is Alice.'
    assert messages[1]['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    assert gateway.seen_messages[1][1:][0]['content'] == 'My name is Alice.'
    assert c.get('/sessions/unknown/messages').json() == {'detail':'session not found'}
    assert c.get('/sessions/unknown/messages').status_code == 404
    assert c.get('/sessions/bob/messages').status_code == 404


def test_cache_across_new_sessions(fixture_client):
    c, _, _ = fixture_client
    first = c.post('/chat', json={'session_id':'a', 'message':'Same question'}).json()
    second = c.post('/chat', json={'session_id':'b', 'message':'Same question'}).json()
    third = c.post('/chat', json={'session_id':'c', 'message':'Different question'}).json()
    assert second['reply'] == first['reply']
    assert second['metadata']['resolution_source'] == 'LLM_CACHE'
    assert second['metadata']['key_id'] is None
    assert second['metadata']['fallback_attempts'] == 0
    assert second['metadata']['input_tokens'] == first['metadata']['input_tokens']
    assert second['metadata']['output_tokens'] == first['metadata']['output_tokens']
    assert third['metadata']['resolution_source'] == 'LIVE_INFERENCE'


@pytest.mark.parametrize('value', ['key_1=429', 'key_1=500'])
def test_failover(fixture_client, value):
    c, _, _ = fixture_client
    response = c.post('/chat', headers={'X-Simulate-Failure':value}, json={'session_id':value, 'message':'hi'})
    assert response.status_code == 200
    meta = response.json()['metadata']
    assert meta['key_id'] == 'key_2'
    assert meta['fallback_attempts'] == 1
    assert meta['resolution_source'] == 'LIVE_INFERENCE'


def test_fail_all_never_persists(fixture_client):
    c, _, _ = fixture_client
    response = c.post('/chat', headers={'X-Simulate-Failure':'*=429'}, json={'session_id':'failed', 'message':'hello'})
    assert response.status_code == 503
    assert response.json() == {'detail':'all providers unavailable'}
    assert c.get('/sessions/failed/messages').status_code == 404


def test_bad_requests_never_persist(fixture_client):
    c, _, _ = fixture_client
    for body in ({'session_id':'bad','message':' '}, {'session_id':'','message':'hello'}, {'session_id':'bad','message':'x'*4001}, {'message':'missing session'}, {}):
        response = c.post('/chat', json=body)
        assert response.status_code == 422
        assert 'detail' in response.json()
    malformed = c.post('/chat', data='{', headers={'Content-Type':'application/json'})
    assert malformed.status_code == 422
    assert c.get('/sessions/bad/messages').status_code == 404


def test_system_prompt_and_sessions_are_isolated(fixture_client):
    c, gateway, _ = fixture_client
    c.post('/chat', json={'session_id':'a','message':'A','system_prompt':'Custom prompt'})
    c.post('/chat', json={'session_id':'a','message':'B'})
    c.post('/chat', json={'session_id':'b','message':'B'})
    assert gateway.seen_messages[1][0]['content'] == 'Custom prompt'
    assert gateway.seen_messages[2][0]['content'] == 'You are helpful.'
    assert len(c.get('/sessions/b/messages').json()['messages']) == 2


def test_database_survives_reopen(fixture_client):
    c, _, store = fixture_client
    c.post('/chat', json={'session_id':'persist','message':'Remember me'})
    other = MessageStore(f'sqlite:///{store.path}')
    assert len(other.get_history('persist')) == 2


def test_simulator_parsing_and_retryable():
    assert parse_simulation('key_1=429,key_2=500') == {'key_1':429, 'key_2':500}
    assert parse_simulation('*=429') == {'*':429}
    assert parse_simulation('bad stuff') == {}
    class Failure(Exception):
        status_code = 429
    assert is_retryable(Failure())

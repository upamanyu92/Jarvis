"""
Tests for agent_service – chat endpoint and memory module.
"""

import importlib
import importlib.util
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Service root – used for explicit module loading
AGENT_SERVICE_DIR = os.path.join(os.path.dirname(__file__), '..', 'agent_service')

# Use a shared in-memory SQLite so all connections see the same tables
os.environ['DATABASE_URL'] = 'sqlite:///file::memory:?cache=shared&uri=true'

# Ensure agent_service is on the path BEFORE any other service
if AGENT_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AGENT_SERVICE_DIR)

# Import memory module directly (we control the path)
import memory  # noqa: E402  (path already set above)


def _load_agent_main():
    """Load agent_service/main.py, clearing any stale cached module."""
    sys.modules.pop('main', None)
    spec = importlib.util.spec_from_file_location(
        'main', os.path.join(AGENT_SERVICE_DIR, 'main.py')
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['main'] = mod
    spec.loader.exec_module(mod)
    return mod


class TestMemoryModule(unittest.TestCase):
    """Unit tests for memory.py functions."""

    def test_save_and_get_memory(self):
        from memory import get_memory, save_memory

        user_id = 'test_memory_user_01'
        save_memory(user_id, 'user', 'Hello there!', 'happy')
        save_memory(user_id, 'assistant', 'Hi! Great to hear from you!', None)

        history = get_memory(user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[0]['content'], 'Hello there!')
        self.assertEqual(history[0]['emotion'], 'happy')
        self.assertEqual(history[1]['role'], 'assistant')

    def test_get_memory_limit(self):
        from memory import get_memory, save_memory

        user_id = 'test_memory_user_02'
        for i in range(15):
            save_memory(user_id, 'user', f'Message {i}', 'neutral')

        history = get_memory(user_id, limit=5)
        self.assertEqual(len(history), 5)

    def test_user_profile_create_and_update(self):
        from memory import get_user_profile, update_user_profile

        user_id = 'test_profile_user_01'
        profile = get_user_profile(user_id)
        self.assertEqual(profile['user_id'], user_id)
        self.assertIsNone(profile['name'])

        update_user_profile(user_id, name='Alice', preferences={'theme': 'dark'})
        profile = get_user_profile(user_id)
        self.assertEqual(profile['name'], 'Alice')
        self.assertEqual(profile['preferences']['theme'], 'dark')

    def test_emotion_patterns(self):
        from memory import get_emotion_patterns, save_memory

        user_id = 'test_emotion_user_01'
        save_memory(user_id, 'user', 'I am sad today', 'sad')
        save_memory(user_id, 'user', 'Feeling better now', 'happy')

        patterns = get_emotion_patterns(user_id)
        self.assertGreaterEqual(len(patterns), 1)
        self.assertIn(patterns[0]['emotion'], ['sad', 'happy'])


class TestAgentEndpoints(unittest.TestCase):
    """Unit tests for agent_service FastAPI endpoints."""

    def _make_client(self):
        # Patch the Ollama HTTP call
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {
                'message': {'content': 'I hear you – it sounds tough.'},
            }
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            agent_main = _load_agent_main()
            from fastapi.testclient import TestClient
            return TestClient(agent_main.app)

    def test_health(self):
        client = self._make_client()
        resp = client.get('/health')
        self.assertEqual(resp.status_code, 200)

    def test_chat_empty_text(self):
        client = self._make_client()
        resp = client.post('/chat', json={'user_id': 'u1', 'text': '', 'emotion': 'neutral'})
        self.assertEqual(resp.status_code, 400)

    def test_memory_endpoints(self):
        from memory import save_memory

        user_id = 'test_api_user_01'
        save_memory(user_id, 'user', 'Test message', 'neutral')

        client = self._make_client()
        resp = client.get(f'/memory/{user_id}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['user_id'], user_id)
        self.assertIsInstance(data['history'], list)

    def test_profile_endpoints(self):
        user_id = 'test_profile_api_01'
        client = self._make_client()

        resp = client.get(f'/profile/{user_id}')
        self.assertEqual(resp.status_code, 200)

        resp = client.put(f'/profile/{user_id}', json={'name': 'Bob'})
        self.assertEqual(resp.status_code, 200)

        resp = client.get(f'/profile/{user_id}')
        self.assertEqual(resp.json()['name'], 'Bob')


if __name__ == '__main__':
    unittest.main()

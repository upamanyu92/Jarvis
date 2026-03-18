"""Integration test – full pipeline smoke test."""

import importlib
import importlib.util
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Use a shared in-memory SQLite so all connections see the same tables
os.environ['DATABASE_URL'] = 'sqlite:///file::memory:?cache=shared&uri=true'

AGENT_SERVICE_DIR = os.path.join(os.path.dirname(__file__), '..', 'agent_service')
if AGENT_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AGENT_SERVICE_DIR)


def _load_agent_main():
    sys.modules.pop('main', None)
    spec = importlib.util.spec_from_file_location(
        'main', os.path.join(AGENT_SERVICE_DIR, 'main.py')
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['main'] = mod
    spec.loader.exec_module(mod)
    return mod


class TestFullPipeline(unittest.TestCase):
    """
    Smoke tests simulating the complete data flow:
    (emotion) + (text) → agent → response → (tts)
    """

    def test_agent_builds_correct_prompt(self):
        """Verify that the system prompt includes the detected emotion."""
        agent_main = _load_agent_main()
        prompt = agent_main._build_system_prompt('user_pipeline_01', 'sad')
        self.assertIn('sad', prompt)
        self.assertIn('Jarvis', prompt)

    def test_agent_fallback_response(self):
        """Fallback response should be non-empty for every emotion."""
        agent_main = _load_agent_main()
        for emotion in ['happy', 'sad', 'angry', 'fear', 'neutral']:
            resp = agent_main._fallback_response('I need help', emotion)
            self.assertTrue(len(resp) > 0, f"Empty fallback for emotion={emotion}")

    def test_memory_round_trip(self):
        """Save a message and retrieve it back."""
        from memory import get_memory, save_memory
        uid = 'pipeline_test_user'
        save_memory(uid, 'user', 'Feeling anxious', 'fear')
        history = get_memory(uid)
        found = any(h['content'] == 'Feeling anxious' for h in history)
        self.assertTrue(found)


if __name__ == '__main__':
    unittest.main()

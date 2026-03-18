"""
Tests for tts_service – text-to-speech synthesis endpoint.
Mocks gTTS to avoid network calls.
"""

import os
import sys
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

# Add tts_service to the module search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tts_service'))


class TestTTSService(unittest.TestCase):
    """Unit tests for the TTS synthesis service."""

    def setUp(self):
        self.gtts_patcher = patch('gtts.gTTS')
        mock_gtts_cls = self.gtts_patcher.start()
        mock_gtts = MagicMock()
        mock_gtts.write_to_fp = lambda fp: fp.write(b'\xff\xfb\x90\x00' * 10)
        mock_gtts_cls.return_value = mock_gtts

    def tearDown(self):
        self.gtts_patcher.stop()
        sys.modules.pop('main', None)

    def _make_client(self):
        import main as tts_main
        from fastapi.testclient import TestClient
        return TestClient(tts_main.app)

    def test_health(self):
        client = self._make_client()
        resp = client.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')

    def test_synthesize_returns_audio(self):
        client = self._make_client()
        resp = client.post('/synthesize', json={'text': 'Hello, world!'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('audio', resp.headers.get('content-type', ''))

    def test_synthesize_empty_text(self):
        client = self._make_client()
        resp = client.post('/synthesize', json={'text': ''})
        self.assertEqual(resp.status_code, 400)

    def test_synthesize_whitespace_only(self):
        client = self._make_client()
        resp = client.post('/synthesize', json={'text': '   '})
        self.assertEqual(resp.status_code, 400)

    def test_synthesize_custom_language(self):
        client = self._make_client()
        resp = client.post('/synthesize', json={'text': 'Bonjour!', 'language': 'fr'})
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()

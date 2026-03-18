"""
Tests for speech_service – transcription endpoint.
Mocks the Whisper model to avoid loading large model files.
"""

import importlib
import importlib.util
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

SPEECH_SERVICE_DIR = os.path.join(os.path.dirname(__file__), '..', 'speech_service')

# Inject a stub 'whisper' module so the service can be imported without
# the real (large) openai-whisper package being installed.
_whisper_stub = MagicMock()
_whisper_stub.load_model.return_value = MagicMock()
sys.modules.setdefault('whisper', _whisper_stub)


def _load_speech_main():
    """Load speech_service/main.py with fresh state."""
    sys.modules.pop('main', None)
    spec = importlib.util.spec_from_file_location(
        'main', os.path.join(SPEECH_SERVICE_DIR, 'main.py')
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['main'] = mod
    spec.loader.exec_module(mod)
    return mod


class TestSpeechService(unittest.TestCase):
    """Unit tests for the speech transcription service."""

    def setUp(self):
        # Configure the stub model to return expected transcription results
        self.mock_model = MagicMock()
        self.mock_model.transcribe.return_value = {
            'text': ' Hello, how are you?',
            'language': 'en',
        }
        _whisper_stub.load_model.return_value = self.mock_model

    def tearDown(self):
        sys.modules.pop('main', None)

    def _make_client(self):
        speech_main = _load_speech_main()
        from fastapi.testclient import TestClient
        return TestClient(speech_main.app)

    def test_health(self):
        client = self._make_client()
        resp = client.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')

    def test_transcribe_audio(self):
        dummy_audio = io.BytesIO(b'RIFF\x00\x00\x00\x00WAVEfmt ')
        client = self._make_client()
        resp = client.post(
            '/transcribe',
            files={'audio': ('test.wav', dummy_audio, 'audio/wav')},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['text'], 'Hello, how are you?')
        self.assertEqual(data['language'], 'en')

    def test_transcribe_no_file(self):
        client = self._make_client()
        resp = client.post('/transcribe')
        self.assertEqual(resp.status_code, 422)  # Validation error

    def test_transcribe_strips_text(self):
        """Leading/trailing whitespace in Whisper output should be stripped."""
        self.mock_model.transcribe.return_value = {'text': '  spaces around  ', 'language': 'en'}
        dummy_audio = io.BytesIO(b'fake audio data')
        client = self._make_client()
        resp = client.post(
            '/transcribe',
            files={'audio': ('clip.wav', dummy_audio, 'audio/wav')},
        )
        self.assertEqual(resp.json()['text'], 'spaces around')



if __name__ == '__main__':
    unittest.main()

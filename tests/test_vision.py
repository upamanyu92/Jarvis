"""
Tests for vision_service – emotion detection endpoint.
Runs against a live vision_service or mocks DeepFace.
"""

import base64
import importlib
import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

VISION_SERVICE_DIR = os.path.join(os.path.dirname(__file__), '..', 'vision_service')

# Stub out heavy optional packages so tests run without installing them
_deepface_stub = MagicMock()
_deepface_DeepFace = MagicMock()
_deepface_stub.DeepFace = _deepface_DeepFace
sys.modules.setdefault('deepface', _deepface_stub)


def _load_vision_main():
    """Load vision_service/main.py with fresh state."""
    sys.modules.pop('main', None)
    spec = importlib.util.spec_from_file_location(
        'main', os.path.join(VISION_SERVICE_DIR, 'main.py')
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules['main'] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEmotionDetection(unittest.TestCase):
    """Unit tests for emotion detection with mocked DeepFace."""

    def setUp(self):
        # Configure the DeepFace stub to return expected results
        _deepface_DeepFace.analyze.return_value = [{
            'dominant_emotion': 'happy',
            'emotion': {
                'happy': 85.3,
                'sad': 2.1,
                'neutral': 10.1,
                'angry': 1.0,
                'fear': 0.5,
                'surprise': 0.8,
                'disgust': 0.2,
            },
        }]

    def tearDown(self):
        sys.modules.pop('main', None)

    def _make_client(self):
        import cv2
        import numpy as np
        vision_main = _load_vision_main()
        from fastapi.testclient import TestClient
        return TestClient(vision_main.app)

    def test_health(self):
        client = self._make_client()
        resp = client.get('/health')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')

    def test_detect_emotion_happy(self):
        import numpy as np
        import cv2

        # Create a tiny white dummy image and base64-encode it
        dummy = np.ones((10, 10, 3), dtype=np.uint8) * 255
        _, buf = cv2.imencode('.jpg', dummy)
        b64 = base64.b64encode(buf.tobytes()).decode()

        client = self._make_client()
        resp = client.post('/detect-emotion', json={'image_b64': b64})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['emotion'], 'happy')
        self.assertGreater(data['confidence'], 0.0)
        self.assertIn('happy', data['all_emotions'])

    def test_detect_emotion_invalid_image(self):
        client = self._make_client()
        resp = client.post('/detect-emotion', json={'image_b64': 'not_valid_base64!!'})
        # Should either return 400 or gracefully return neutral
        self.assertIn(resp.status_code, [200, 400])

    def test_detect_emotion_fallback_on_no_face(self):
        """When DeepFace raises, service should fall back to neutral."""
        import numpy as np
        import cv2
        _deepface_DeepFace.analyze.side_effect = Exception('No face detected')

        dummy = np.ones((10, 10, 3), dtype=np.uint8) * 128
        _, buf = cv2.imencode('.jpg', dummy)
        b64 = base64.b64encode(buf.tobytes()).decode()

        client = self._make_client()
        resp = client.post('/detect-emotion', json={'image_b64': b64})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['emotion'], 'neutral')
        # Reset side effect for subsequent tests
        _deepface_DeepFace.analyze.side_effect = None

    def test_confidence_normalized(self):
        """Confidence should be in [0, 1]."""
        import numpy as np
        import cv2
        dummy = np.ones((10, 10, 3), dtype=np.uint8) * 200
        _, buf = cv2.imencode('.jpg', dummy)
        b64 = base64.b64encode(buf.tobytes()).decode()

        client = self._make_client()
        resp = client.post('/detect-emotion', json={'image_b64': b64})
        data = resp.json()
        self.assertLessEqual(data['confidence'], 1.0)
        self.assertGreaterEqual(data['confidence'], 0.0)


if __name__ == '__main__':
    unittest.main()

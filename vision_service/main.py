"""
Vision Service - Webcam frame capture + facial emotion detection.

Endpoints:
  POST /detect-emotion  – Accept a base64-encoded JPEG and return detected emotion.
  GET  /health          – Health check.
"""

import base64
import io
import logging
import os
from typing import Optional

import cv2
import numpy as np
from deepface import DeepFace
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vision Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FrameRequest(BaseModel):
    """Request model for emotion detection."""
    image_b64: str  # Base64-encoded JPEG/PNG image


class EmotionResponse(BaseModel):
    """Response model for detected emotion."""
    emotion: str
    confidence: float
    all_emotions: dict


@app.get("/health")
def health():
    return {"status": "ok", "service": "vision_service"}


@app.post("/detect-emotion", response_model=EmotionResponse)
def detect_emotion(request: FrameRequest):
    """
    Detect the dominant facial emotion from a base64-encoded image frame.
    Returns the dominant emotion and confidence scores for all emotions.
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_b64)
        np_arr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Run emotion analysis via DeepFace
        results = DeepFace.analyze(
            img_path=frame,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,
        )

        # DeepFace can return a list or a single dict
        if isinstance(results, list):
            result = results[0]
        else:
            result = results

        dominant_emotion: str = result.get("dominant_emotion", "neutral")
        emotion_scores: dict = result.get("emotion", {})
        confidence: float = float(emotion_scores.get(dominant_emotion, 0.0))

        # Normalize confidence to [0, 1]
        if confidence > 1.0:
            confidence = confidence / 100.0

        return EmotionResponse(
            emotion=dominant_emotion,
            confidence=round(confidence, 4),
            all_emotions={k: round(float(v) / 100.0 if float(v) > 1.0 else float(v), 4)
                          for k, v in emotion_scores.items()},
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Emotion detection failed: %s", exc)
        # Graceful fallback – return neutral when face is not found
        return EmotionResponse(
            emotion="neutral",
            confidence=0.0,
            all_emotions={},
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

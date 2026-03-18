"""
TTS Service – Convert response text to speech audio using gTTS.

Endpoints:
  POST /synthesize  – Accept text, return MP3 audio bytes.
  GET  /health      – Health check.
"""

import io
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from gtts import gTTS
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TTS Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
DEFAULT_SLOW = os.getenv("TTS_SLOW", "false").lower() == "true"


class TTSRequest(BaseModel):
    text: str
    language: str = DEFAULT_LANGUAGE
    slow: bool = DEFAULT_SLOW


@app.get("/health")
def health():
    return {"status": "ok", "service": "tts_service"}


@app.post("/synthesize")
def synthesize(request: TTSRequest):
    """
    Convert text to speech and return the MP3 audio as a streaming response.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must not be empty")

    try:
        tts = gTTS(text=text, lang=request.language, slow=request.slow)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"},
        )
    except Exception as exc:
        logger.exception("TTS synthesis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

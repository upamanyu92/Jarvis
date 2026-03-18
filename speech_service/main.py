"""
Speech Service - Microphone audio → text transcription via OpenAI Whisper.

Endpoints:
  POST /transcribe  – Accept a WAV/WEBM audio file upload and return transcription.
  GET  /health      – Health check.
"""

import logging
import os
import tempfile

import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Speech Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper model once at startup (tiny = fast, base = better accuracy)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
logger.info("Loading Whisper model: %s", WHISPER_MODEL)
_model = whisper.load_model(WHISPER_MODEL)
logger.info("Whisper model loaded.")


class TranscriptionResponse(BaseModel):
    text: str
    language: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "speech_service"}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: UploadFile = File(...)):
    """
    Transcribe uploaded audio file (WAV, WEBM, MP3, etc.) to text using Whisper.
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    suffix = os.path.splitext(audio.filename)[-1] or ".wav"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            contents = await audio.read()
            tmp.write(contents)
            tmp_path = tmp.name

        result = _model.transcribe(tmp_path)
        text: str = result.get("text", "").strip()
        language: str = result.get("language", "en")

        return TranscriptionResponse(text=text, language=language)

    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription error: {exc}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

"""Global constants, paths, and configuration for the pipeline."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = BASE_DIR / "storage"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUTS_DIR = STORAGE_DIR / "outputs"

for _dir in (STORAGE_DIR, DOWNLOADS_DIR, TEMP_DIR, OUTPUTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# LLM configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# faster-whisper configuration
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

# Clip constraints
CLIP_MIN_DURATION = 25.0
CLIP_MAX_DURATION = 60.0

# Visual tracking
FACE_TRACK_EMA_ALPHA = 0.08
OUTPUT_ASPECT_RATIO = 9 / 16

# Subtitle styling
SUBTITLE_FONT = "Arial Black"
SUBTITLE_FONT_SIZE = 84
SUBTITLE_WORDS_PER_GROUP = 4

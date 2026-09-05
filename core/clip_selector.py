"""LLM-based viral clip extraction with strict JSON schema enforcement."""
import json
from typing import Any

from pydantic import BaseModel, Field

import config

SYSTEM_PROMPT = """You are a viral short-form video editor. Given a word-level transcript \
with timestamps, identify the best candidate segments for YouTube Shorts.

Rules:
- Each clip must be between 25 and 60 seconds long.
- Each clip must open with a strong, attention-grabbing 3-second hook.
- Start and end times must snap to clean sentence boundaries (do not cut off mid-sentence).
- Assign a virality_score from 0-100 estimating viewer retention/shareability.
- Return only clips genuinely likely to perform well; quality over quantity."""


class ClipCandidate(BaseModel):
    start: float = Field(..., description="Clip start time in seconds")
    end: float = Field(..., description="Clip end time in seconds")
    hook: str = Field(..., description="The 3-second hook line/summary")
    title: str = Field(..., description="Suggested short title for the clip")
    virality_score: int = Field(..., ge=0, le=100)


class ClipSelectionResult(BaseModel):
    clips: list[ClipCandidate]


def _format_transcript(words: list[dict]) -> str:
    lines = [f"[{w['start']:.2f}-{w['end']:.2f}] {w['word']}" for w in words]
    return "\n".join(lines)


def _select_with_gemini(transcript_text: str) -> ClipSelectionResult:
    from google import genai

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\nTranscript:\n{transcript_text}",
        config={
            "response_mime_type": "application/json",
            "response_schema": ClipSelectionResult,
        },
    )
    return ClipSelectionResult.model_validate_json(response.text)


def _select_with_openai(transcript_text: str) -> ClipSelectionResult:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript_text}"},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    data: dict[str, Any] = json.loads(content)
    return ClipSelectionResult.model_validate(data)


def select_clips(words: list[dict], provider: str | None = None) -> list[ClipCandidate]:
    """Feed word-level transcript into an LLM and return viral clip candidates."""
    provider = (provider or config.LLM_PROVIDER).lower()
    transcript_text = _format_transcript(words)

    if provider == "gemini":
        result = _select_with_gemini(transcript_text)
    elif provider == "openai":
        result = _select_with_openai(transcript_text)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    valid_clips = [
        clip
        for clip in result.clips
        if config.CLIP_MIN_DURATION <= (clip.end - clip.start) <= config.CLIP_MAX_DURATION
    ]
    return sorted(valid_clips, key=lambda c: c.virality_score, reverse=True)

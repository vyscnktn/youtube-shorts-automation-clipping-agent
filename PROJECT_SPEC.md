# SPECIFICATION: YouTube Shorts Automation & AI Clipping Agent System

## 1. Project Overview & Architecture
An end-to-end automated pipeline to ingest full-length YouTube videos, identify high-engagement segments (30–60 seconds), reframe 16:9 landscape footage into dynamic 9:16 vertical format (with face-tracking auto-crop and blurred background fallbacks), generate synchronized animated subtitles (Karaoke ASS format), and publish selected clips directly to YouTube Shorts via YouTube Data API v3 within a Streamlit dashboard.

```
[YouTube URL]
     │
     ▼
[yt-dlp Ingestion] ──► Extracts 1080p Video + Audio (.mp3/.wav)
     │
     ▼
[faster-whisper Transcription] ──► Word-level Timestamps (JSON)
     │
     ▼
[LLM Highlight Selector] ──► Identifies Viral 30-60s Windows (Start, End, Hook, Virality Score)
     │
     ▼
[Computer Vision Engine (MediaPipe)] ──► Tracks Active Speaker Bounding Boxes & Smooths Pan (X-center)
     │
     ▼
[FFmpeg Compositor] ──► 9:16 Reframing + Animated ASS Subtitle Burn-In
     │
     ▼
[Streamlit Interactive UI] ──► Review Clips, Edit Captions & Metadata, Trigger Upload
     │
     ▼
[YouTube Data API v3] ──► Uploads as Shorts with #Shorts Tag & Thumbnail
```

---

## 2. Directory Structure
```
youtube-shorts-agent/
│
├── .env.example
├── requirements.txt
├── app.py                      # Main Streamlit UI Entrypoint
├── config.py                   # Global constants, paths, LLM configuration
│
├── core/
│   ├── __init__.py
│   ├── downloader.py           # yt-dlp wrapper with progress hook
│   ├── transcriber.py          # faster-whisper word-level timestamp extraction
│   ├── clip_selector.py        # LLM integration (Gemini / OpenAI structured output)
│   ├── visual_tracker.py       # MediaPipe Face Detection & smoothed trajectory
│   ├── video_processor.py      # FFmpeg filter pipelines (crop, reframe, burn-in)
│   ├── subtitle_generator.py   # Word-level .ass generation with highlight effects
│   └── youtube_uploader.py     # YouTube Data API v3 OAuth & resumable upload
│
└── storage/
    ├── downloads/              # Raw ingested full-length videos
    ├── temp/                   # Intermediate audio, segments, and ass files
    └── outputs/                # Final rendered 9:16 MP4 clips
```

---

## 3. Environment & Dependencies (`requirements.txt`)
```text
streamlit>=1.35.0
yt-dlp>=2024.4.9
faster-whisper>=1.0.2
google-genai>=0.1.1
openai>=1.30.0
mediapipe>=0.10.14
opencv-python>=4.9.0.80
numpy>=1.26.4
google-api-python-client>=2.130.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
python-dotenv>=1.0.1
pydantic>=2.7.1
```
*System dependency:* `ffmpeg` and `ffprobe` must be installed on the host system PATH.

---

## 4. Module Guidelines & Specifications

### 4.1. Configuration (`config.py`)
- Define base paths for downloads, temp files, and outputs.
- Ensure all directories are automatically created if they do not exist.
- Load environment variables for API keys and hardware settings (CPU vs. CUDA).

### 4.2. Video Ingestion (`core/downloader.py`)
- Ingest YouTube URL using `yt-dlp`.
- Download best progressive MP4 (up to 1080p) or merge best video + best audio.
- Return a dictionary: `video_id`, `title`, `duration`, `video_path`, and `thumbnail_url`.

### 4.3. Speech-to-Text (`core/transcriber.py`)
- Run `faster-whisper` model with `word_timestamps=True` and `vad_filter=True`.
- Return a list of dictionaries with word-level timestamps: `[{"word": str, "start": float, "end": float, "probability": float}, ...]`.

### 4.4. Viral Clip Extractor (`core/clip_selector.py`)
- Feed transcript chunks into an LLM (Gemini / OpenAI) with strict JSON schema enforcement via Pydantic.
- Bounds constraint: Each clip must be 25–60 seconds long.
- Each clip must have a strong 3-second hook and snap to clean sentence boundaries.

### 4.5. Dynamic Smart Framing (`core/visual_tracker.py`)
- Process clip frame-by-frame (or sub-sampled) with MediaPipe Face Detection.
- Find the active speaker's bounding box and track horizontal center ($X$).
- Apply Exponential Moving Average (EMA) smoothing ($lpha pprox 0.08$) to avoid jitter.
- Clamp coordinates so the 9:16 window never leaves source video bounds.

### 4.6. Subtitle Engine (`core/subtitle_generator.py`)
- Compile an Advanced SubStation Alpha (`.ass`) file.
- Style for vertical content: large font, heavy stroke, centered at the lower third.
- Group words into 3–4 word blocks with karaoke-style highlight timing.

### 4.7. FFmpeg Rendering Pipeline (`core/video_processor.py`)
- Run FFmpeg subprocess to trim clip, crop to 9:16 around speaker coordinate, and burn in `.ass` subtitles.
- Encode using H.264 (`libx264`) and AAC audio (`192k`).

### 4.8. YouTube Uploader (`core/youtube_uploader.py`)
- Manage OAuth 2.0 flow via `client_secrets.json` and persist credentials in a token pickle.
- Upload rendered shorts using resumable upload with `#Shorts` appended to the title and tags.

### 4.9. Orchestration UI (`app.py`)
- Streamlit dashboard tracking workflow execution (`st.status`).
- Render output videos (`st.video`) alongside metadata edit fields.
- One-click trigger for YouTube Shorts upload with live link output.

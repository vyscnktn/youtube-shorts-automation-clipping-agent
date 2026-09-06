# YouTube Shorts Automation & AI Clipping Agent

Turn a full-length YouTube video into a set of ready-to-post vertical (9:16) Shorts —
automatically. Paste a link, and the pipeline downloads the video, transcribes it,
asks an LLM to pick the most "viral" 25–60s segments, tracks the active speaker's
face to auto-crop each segment to 9:16, burns in animated word-by-word subtitles,
and hands you the finished clips to review and download from a Streamlit dashboard.

```
[YouTube URL]
     │
     ▼
[yt-dlp] ──► downloads best H.264 video (up to 1080p)
     │
     ▼
[faster-whisper] ──► word-level transcript with timestamps (GPU-accelerated)
     │
     ▼
[Gemini / OpenAI] ──► picks high-retention 25-60s windows (hook, title, virality score)
     │
     ▼
[MediaPipe] ──► tracks the active speaker's face, smoothing + hysteresis to avoid flicker
     │
     ▼
[FFmpeg] ──► pans/crops to 9:16, burns in karaoke-style ASS subtitles
     │
     ▼
[Streamlit UI] ──► review, edit title/description/tags, download the clip
```

## Features

- **Smart caching** — videos already downloaded are detected and reused; partial
  downloads resume instead of restarting from scratch. A "Downloaded videos" tab
  lets you re-run transcription/clipping on anything already fetched without
  re-downloading, so a failed run partway through the pipeline can pick up
  right where it left off.
- **Speaker-aware auto-crop** — MediaPipe face detection with a locking/hysteresis
  heuristic keeps the crop on the active speaker in multi-person shots instead of
  flickering between faces (which used to average out to a dead-center crop, e.g.
  landing on a coffee table between two speakers). The crop pans smoothly between
  keyframes rather than freezing on a single position for the whole clip.
- **GPU transcription with automatic CPU fallback** — uses `faster-whisper` on CUDA
  when available, retrying on CPU if the GPU path fails at runtime.
- **Pluggable LLM backend** — clip selection works with either Gemini or OpenAI.

## Requirements

- Python 3.11+
- `ffmpeg` (with `libx264`) on `PATH`
- (Optional, for GPU transcription) an NVIDIA GPU + driver; CUDA runtime libraries
  are installed automatically via the `nvidia-cublas-cu12` / `nvidia-cudnn-cu12`
  pip packages in `requirements.txt`
- A Gemini or OpenAI API key for clip selection

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set GEMINI_API_KEY (or OPENAI_API_KEY + LLM_PROVIDER=openai)
```

### Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai` — which backend picks clips |
| `GEMINI_API_KEY` | — | required if `LLM_PROVIDER=gemini` |
| `OPENAI_API_KEY` | — | required if `LLM_PROVIDER=openai` |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model id |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model id |
| `WHISPER_MODEL` | `medium` | faster-whisper model size |
| `WHISPER_DEVICE` | `cuda` | `cuda` or `cpu` (falls back to CPU automatically if CUDA fails) |
| `WHISPER_COMPUTE_TYPE` | `float16` | faster-whisper compute type |

### YouTube bot-check / cookies

YouTube occasionally requires sign-in verification for a given video or IP
("Sign in to confirm you're not a bot"). If you hit this, pass cookies from a
logged-in browser to yt-dlp — see `yt-dlp`'s
[cookie export docs](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
Never commit an exported `cookies.txt` — it contains live session cookies
(already excluded via `.gitignore`).

## Running

```bash
streamlit run app.py
```

Open the local URL Streamlit prints. Two tabs are available:

<img width="1864" height="964" alt="image" src="https://github.com/user-attachments/assets/2941e130-4907-4e68-8d97-4917fb9551e3" />


- **New video** — paste a YouTube URL and click "Process Video" to run the full
  pipeline (download → transcribe → select clips → render).
- **Downloaded videos** — pick a video that's already been downloaded (from a
  prior run, including one that failed partway through) and click
  "Transcribe & Process" to resume from transcription onward without
  re-downloading.

Rendered clips appear below with an editable title/description/tags and a
download button — uploading to YouTube Shorts is manual by design.

## Project structure

```
app.py                       Streamlit UI: wires the pipeline stages together
config.py                    Paths, env-driven settings, pipeline constants
core/
  downloader.py               yt-dlp wrapper: download, resume, cache, list downloaded videos
  transcriber.py               faster-whisper word-level transcription (CUDA w/ CPU fallback)
  clip_selector.py              LLM-based viral segment selection (Gemini/OpenAI)
  visual_tracker.py              MediaPipe face tracking with speaker-lock hysteresis
  video_processor.py              FFmpeg: audio extraction, 9:16 crop, subtitle burn-in
  subtitle_generator.py            Word-timed karaoke-style .ass subtitle generation
storage/
  downloads/                  cached source videos + metadata sidecars (gitignored)
  temp/                        intermediate audio/subtitle files (gitignored)
  outputs/                      final rendered clips (gitignored)
```

## Notes

- Downloaded videos, extracted audio, subtitles, and rendered clips are all
  stored under `storage/` and are gitignored — they're local pipeline state,
  not source.
- `faster-whisper`/`ctranslate2` need `libcublas`/`libcudnn` at runtime for GPU
  inference; `transcriber.py` preloads them from their pip packages by absolute
  path so a system-wide CUDA install isn't required.

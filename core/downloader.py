"""yt-dlp wrapper for ingesting full-length YouTube videos."""
import json
from pathlib import Path
from typing import Any, Callable, Optional

import yt_dlp

import config


def _info_json_path(video_id: str) -> Path:
    return config.DOWNLOADS_DIR / f"{video_id}.info.json"


def _save_sidecar(video_id: str, info: dict[str, Any]) -> None:
    sidecar = {
        "video_id": video_id,
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail_url": info.get("thumbnail"),
    }
    _info_json_path(video_id).write_text(json.dumps(sidecar))


def download_video(url: str, progress_hook: Optional[Callable[[dict], None]] = None) -> dict[str, Any]:
    """Download a YouTube video (best progressive MP4 up to 1080p, or merge best video+audio).

    Returns a dict with: video_id, title, duration, video_path, thumbnail_url.
    """
    outtmpl = str(config.DOWNLOADS_DIR / "%(id)s.%(ext)s")

    ydl_opts = {
        # Force H.264 (avc1) video: AV1/VP9 streams that yt-dlp's plain
        # "best" would otherwise pick aren't decoded reliably by the local
        # ffmpeg/OpenCV build, which silently corrupts frames fed to face
        # detection and breaks auto-crop.
        "format": (
            "best[vcodec^=avc1][ext=mp4][height<=1080]"
            "/bestvideo[vcodec^=avc1][height<=1080]+bestaudio"
            "/best[height<=1080]"
        ),
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,  # resume partially-downloaded .part files
    }
    if progress_hook is not None:
        ydl_opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Resolve the final file path without downloading first, so we can
        # skip re-downloading a video that's already complete on disk.
        info = ydl.extract_info(url, download=False)
        video_path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")

        if video_path.exists() and video_path.stat().st_size > 0:
            if progress_hook is not None:
                progress_hook({"status": "finished", "filename": str(video_path), "cached": True})
        else:
            info = ydl.extract_info(url, download=True)
            video_path = Path(ydl.prepare_filename(info))
            if not video_path.exists():
                video_path = video_path.with_suffix(".mp4")

    _save_sidecar(info.get("id"), info)

    return {
        "video_id": info.get("id"),
        "title": info.get("title"),
        "duration": info.get("duration"),
        "video_path": str(video_path),
        "thumbnail_url": info.get("thumbnail"),
    }


def list_downloaded_videos() -> list[dict[str, Any]]:
    """List videos already saved in DOWNLOADS_DIR, most recently modified first.

    Returns dicts with: video_id, title, duration, video_path, thumbnail_url.
    Reads cached metadata from the .info.json sidecar when present, falling
    back to just the video_id/path if a video was downloaded before caching
    was added.
    """
    videos = []
    for video_path in config.DOWNLOADS_DIR.glob("*.mp4"):
        if video_path.stat().st_size == 0:
            continue
        video_id = video_path.stem
        sidecar_path = _info_json_path(video_id)
        if sidecar_path.exists():
            sidecar = json.loads(sidecar_path.read_text())
        else:
            sidecar = {"video_id": video_id, "title": video_id, "duration": None, "thumbnail_url": None}
        videos.append({**sidecar, "video_path": str(video_path)})

    videos.sort(key=lambda v: Path(v["video_path"]).stat().st_mtime, reverse=True)
    return videos

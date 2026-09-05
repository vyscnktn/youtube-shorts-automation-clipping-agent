"""FFmpeg filter pipelines: trim, 9:16 reframe (face-tracked crop w/ blurred-background
fallback), and .ass subtitle burn-in."""
import subprocess
from pathlib import Path

import cv2

import config


def _probe_dimensions(video_path: str) -> tuple[int, int]:
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return width, height


def _crop_x_offset(x_center: float, src_width: int, crop_width: int) -> int:
    """Convert a normalized x_center into a pixel offset, clamped to source bounds."""
    raw_offset = int(x_center * src_width - crop_width / 2)
    return max(0, min(raw_offset, src_width - crop_width))


def _crop_x_expression(
    trajectory: list[dict], clip_start_time: float, src_width: int, crop_width: int
) -> str:
    """Build an ffmpeg crop `x` expression that pans between trajectory keyframes.

    Keyframe times are relative to clip start (matching the filter's `t`
    after -ss trimming). Between keyframes, x is linearly interpolated so the
    crop pans smoothly to follow the locked speaker instead of sitting on one
    clip-wide average position.
    """
    points = [
        (p["time"] - clip_start_time, _crop_x_offset(p["x_center"], src_width, crop_width))
        for p in trajectory
    ]

    expr = str(points[-1][1])
    for (t0, x0), (t1, x1) in zip(points[:-1], points[1:]):
        if t1 == t0:
            continue
        lerp = f"({x0}+({x1}-{x0})*(t-{t0})/({t1}-{t0}))"
        expr = f"if(lt(t,{t1}),{lerp},{expr})"
    return expr


def render_clip(
    source_video_path: str,
    start_time: float,
    end_time: float,
    crop_trajectory: list[dict],
    ass_path: str,
    output_path: str,
) -> str:
    """Trim, crop to 9:16 around the tracked speaker x-coordinate, and burn in subtitles.

    If the source video can't provide a full-height 9:16 crop from cropping alone
    (i.e. it's already narrower than 9:16 of its height), falls back to a blurred,
    scaled full-frame background with the sharp video centered on top.
    """
    src_width, src_height = _probe_dimensions(source_video_path)
    duration = end_time - start_time

    target_crop_width = int(src_height * config.OUTPUT_ASPECT_RATIO)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if target_crop_width <= src_width:
        # Standard path: crop a 9:16 vertical slice, panning to follow the speaker.
        x_expr = _crop_x_expression(crop_trajectory, start_time, src_width, target_crop_width)
        vf = (
            f"crop={target_crop_width}:{src_height}:'{x_expr}':0,"
            f"scale=1080:1920,"
            f"ass={ass_path}"
        )
    else:
        # Fallback: blurred, scaled background with the full frame centered on top.
        vf = (
            f"split=2[bg][fg];"
            f"[bg]scale=1080:1920,boxblur=20:5,crop=1080:1920[bgblur];"
            f"[fg]scale=1080:-1[fgscaled];"
            f"[bgblur][fgscaled]overlay=(W-w)/2:(H-h)/2,"
            f"ass={ass_path}"
        )

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        source_video_path,
        "-t",
        str(duration),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def extract_audio(video_path: str, output_path: str) -> str:
    """Extract audio track from a video file (for transcription)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path

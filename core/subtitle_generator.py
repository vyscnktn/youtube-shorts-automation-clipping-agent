"""Word-level Advanced SubStation Alpha (.ass) generation with karaoke highlight effects."""
from pathlib import Path

import config

ASS_HEADER = """[Script Info]
Title: Auto-generated Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font},{size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{outline},2,2,60,60,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    centis = int(round((secs - int(secs)) * 100))
    return f"{hours:d}:{minutes:02d}:{int(secs):02d}.{centis:02d}"


def _group_words(words: list[dict], group_size: int) -> list[list[dict]]:
    groups = []
    for i in range(0, len(words), group_size):
        groups.append(words[i : i + group_size])
    return groups


def _karaoke_line(group: list[dict]) -> str:
    """Build a karaoke-tagged ASS text line where each word highlights in sequence."""
    parts = []
    for word in group:
        duration_centis = max(1, int(round((word["end"] - word["start"]) * 100)))
        parts.append(f"{{\\kf{duration_centis}}}{word['word']} ")
    return "".join(parts).strip()


def generate_ass(
    words: list[dict],
    output_path: str,
    group_size: int = config.SUBTITLE_WORDS_PER_GROUP,
) -> str:
    """Compile a .ass subtitle file from word-level timestamps (relative to clip start)."""
    header = ASS_HEADER.format(
        font=config.SUBTITLE_FONT,
        size=config.SUBTITLE_FONT_SIZE,
        outline=6,
    )

    events = []
    for group in _group_words(words, group_size):
        if not group:
            continue
        start = _format_time(group[0]["start"])
        end = _format_time(group[-1]["end"])
        text = _karaoke_line(group)
        events.append(f"Dialogue: 0,{start},{end},Karaoke,,0,0,0,,{text}")

    Path(output_path).write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return output_path

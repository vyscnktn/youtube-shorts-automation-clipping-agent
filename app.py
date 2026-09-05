"""Streamlit dashboard: ingest -> transcribe -> select clips -> render for manual upload."""
from pathlib import Path

import streamlit as st

import config
from core import (
    clip_selector,
    downloader,
    subtitle_generator,
    video_processor,
    visual_tracker,
)

st.set_page_config(page_title="YouTube Shorts Agent", layout="wide")
st.title("YouTube Shorts Automation & AI Clipping Agent")

if "rendered_clips" not in st.session_state:
    st.session_state.rendered_clips = []


def run_pipeline(video_info: dict) -> None:
    st.session_state.rendered_clips = []

    with st.status("Running pipeline...", expanded=True) as status:
        status.write("Extracting audio...")
        audio_path = str(config.TEMP_DIR / f"{video_info['video_id']}.wav")
        video_processor.extract_audio(video_info["video_path"], audio_path)

        status.write("Transcribing (faster-whisper, word-level timestamps)...")
        from core import transcriber

        words = transcriber.transcribe(audio_path)
        status.write(f"Transcribed {len(words)} words.")

        status.write("Selecting viral highlight windows (LLM)...")
        clips = clip_selector.select_clips(words)
        status.write(f"Found {len(clips)} candidate clip(s).")

        for i, clip in enumerate(clips):
            status.write(f"Rendering clip {i + 1}/{len(clips)}: {clip.title}")

            clip_words = [
                {
                    "word": w["word"],
                    "start": w["start"] - clip.start,
                    "end": w["end"] - clip.start,
                }
                for w in words
                if clip.start <= w["start"] < clip.end
            ]

            ass_path = str(config.TEMP_DIR / f"{video_info['video_id']}_clip{i}.ass")
            subtitle_generator.generate_ass(clip_words, ass_path)

            trajectory = visual_tracker.compute_crop_trajectory(
                video_info["video_path"], clip.start, clip.end
            )
            trajectory = visual_tracker.resample_trajectory(trajectory)

            output_path = str(config.OUTPUTS_DIR / f"{video_info['video_id']}_clip{i}.mp4")
            video_processor.render_clip(
                video_info["video_path"],
                clip.start,
                clip.end,
                trajectory,
                ass_path,
                output_path,
            )

            st.session_state.rendered_clips.append(
                {
                    "path": output_path,
                    "title": clip.title,
                    "hook": clip.hook,
                    "virality_score": clip.virality_score,
                }
            )

        status.update(label="Pipeline complete.", state="complete")


tab_new, tab_downloaded = st.tabs(["New video", "Downloaded videos"])

with tab_new:
    url = st.text_input("YouTube video URL")
    if st.button("Process Video", type="primary", disabled=not url):
        with st.status("Downloading source video (yt-dlp)...", expanded=True) as dl_status:
            video_info = downloader.download_video(url)
            dl_status.update(
                label=f"Downloaded: {video_info['title']} ({video_info['duration']}s)",
                state="complete",
            )
        run_pipeline(video_info)

with tab_downloaded:
    downloaded = downloader.list_downloaded_videos()
    if not downloaded:
        st.caption("No videos downloaded yet.")
    else:
        options = {
            f"{v['title']} ({v['video_id']})": v for v in downloaded
        }
        choice = st.selectbox("Pick a previously downloaded video", options.keys())
        if st.button("Transcribe & Process", type="primary", key="process_downloaded"):
            run_pipeline(options[choice])

for i, clip in enumerate(st.session_state.rendered_clips):
    st.divider()
    cols = st.columns([1, 1])
    with cols[0]:
        if Path(clip["path"]).exists():
            st.video(clip["path"])
    with cols[1]:
        st.text_input("Title", value=clip["title"], key=f"title_{i}")
        st.text_area("Description", value=clip["hook"], key=f"desc_{i}")
        st.text_input("Tags (comma-separated)", value="", key=f"tags_{i}")
        st.metric("Virality Score", clip["virality_score"])
        st.caption(f"Rendered file: `{clip['path']}` — download and upload to YouTube Shorts manually.")
        with open(clip["path"], "rb") as f:
            st.download_button(
                "Download clip",
                data=f.read(),
                file_name=Path(clip["path"]).name,
                mime="video/mp4",
                key=f"download_{i}",
            )

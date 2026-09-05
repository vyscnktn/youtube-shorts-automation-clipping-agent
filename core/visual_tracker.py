"""MediaPipe Face Detection + smoothed horizontal-center trajectory for auto-crop."""
import cv2
import mediapipe as mp

import config

mp_face_detection = mp.solutions.face_detection

# How much bigger a new face's bounding box must be than the currently locked
# speaker's before we consider switching to it. Interview-style shots have
# two similarly-sized faces, and "largest face this frame" flickers between
# them almost every sample without this — collapsing the trajectory's average
# toward the dead center of the frame (i.e. the table between the speakers).
_SWITCH_AREA_RATIO = 1.3
# Number of consecutive samples the new face must stay dominant before we
# actually switch, so a single noisy frame can't trigger a swap.
_SWITCH_CONFIRM_SAMPLES = 3


def compute_crop_trajectory(
    video_path: str,
    start_time: float,
    end_time: float,
    sample_rate: int = 5,
) -> list[dict]:
    """Track the active speaker's horizontal center across a clip window.

    Returns a list of {"time": float, "x_center": float} (x_center normalized 0-1),
    smoothed with an EMA (alpha = config.FACE_TRACK_EMA_ALPHA) and clamped to [0, 1].
    Falls back to center-frame (x_center=0.5) whenever no face is detected.

    Uses hysteresis to stay locked onto one speaker rather than jumping to
    whichever face is largest in a single frame, which flickers badly in
    multi-person shots.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    trajectory: list[dict] = []
    smoothed_x = 0.5
    alpha = config.FACE_TRACK_EMA_ALPHA

    locked_x = None
    locked_area = None
    pending_x = None
    pending_area = None
    pending_streak = 0

    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
        frame_idx = start_frame
        while frame_idx <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if (frame_idx - start_frame) % sample_rate == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = detector.process(rgb_frame)

                raw_x = locked_x if locked_x is not None else 0.5
                if results.detections:
                    largest = max(
                        results.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width
                        * d.location_data.relative_bounding_box.height,
                    )
                    bbox = largest.location_data.relative_bounding_box
                    candidate_x = bbox.xmin + bbox.width / 2
                    candidate_area = bbox.width * bbox.height

                    if locked_x is None:
                        locked_x, locked_area = candidate_x, candidate_area
                    elif candidate_area > locked_area * _SWITCH_AREA_RATIO:
                        # Candidate is meaningfully bigger than the locked
                        # speaker — only switch once it's persisted a bit.
                        if pending_x is not None and abs(candidate_x - pending_x) < 0.1:
                            pending_streak += 1
                        else:
                            pending_x, pending_area, pending_streak = candidate_x, candidate_area, 1

                        if pending_streak >= _SWITCH_CONFIRM_SAMPLES:
                            locked_x, locked_area = pending_x, pending_area
                            pending_x = pending_area = None
                            pending_streak = 0
                    else:
                        # Locked speaker is still dominant; drift the lock
                        # gently to track their own movement and reset any
                        # pending switch.
                        locked_x = candidate_x if abs(candidate_x - locked_x) < 0.3 else locked_x
                        locked_area = candidate_area
                        pending_x = pending_area = None
                        pending_streak = 0

                    raw_x = locked_x

                smoothed_x = alpha * raw_x + (1 - alpha) * smoothed_x
                smoothed_x = max(0.0, min(1.0, smoothed_x))

                trajectory.append(
                    {"time": frame_idx / fps, "x_center": smoothed_x}
                )

            frame_idx += 1

    cap.release()

    if not trajectory:
        trajectory = [{"time": start_time, "x_center": 0.5}, {"time": end_time, "x_center": 0.5}]

    return trajectory


def get_average_crop_x(trajectory: list[dict]) -> float:
    """Collapse a trajectory into a single representative x_center (mean)."""
    if not trajectory:
        return 0.5
    return sum(p["x_center"] for p in trajectory) / len(trajectory)


def resample_trajectory(trajectory: list[dict], step: float = 0.5) -> list[dict]:
    """Downsample a trajectory to one point per `step` seconds.

    Keeps the crop-position expression built from this trajectory small
    enough for ffmpeg to parse, while still panning to follow the locked
    speaker over the course of a clip instead of freezing on one average.
    """
    if not trajectory:
        return trajectory

    resampled = [trajectory[0]]
    next_time = trajectory[0]["time"] + step
    for point in trajectory[1:]:
        if point["time"] >= next_time:
            resampled.append(point)
            next_time = point["time"] + step
    if resampled[-1]["time"] != trajectory[-1]["time"]:
        resampled.append(trajectory[-1])
    return resampled

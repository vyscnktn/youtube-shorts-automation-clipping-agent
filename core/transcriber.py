"""faster-whisper word-level timestamp extraction."""
import ctypes
import glob
import os


def _preload_cuda_libs() -> None:
    """Preload cuBLAS/cuDNN from their pip packages.

    ctranslate2 dlopen()s these by soname at runtime, but setting
    LD_LIBRARY_PATH from within the process has no effect (glibc reads it
    once at process start). Loading them here by absolute path first makes
    the later dlopen-by-soname resolve to the already-loaded library.
    """
    import site

    site_dirs = site.getsitepackages() + [site.getusersitepackages()]
    for pattern in ("nvidia/cublas/lib/libcublas.so.*", "nvidia/cudnn/lib/libcudnn.so.*"):
        for site_dir in site_dirs:
            for lib_path in glob.glob(os.path.join(site_dir, pattern)):
                try:
                    ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


_preload_cuda_libs()

from faster_whisper import WhisperModel

import config

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        try:
            _model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
        except Exception:
            # Fall back to CPU if CUDA/requested device is unavailable.
            _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Transcribe audio with word-level timestamps.

    Returns: [{"word": str, "start": float, "end": float, "probability": float}, ...]
    """
    global _model
    model = _get_model()
    try:
        segments, _info = model.transcribe(
            audio_path,
            word_timestamps=True,
            vad_filter=True,
        )
        segments = list(segments)
    except Exception:
        # Runtime CUDA failure (e.g. missing cuBLAS) surfaces here, not at
        # construction time, so retry once on CPU before giving up.
        _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, _info = _model.transcribe(
            audio_path,
            word_timestamps=True,
            vad_filter=True,
        )

    words: list[dict] = []
    for segment in segments:
        if not segment.words:
            continue
        for word in segment.words:
            words.append(
                {
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability,
                }
            )
    return words

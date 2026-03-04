"""Kokoro TTS wrapper for local speech synthesis.

Usage:
    from backend.services.tts_engine import TTSEngine

    engine = TTSEngine()
    engine.synthesize("Hello world", "output.wav")
    paths = engine.synthesize_segments(segments, "audio_dir/")

Requires ``kokoro``, ``soundfile``, and the ``espeak-ng`` system package.
"""

from __future__ import annotations

import logging
import os
import tempfile

from backend.config import settings

logger = logging.getLogger(__name__)

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(**kwargs):
        def decorator(func):
            return func
        return decorator

SAMPLE_RATE = 24_000  # Kokoro outputs 24 kHz audio


class TTSEngine:
    """Wraps Kokoro TTS for script-to-audio conversion.

    The KPipeline is initialized lazily on first use to avoid loading the
    model (~250 MB) when TTS is not needed.

    Args:
        voice: Kokoro voice name (default from config: ``af_heart``).
        lang: Kokoro language code (default from config: ``a`` for American English).
    """

    def __init__(self, voice: str | None = None, lang: str | None = None):
        self._voice = voice or settings.kokoro_voice
        self._lang = lang or settings.kokoro_lang
        self._pipeline = None  # lazy init

    def _get_pipeline(self):
        """Return the Kokoro KPipeline, creating it on first call."""
        if self._pipeline is None:
            from backend.services.gpu_utils import get_torch_device

            device = get_torch_device(settings.video_device)
            logger.info(
                "Loading Kokoro TTS model (voice=%s, lang=%s, device=%s)...",
                self._voice, self._lang, device,
            )
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code=self._lang, device=device)
            logger.info("Kokoro TTS model loaded successfully on %s", device)
        return self._pipeline

    @traceable(run_type="tool", name="tts_synthesize")
    def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize *text* to a WAV file at *output_path*.

        Args:
            text: The text to convert to speech.
            output_path: Filesystem path for the output WAV file.

        Returns:
            The *output_path* for convenience.

        Raises:
            ValueError: If *output_path* escapes the working directory or /tmp.
        """
        import numpy as np
        import soundfile as sf

        _validate_path(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        pipeline = self._get_pipeline()
        samples = []
        logger.debug("Synthesizing %d chars to %s", len(text), output_path)
        for chunk in pipeline(text, voice=self._voice):
            samples.append(chunk.audio)

        if not samples:
            raise RuntimeError(f"Kokoro produced no audio for text ({len(text)} chars)")

        audio = np.concatenate(samples)
        sf.write(output_path, audio, SAMPLE_RATE)
        logger.debug("Audio written: %s (%.1fs)", output_path, len(audio) / SAMPLE_RATE)
        return output_path

    def synthesize_segments(self, segments: list[dict], output_dir: str) -> list[str]:
        """Synthesize multiple script segments to WAV files.

        Args:
            segments: List of dicts from :func:`script_parser.parse_script`,
                each with ``slide_num`` and ``text``.
            output_dir: Directory to write WAV files into.

        Returns:
            Ordered list of WAV file paths, one per segment.
        """
        _validate_path(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        paths: list[str] = []
        for seg in segments:
            filename = f"slide_{seg['slide_num']:03d}.wav"
            out_path = os.path.join(output_dir, filename)
            self.synthesize(seg["text"], out_path)
            paths.append(out_path)
            logger.debug("TTS segment %d synthesized → %s", seg["slide_num"], filename)
            print(f"[Video]   TTS segment slide {seg['slide_num']} → {filename}")
        return paths


def _validate_path(path: str) -> None:
    """Reject paths that escape the working directory or /tmp."""
    resolved = os.path.realpath(path)
    cwd = os.path.realpath(os.getcwd())
    tmp = os.path.realpath(tempfile.gettempdir())
    if not (
        resolved.startswith(cwd + os.sep)
        or resolved.startswith(tmp + os.sep)
        or resolved == cwd
        or resolved == tmp
    ):
        raise ValueError(f"Path traversal detected: {path}")

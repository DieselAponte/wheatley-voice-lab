"""Acoustic inspection and technical audio validation module using SoundFile and NumPy/Librosa."""

import logging
import math
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class AudioTechnicalProfile(BaseModel):
    """Deterministic acoustic measurements and technical validity profile."""

    model_config = ConfigDict(extra="ignore")

    duration_seconds: float = 0.0
    sample_rate_hz: int = 0
    channels: int = 0
    subtype: str = "UNKNOWN"
    peak_amplitude: float = 0.0
    peak_dbfs: float = -100.0
    rms_amplitude: float = 0.0
    rms_dbfs: float = -100.0
    silence_duration_seconds: float = 0.0
    silence_ratio: float = 0.0
    has_clipping: bool = False
    is_valid: bool = False
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class AudioInspector:
    """Performs deterministic technical inspection and acoustic metric extraction."""

    # Threshold for clipping detection (0.999 is ~ -0.01 dBFS)
    CLIPPING_THRESHOLD_LINEAR = 0.999
    # Silence threshold: values below -50 dBFS are considered silence
    SILENCE_THRESHOLD_LINEAR = 10 ** (-50 / 20)

    @classmethod
    def inspect_file(cls, audio_path: Path | str) -> AudioTechnicalProfile:
        """Inspect an audio file and return an objective acoustic profile."""
        path = Path(audio_path)
        if not path.exists():
            return AudioTechnicalProfile(
                is_valid=False,
                error_message=f"File not found: {path}",
            )

        if path.stat().st_size == 0:
            return AudioTechnicalProfile(
                is_valid=False,
                error_message="Audio file is 0 bytes (empty).",
            )

        try:
            # Read metadata and samples using soundfile
            info = sf.info(str(path))
            data, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
        except Exception as e:
            logger.warning(f"Failed to decode audio file {path}: {e}")
            return AudioTechnicalProfile(
                is_valid=False,
                error_message=f"Audio decoding failure: {e}",
            )

        num_frames, num_channels = data.shape
        duration = float(info.duration)
        subtype = str(info.subtype)

        if num_frames == 0 or duration == 0:
            return AudioTechnicalProfile(
                duration_seconds=0.0,
                sample_rate_hz=sample_rate,
                channels=num_channels,
                subtype=subtype,
                is_valid=False,
                error_message="File contains 0 audio frames.",
            )

        # Flatten or average across channels for signal measurements
        mono_signal = np.mean(data, axis=1)
        abs_signal = np.abs(mono_signal)

        # 1. Peak Amplitude and dBFS
        peak_amp = float(np.max(abs_signal))
        peak_dbfs = 20.0 * math.log10(peak_amp) if peak_amp > 1e-9 else -100.0

        # 2. RMS Amplitude and dBFS
        rms_amp = float(np.sqrt(np.mean(mono_signal**2)))
        rms_dbfs = 20.0 * math.log10(rms_amp) if rms_amp > 1e-9 else -100.0

        # 3. Clipping detection
        has_clipping = bool(peak_amp >= cls.CLIPPING_THRESHOLD_LINEAR)

        # 4. Silence analysis
        silence_mask = abs_signal < cls.SILENCE_THRESHOLD_LINEAR
        silence_frames = int(np.sum(silence_mask))
        silence_ratio = float(silence_frames / num_frames)
        silence_duration = float(silence_ratio * duration)

        warnings: list[str] = []
        if has_clipping:
            warnings.append(f"Audio exhibits digital clipping (peak: {peak_dbfs:.2f} dBFS).")
        if silence_ratio > 0.6:
            warnings.append(f"High silence proportion ({silence_ratio * 100:.1f}%).")
        if rms_dbfs < -40.0:
            warnings.append(f"Very quiet audio (RMS: {rms_dbfs:.2f} dBFS).")

        return AudioTechnicalProfile(
            duration_seconds=round(duration, 4),
            sample_rate_hz=sample_rate,
            channels=num_channels,
            subtype=subtype,
            peak_amplitude=round(peak_amp, 4),
            peak_dbfs=round(peak_dbfs, 2),
            rms_amplitude=round(rms_amp, 4),
            rms_dbfs=round(rms_dbfs, 2),
            silence_duration_seconds=round(silence_duration, 4),
            silence_ratio=round(silence_ratio, 4),
            has_clipping=has_clipping,
            is_valid=True,
            warnings=warnings,
        )

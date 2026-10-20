"""Audio derivative processing: resampling, format normalization, and derived file management."""

import logging
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict

from src.voice_lab.infrastructure.audio.validation import AudioInspector, AudioTechnicalProfile

logger = logging.getLogger(__name__)


class DerivativeMetadata(BaseModel):
    """Metadata tracking the creation of a derived audio asset."""

    model_config = ConfigDict(extra="ignore")

    derivative_id: str
    original_file_path: str
    derived_file_path: str
    transformation: str
    target_sample_rate: int
    target_channels: int
    original_profile: AudioTechnicalProfile
    derived_profile: AudioTechnicalProfile


class AudioProcessor:
    """Creates identifiable audio derivatives without modifying original source assets."""

    @classmethod
    def create_derivative(
        self,
        input_path: Path | str,
        output_dir: Path | str,
        target_sample_rate: int = 24000,
        mono: bool = True,
        normalize_peak: Optional[float] = None,
    ) -> tuple[Path, DerivativeMetadata]:
        """Convert audio to a target derivative (e.g. 24kHz mono PCM) in a dedicated derivative path."""
        in_path = Path(input_path)
        out_directory = Path(output_dir)
        out_directory.mkdir(parents=True, exist_ok=True)

        if not in_path.exists():
            raise FileNotFoundError(f"Input audio does not exist: {in_path}")

        # Original profile
        orig_profile = AudioInspector.inspect_file(in_path)
        if not orig_profile.is_valid:
            raise ValueError(f"Cannot process invalid audio file: {orig_profile.error_message}")

        # Read samples
        data, sr = sf.read(str(in_path), dtype="float32", always_2d=True)

        # Convert to mono if requested
        if mono and data.shape[1] > 1:
            data = np.mean(data, axis=1, keepdims=True)

        # Resample if needed
        channels = 1 if mono else data.shape[1]
        if sr != target_sample_rate:
            # Resample using librosa if sample rate changes
            import librosa
            resampled_channels = []
            for c in range(data.shape[1]):
                resampled = librosa.resample(
                    data[:, c],
                    orig_sr=sr,
                    target_sr=target_sample_rate,
                    res_type="soxr_hq",
                )
                resampled_channels.append(resampled)
            data = np.column_stack(resampled_channels)
            sr = target_sample_rate

        # Normalize peak if requested
        if normalize_peak is not None:
            current_peak = np.max(np.abs(data))
            if current_peak > 1e-6:
                scale = normalize_peak / current_peak
                data = data * scale

        # Prepare derivative output path
        stem = in_path.stem
        target_channels = 1 if mono else data.shape[1]
        out_filename = f"{stem}_deriv_{target_sample_rate}hz_{target_channels}ch.wav"
        out_path = out_directory / out_filename

        # Write derivative file
        sf.write(str(out_path), data, target_sample_rate, subtype="PCM_16")
        derived_profile = AudioInspector.inspect_file(out_path)

        metadata = DerivativeMetadata(
            derivative_id=f"deriv_{stem}_{target_sample_rate}",
            original_file_path=str(in_path),
            derived_file_path=str(out_path),
            transformation=f"resample_{target_sample_rate}hz_mono_{mono}",
            target_sample_rate=target_sample_rate,
            target_channels=target_channels,
            original_profile=orig_profile,
            derived_profile=derived_profile,
        )

        logger.info(f"Created derivative {out_path} from {in_path}")
        return out_path, metadata

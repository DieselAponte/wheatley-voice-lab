"""Chatterbox synthesis adapter for Spanish (es-ES) speech generation with device management."""

import logging
import math
from pathlib import Path
from typing import Any, Optional
import numpy as np
import soundfile as sf

from src.voice_lab.domain.contracts import SpeechGenerator
from src.voice_lab.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class ChatterboxAdapter(SpeechGenerator):
    """Adapter for Chatterbox text-to-speech model supporting Spanish (es-ES) and voice prompt cloning."""

    def __init__(
        self,
        device: Optional[str] = None,
        model_name: str = "ResembleAI/Chatterbox-Multilingual-es-es",
        sample_rate: int = 24000,
    ):
        self.requested_device = device
        self.model_name = model_name
        self.sample_rate = sample_rate
        self.device = self._resolve_device(device)
        self._model: Any = None
        self._is_chatterbox_available = self._check_chatterbox_available()

    def _check_chatterbox_available(self) -> bool:
        """Check if torch and chatterbox are installed in the active environment."""
        try:
            import torch  # noqa: F401
            import chatterbox  # noqa: F401
            return True
        except ImportError:
            return False

    def _resolve_device(self, requested: Optional[str]) -> str:
        """Resolve optimal device considering GTX 1650 4GB VRAM limitations."""
        if requested in ("cuda", "cpu"):
            return requested

        try:
            import torch
            if torch.cuda.is_available():
                # Check free VRAM on device 0
                props = torch.cuda.get_device_properties(0)
                total_mem = props.total_memory / (1024**3)
                # If VRAM is 4GB or less, default to CPU to prevent CUDA OOM
                if total_mem < 5.0:
                    logger.warning(
                        f"Detected GPU with {total_mem:.1f}GB VRAM (GTX 1650 / 4GB). "
                        f"Defaulting Chatterbox to CPU inference for stability."
                    )
                    return "cpu"
                return "cuda"
        except Exception:
            pass

        return "cpu"

    def load_model(self) -> None:
        """Load model weights into memory if chatterbox is installed."""
        if self._model is not None:
            return

        if not self._is_chatterbox_available:
            logger.info("Chatterbox/Torch not installed in .venv. Operating in simulated synthesis mode.")
            return

        try:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            logger.info(f"Loading Chatterbox model ({self.model_name}) on device={self.device}...")
            self._model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            logger.info("Chatterbox model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Chatterbox model: {e}")
            raise RuntimeError(f"Chatterbox initialization error: {e}") from e

    def generate(
        self,
        text: str,
        profile_params: dict[str, float],
        reference_audio_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Synthesize expressive speech audio in Spanish."""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Input text for speech generation cannot be empty.")

        out_path = output_path or (settings.generated_dir / f"gen_{hash(clean_text) & 0xffffffff}.wav")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        speed = float(profile_params.get("speed", 1.0))
        exaggeration = float(profile_params.get("exaggeration", 0.5))
        cfg_weight = float(profile_params.get("cfg_weight", 0.5))

        if self._is_chatterbox_available and self._model is not None:
            # Real model execution
            ref_path_str = str(reference_audio_path) if reference_audio_path and reference_audio_path.exists() else None
            try:
                wav = self._model.generate(
                    clean_text,
                    language_id="es",
                    audio_prompt_path=ref_path_str,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                )
                import torchaudio as ta
                ta.save(str(out_path), wav, self.sample_rate)
                logger.info(f"Generated Chatterbox audio saved to {out_path}")
                return out_path
            except Exception as e:
                logger.error(f"Chatterbox inference failed: {e}")
                raise RuntimeError(f"Inference failure: {e}") from e

        # Fallback simulated synthesis: generates deterministic, parameter-modulated audio waveform
        # Distinctively marked as simulated audio
        logger.info(f"[SIMULATION] Synthesizing acoustic audio for '{clean_text[:30]}...' with speed={speed:.2f}, exag={exaggeration:.2f}")
        duration = max(0.8, (len(clean_text) * 0.06) / speed)
        sr = self.sample_rate
        total_samples = int(duration * sr)
        t = np.linspace(0, duration, total_samples, endpoint=False)

        # Base fundamental frequency around 220 Hz with expressive modulation
        f0 = 220.0 + (exaggeration * 60.0 * np.sin(2 * np.pi * 3.0 * t))
        audio_signal = 0.3 * np.sin(2 * np.pi * f0 * t)

        # Add robotic formant harmonic
        audio_signal += 0.15 * np.sin(2 * np.pi * f0 * 2.0 * t)
        # Apply smooth fade in / fade out to avoid clicks
        fade_len = int(0.02 * sr)
        if total_samples > 2 * fade_len:
            audio_signal[:fade_len] *= np.linspace(0, 1, fade_len)
            audio_signal[-fade_len:] *= np.linspace(1, 0, fade_len)

        sf.write(str(out_path), audio_signal.astype(np.float32), sr, subtype="PCM_16")
        return out_path

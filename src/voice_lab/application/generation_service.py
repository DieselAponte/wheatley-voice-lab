"""Generation application service orchestrating expressive speech synthesis and persistence."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import GenerationRepository, SpeechGenerator
from src.voice_lab.domain.generation_models import GenerationRecord
from src.voice_lab.domain.profiles import ProfileManager
from src.voice_lab.infrastructure.audio.storage import LocalAudioStorage
from src.voice_lab.infrastructure.audio.validation import AudioInspector
from src.voice_lab.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Raised when speech synthesis fails."""


class GenerationService:
    """Orchestrates text synthesis, profile resolution, acoustic inspection, and record persistence."""

    def __init__(
        self,
        generator: SpeechGenerator,
        repository: GenerationRepository,
        profile_manager: Optional[ProfileManager] = None,
        output_dir: Optional[Path] = None,
    ):
        self.generator = generator
        self.repository = repository
        self.profile_manager = profile_manager or ProfileManager()
        self.output_dir = output_dir or settings.generated_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_phrase(
        self,
        text: str,
        profile_id: str = "conversacional",
        custom_params: Optional[dict[str, float]] = None,
        reference_audio_path: Optional[Path] = None,
        reference_audio_id: Optional[str] = None,
    ) -> GenerationRecord:
        """Synthesize a single phrase under a specified profile with custom parameters."""
        clean_text = text.strip()
        if len(clean_text) < 2:
            raise ValueError("Input text must contain at least 2 non-whitespace characters.")

        profile = self.profile_manager.resolve_profile(profile_id)
        final_params = profile.validate_custom_parameters(custom_params or {})

        generation_id = f"gen_{uuid.uuid4().hex[:10]}"
        wav_path = self.output_dir / f"{generation_id}.wav"

        device_used = getattr(self.generator, "device", "cpu")
        model_name = getattr(self.generator, "model_name", "ResembleAI/Chatterbox-Multilingual-es-es")

        try:
            logger.info(f"Synthesizing [{generation_id}] under profile '{profile.name}' for text: '{clean_text[:40]}...'")
            result_wav = self.generator.generate(
                text=clean_text,
                profile_params=final_params,
                reference_audio_path=reference_audio_path,
                output_path=wav_path,
            )

            # Technical inspection of the generated audio
            profile_tech = AudioInspector.inspect_file(result_wav)
            sha256 = LocalAudioStorage.calculate_sha256(result_wav)
            file_size = LocalAudioStorage.get_file_size(result_wav)

            record = GenerationRecord(
                generation_id=generation_id,
                text=clean_text,
                profile_id=profile.id,
                profile_name=profile.name,
                parameters=final_params,
                reference_audio_id=reference_audio_id,
                reference_audio_path=str(reference_audio_path) if reference_audio_path else None,
                audio_path=str(result_wav),
                audio_sha256=sha256,
                duration_seconds=profile_tech.duration_seconds,
                file_size_bytes=file_size,
                sample_rate_hz=profile_tech.sample_rate_hz,
                model_name=model_name,
                generator_device=device_used,
                status="SUCCESS",
            )
            self.repository.save_generation(record)
            return record

        except Exception as exc:
            logger.error(f"Generation failure for [{generation_id}]: {exc}")
            failed_record = GenerationRecord(
                generation_id=generation_id,
                text=clean_text,
                profile_id=profile.id,
                profile_name=profile.name,
                parameters=final_params,
                audio_path="",
                status="FAILED",
                error_message=str(exc),
            )
            self.repository.save_generation(failed_record)
            raise GenerationError(f"Speech synthesis error: {exc}") from exc

    def generate_batch(
        self,
        texts: list[str],
        profile_ids: list[str],
        reference_audio_path: Optional[Path] = None,
        reference_audio_id: Optional[str] = None,
    ) -> list[GenerationRecord]:
        """Synthesize multiple phrases across one or more expressive profiles."""
        results: list[GenerationRecord] = []
        for text in texts:
            for pid in profile_ids:
                try:
                    rec = self.generate_phrase(
                        text=text,
                        profile_id=pid,
                        reference_audio_path=reference_audio_path,
                        reference_audio_id=reference_audio_id,
                    )
                    results.append(rec)
                except Exception as exc:
                    logger.warning(f"Batch generation item failed for '{text[:20]}' ({pid}): {exc}")
        return results

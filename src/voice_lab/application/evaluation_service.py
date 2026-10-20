"""Evaluation application service with caching, persistence, and privacy controls."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import AudioEvaluator
from src.voice_lab.domain.evaluation_models import AudioEvaluation
from src.voice_lab.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class PrivacyPolicyViolationError(Exception):
    """Raised when an operation attempts to transmit reference audio without explicit user consent."""


class EvaluationService:
    """Orchestrates structured audio evaluation with caching, provenance, and privacy enforcement."""

    def __init__(
        self,
        evaluator: AudioEvaluator,
        evaluations_dir: Optional[Path] = None,
        allow_reference_upload: Optional[bool] = None,
    ):
        self.evaluator = evaluator
        self.evaluations_dir = evaluations_dir or settings.evaluation_dir
        self.evaluations_dir.mkdir(parents=True, exist_ok=True)
        self.allow_reference_upload = (
            allow_reference_upload
            if allow_reference_upload is not None
            else settings.allow_reference_external_eval
        )
        self._index_file = self.evaluations_dir / "evaluation_index.json"
        self._cache: dict[str, str] = self._load_index()

    def _load_index(self) -> dict[str, str]:
        """Load cache mapping of cache_key -> evaluation_id."""
        if not self._index_file.exists():
            return {}
        try:
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(f"Could not load evaluation index: {e}")
            return {}

    def _save_index(self) -> None:
        """Persist cache mapping to index file."""
        try:
            temp_path = self._index_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            temp_path.replace(self._index_file)
        except Exception as e:
            logger.warning(f"Failed to persist evaluation index: {e}")

    def _make_cache_key(self, audio_sha256: str, model_name: str, prompt_version: str) -> str:
        """Generate deterministic cache key based on audio content and prompt version."""
        raw = f"{audio_sha256}:{model_name}:{prompt_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_evaluation(self, evaluation_id: str) -> Optional[AudioEvaluation]:
        """Retrieve a persisted evaluation by its ID."""
        file_path = self.evaluations_dir / f"{evaluation_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AudioEvaluation.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to read evaluation from {file_path}: {e}")
            return None

    def evaluate_audio(
        self,
        audio_path: Path,
        audio_id: str,
        audio_sha256: str,
        is_reference: bool = False,
        expected_transcript: Optional[str] = None,
        force_reevaluate: bool = False,
    ) -> AudioEvaluation:
        """Evaluate an audio clip, enforcing privacy, checking cache, and persisting results."""
        # Privacy policy check: do not transmit reference audios unless explicitly authorized
        if is_reference and not self.allow_reference_upload:
            if getattr(self.evaluator, "model_name", "").startswith("mock"):
                # Mock evaluators do not transmit network data
                pass
            else:
                raise PrivacyPolicyViolationError(
                    f"Blocked external API evaluation of reference audio '{audio_id}'. "
                    f"Transmitting proprietary reference audios to an external AI provider requires "
                    f"explicit user consent. Enable ALLOW_REFERENCE_EXTERNAL_EVAL in settings or UI."
                )

        evaluator_model = getattr(self.evaluator, "model_name", "unknown")
        prompt_version = getattr(self.evaluator, "PROMPT_VERSION", "v1.0")
        cache_key = self._make_cache_key(audio_sha256, evaluator_model, prompt_version)

        # Check cache if not forced
        if not force_reevaluate and cache_key in self._cache:
            cached_id = self._cache[cache_key]
            cached_eval = self.get_evaluation(cached_id)
            if cached_eval:
                logger.info(f"Retrieved cached evaluation {cached_id} for audio {audio_id}")
                return cached_eval

        # Execute evaluation
        evaluation = self.evaluator.evaluate(
            audio_path=audio_path,
            audio_id=audio_id,
            audio_sha256=audio_sha256,
            is_reference=is_reference,
            expected_transcript=expected_transcript,
        )

        # Persist result
        file_path = self.evaluations_dir / f"{evaluation.evaluation_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(evaluation.model_dump_json(indent=2))

        self._cache[cache_key] = evaluation.evaluation_id
        self._save_index()
        logger.info(f"Persisted evaluation {evaluation.evaluation_id} to {file_path}")

        return evaluation

"""Mock audio evaluator for offline testing and deterministic verification."""

import uuid
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import AudioEvaluator
from src.voice_lab.domain.evaluation_models import AudioEvaluation


class MockAudioEvaluator(AudioEvaluator):
    """Deterministic simulated evaluator for tests (clearly identified as MOCK)."""

    def __init__(self, model_name: str = "mock-evaluator-v1"):
        self.model_name = model_name

    def evaluate(
        self,
        audio_path: Path,
        audio_id: str,
        audio_sha256: str,
        is_reference: bool = False,
        expected_transcript: Optional[str] = None,
    ) -> AudioEvaluation:
        """Return an explicitly identified mock evaluation without calling external APIs."""
        eval_id = f"mock_eval_{audio_id}_{uuid.uuid4().hex[:8]}"

        return AudioEvaluation(
            evaluation_id=eval_id,
            audio_id=audio_id,
            audio_sha256=audio_sha256,
            is_reference_audio=is_reference,
            estimated_transcript=expected_transcript or "Transcripción simulada de prueba.",
            perceived_language="es-ES",
            perceived_emotion="nervioso",
            secondary_emotions=["conversacional", "confundido"],
            expressive_intensity=3.8,
            intelligibility_score=4.5,
            prosody_notes="Cadencia rápida y entrecortada con titubeos simulados para pruebas.",
            vocal_characteristics="Filtro metálico ligero de Wheatley simulado.",
            confidence=0.95,
            explanation="Evaluación sintética generada por MockAudioEvaluator para verificación unitaria.",
            uncertainties=["Incertidumbre simulada de prueba."],
            evaluator_provider="mock",
            evaluator_model=self.model_name,
            prompt_version="mock-v1.0",
        )

"""Unit tests for the evaluation subsystem, privacy policies, and cache."""

from pathlib import Path

import pytest

from src.voice_lab.application.evaluation_service import (
    EvaluationService,
    PrivacyPolicyViolationError,
)
from src.voice_lab.domain.evaluation_models import AudioEvaluation
from src.voice_lab.infrastructure.evaluation.gemini_adapter import GeminiAudioEvaluator
from src.voice_lab.infrastructure.evaluation.mock_evaluator import MockAudioEvaluator


class DummyRealEvaluator:
    """Simulates a non-mock provider (e.g. Gemini) to test privacy safeguards."""
    model_name = "gemini-2.5-flash"
    PROMPT_VERSION = "v1.0"

    def evaluate(self, audio_path, audio_id, audio_sha256, is_reference=False, expected_transcript=None):
        return AudioEvaluation(
            evaluation_id="eval_dummy_123",
            audio_id=audio_id,
            audio_sha256=audio_sha256,
            is_reference_audio=is_reference,
            perceived_emotion="sarcástico",
            evaluator_provider="google-genai",
            evaluator_model="gemini-2.5-flash",
        )


def test_mock_evaluator(tmp_path):
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")

    evaluator = MockAudioEvaluator()
    res = evaluator.evaluate(
        audio_path=dummy_wav,
        audio_id="test_01",
        audio_sha256="abc123hash",
        expected_transcript="Frase de prueba",
    )

    assert res.audio_id == "test_01"
    assert res.evaluator_provider == "mock"
    assert res.estimated_transcript == "Frase de prueba"
    assert 1.0 <= res.expressive_intensity <= 5.0
    assert 1.0 <= res.intelligibility_score <= 5.0
    assert 0.0 <= res.confidence <= 1.0


def test_evaluation_caching_and_persistence(tmp_path):
    eval_dir = tmp_path / "evals"
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")

    evaluator = MockAudioEvaluator()
    service = EvaluationService(evaluator=evaluator, evaluations_dir=eval_dir)

    # 1. Initial evaluation
    eval1 = service.evaluate_audio(
        audio_path=dummy_wav,
        audio_id="test_02",
        audio_sha256="hash_001",
    )
    assert (eval_dir / f"{eval1.evaluation_id}.json").exists()

    # 2. Subsequent call should hit cache and return the exact same evaluation_id
    eval2 = service.evaluate_audio(
        audio_path=dummy_wav,
        audio_id="test_02",
        audio_sha256="hash_001",
    )
    assert eval2.evaluation_id == eval1.evaluation_id

    # 3. Forced reevaluation bypasses cache and creates a new record
    eval3 = service.evaluate_audio(
        audio_path=dummy_wav,
        audio_id="test_02",
        audio_sha256="hash_001",
        force_reevaluate=True,
    )
    assert eval3.evaluation_id != eval1.evaluation_id


def test_privacy_shield_blocks_reference_audio(tmp_path):
    eval_dir = tmp_path / "evals"
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")

    real_evaluator = DummyRealEvaluator()

    # Case 1: allow_reference_upload is False -> must raise PrivacyPolicyViolationError
    service_blocked = EvaluationService(
        evaluator=real_evaluator,
        evaluations_dir=eval_dir,
        allow_reference_upload=False,
    )
    with pytest.raises(PrivacyPolicyViolationError) as exc_info:
        service_blocked.evaluate_audio(
            audio_path=dummy_wav,
            audio_id="wheatley_ref_01",
            audio_sha256="sha256_ref_01",
            is_reference=True,
        )
    assert "Blocked external API evaluation of reference audio" in str(exc_info.value)

    # Case 2: allow_reference_upload is True -> allowed to proceed
    service_allowed = EvaluationService(
        evaluator=real_evaluator,
        evaluations_dir=eval_dir,
        allow_reference_upload=True,
    )
    result = service_allowed.evaluate_audio(
        audio_path=dummy_wav,
        audio_id="wheatley_ref_01",
        audio_sha256="sha256_ref_01",
        is_reference=True,
    )
    assert result.is_reference_audio is True
    assert result.evaluation_id == "eval_dummy_123"


def test_gemini_evaluator_missing_key():
    evaluator = GeminiAudioEvaluator(api_key="")
    with pytest.raises(ValueError) as exc:
        evaluator.evaluate(
            audio_path=Path("dummy.wav"),
            audio_id="audio_1",
            audio_sha256="hash",
        )
    assert "GEMINI_API_KEY is not configured" in str(exc.value)

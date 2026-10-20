"""CLI script for evaluating audio clips expressively using Gemini or a simulated mock."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice_lab.application.evaluation_service import (
    EvaluationService,
    PrivacyPolicyViolationError,
)
from src.voice_lab.infrastructure.audio.storage import LocalAudioStorage
from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.evaluation.gemini_adapter import GeminiAudioEvaluator
from src.voice_lab.infrastructure.evaluation.mock_evaluator import MockAudioEvaluator
from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate audio expressiveness, prosody, and transcription with Gemini or Mock."
    )
    parser.add_argument(
        "--audio-path",
        type=Path,
        help="Direct path to an audio file (.wav, .mp3, .ogg).",
    )
    parser.add_argument(
        "--audio-id",
        type=str,
        help="Audio ID from the discovery catalog.",
    )
    parser.add_argument(
        "--transcript",
        type=str,
        help="Expected reference transcript to contrast against.",
    )
    parser.add_argument(
        "--is-reference",
        action="store_true",
        help="Flag indicating that this is a Valve proprietary reference clip.",
    )
    parser.add_argument(
        "--allow-reference-upload",
        action="store_true",
        help="Explicit consent to send reference audio to external provider API.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic offline MockAudioEvaluator without API calls.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-evaluation bypassing the persistent cache.",
    )

    args = parser.parse_args()

    # Resolve audio path, id, sha256
    audio_path = args.audio_path
    audio_id = args.audio_id
    expected_transcript = args.transcript
    is_reference = args.is_reference

    if not audio_path and not audio_id:
        print("[!] Either --audio-path or --audio-id must be provided.")
        sys.exit(1)

    if audio_id and not audio_path:
        repo = JsonReferenceRepository(settings.data_dir / "metadata" / "discovery_catalog.json")
        audio = repo.get_audio_by_id(audio_id)
        if not audio or not audio.local_path:
            print(f"[!] Audio ID '{audio_id}' not found or not downloaded.")
            sys.exit(1)
        audio_path = Path(audio.local_path)
        expected_transcript = expected_transcript or audio.transcript
        is_reference = True

    if not audio_path.exists():
        print(f"[!] Audio file {audio_path} does not exist.")
        sys.exit(1)

    audio_id = audio_id or f"audio_{audio_path.stem}"
    sha256 = LocalAudioStorage.calculate_sha256(audio_path)

    # Initialize evaluator
    if args.mock:
        evaluator = MockAudioEvaluator()
    else:
        evaluator = GeminiAudioEvaluator()

    service = EvaluationService(
        evaluator=evaluator,
        allow_reference_upload=args.allow_reference_upload or settings.allow_reference_external_eval,
    )

    print("\n" + "=" * 70)
    print("STARTING AUDIO EVALUATION")
    print(f"Target Audio: {audio_path}")
    print(f"Audio ID: {audio_id}")
    print(f"SHA-256: {sha256}")
    print(f"Evaluator Provider: {getattr(evaluator, 'model_name', 'default')}")
    print(f"Is Reference: {is_reference}")
    print(f"Reference Upload Allowed: {service.allow_reference_upload}")
    print("=" * 70 + "\n")

    try:
        evaluation = service.evaluate_audio(
            audio_path=audio_path,
            audio_id=audio_id,
            audio_sha256=sha256,
            is_reference=is_reference,
            expected_transcript=expected_transcript,
            force_reevaluate=args.force,
        )

        print("\n" + "=" * 70)
        print("EVALUATION RESULT")
        print(f"Evaluation ID: {evaluation.evaluation_id}")
        print(f"Provider: {evaluation.evaluator_provider} ({evaluation.evaluator_model})")
        print(f"Estimated Transcript: \"{evaluation.estimated_transcript}\"")
        print(f"Perceived Language: {evaluation.perceived_language}")
        print(f"Perceived Emotion: {evaluation.perceived_emotion}")
        print(f"Secondary Emotions: {', '.join(evaluation.secondary_emotions) or 'None'}")
        print(f"Expressive Intensity: {evaluation.expressive_intensity} / 5.0")
        print(f"Intelligibility Score: {evaluation.intelligibility_score} / 5.0")
        print(f"Prosody Notes: {evaluation.prosody_notes}")
        print(f"Vocal Characteristics: {evaluation.vocal_characteristics}")
        print(f"Confidence: {evaluation.confidence * 100:.1f}%")
        print(f"Explanation: {evaluation.explanation}")
        print("=" * 70)

    except PrivacyPolicyViolationError as pve:
        print(f"\n[PRIVACY SHIELD] {pve}")
        sys.exit(2)
    except Exception as exc:
        print(f"\n[ERROR] Evaluation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

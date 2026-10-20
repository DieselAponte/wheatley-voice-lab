"""CLI script for batch speech generation across multiple expressive profiles and comparison."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice_lab.application.comparison_service import ComparisonService
from src.voice_lab.application.generation_service import GenerationService
from src.voice_lab.domain.profiles import ProfileManager
from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.models.chatterbox_adapter import ChatterboxAdapter
from src.voice_lab.infrastructure.persistence.json_generation_repository import (
    JsonGenerationRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch generate expressive speech under various emotion profiles."
    )
    parser.add_argument(
        "--text",
        type=str,
        default="¡Hola! No te alarmes, pero creo que tenemos un pequeño problema aquí.",
        help="Text to synthesize in Spanish.",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default="conversacional,nervioso,entusiasmado",
        help="Comma-separated list of profile IDs to evaluate.",
    )
    parser.add_argument(
        "--reference-audio",
        type=Path,
        help="Optional path to reference audio clip for voice cloning.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Output structured side-by-side comparison after generation.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        help="Directory to export manifest and audio bundle.",
    )

    args = parser.parse_args()
    profile_ids = [p.strip() for p in args.profiles.split(",") if p.strip()]

    settings.ensure_directories()
    repo = JsonGenerationRepository()
    adapter = ChatterboxAdapter()
    profile_manager = ProfileManager()
    service = GenerationService(generator=adapter, repository=repo, profile_manager=profile_manager)
    comparison_service = ComparisonService(generation_repo=repo)

    print("\n" + "=" * 70)
    print("STARTING BATCH GENERATION")
    print(f"Text: \"{args.text}\"")
    print(f"Profiles: {profile_ids}")
    print(f"Reference Audio: {args.reference_audio or 'None'}")
    print("=" * 70 + "\n")

    results = service.generate_batch(
        texts=[args.text],
        profile_ids=profile_ids,
        reference_audio_path=args.reference_audio,
    )

    print("\n" + "=" * 70)
    print(f"BATCH COMPLETED ({len(results)} generations produced)")
    print("=" * 70)
    for rec in results:
        print(f"[{rec.profile_name}] ID: {rec.generation_id}")
        print(f"  Duration: {rec.duration_seconds:.2f}s | Size: {rec.file_size_bytes} bytes")
        print(f"  Audio File: {rec.audio_path}")
        print(f"  Parameters: {rec.parameters}")

    if args.compare and results:
        gen_ids = [r.generation_id for r in results]
        comparison = comparison_service.compare_generations(gen_ids)
        print("\n" + "=" * 70)
        print("COMPARISON SUMMARY")
        print("=" * 70)
        print(comparison.summary_text)

    if args.export_dir and results:
        gen_ids = [r.generation_id for r in results]
        exported_path = comparison_service.export_bundle(gen_ids, args.export_dir)
        print(f"\n[+] Bundle successfully exported to: {exported_path}")


if __name__ == "__main__":
    main()

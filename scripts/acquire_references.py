"""CLI script for controlled, resilient downloading of reference audio files."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice_lab.application.acquisition_service import AcquisitionService
from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.persistence.json_reference_repository import (
    JsonReferenceRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Controlled downloader for Wheatley Voice Lab reference audio clips."
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Filter downloads to a specific section ID (e.g. capitulo-1-despertares).",
    )
    parser.add_argument(
        "--audio-id",
        type=str,
        help="Download an individual audio entry by stable ID.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Explicitly allow mass downloading of all eligible audios in the catalog.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of audio files to download in this execution.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the acquisition operation without executing network transfers.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Only target audios that previously failed to download.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if a valid local file already exists.",
    )

    args = parser.parse_args()

    # Safety check: if neither section, audio-id, limit, nor --all is specified, default to a safe limit of 5
    limit = args.limit
    if not args.all and not args.section and not args.audio_id and limit is None:
        print("[!] No --all, --section, or --limit specified. Defaulting to safe preview limit of 5 audios.")
        limit = 5

    settings.ensure_directories()
    catalog_file = settings.data_dir / "metadata" / "discovery_catalog.json"
    if not catalog_file.exists():
        print(f"[!] Discovery catalog not found at {catalog_file}. Run scripts/inspect_source.py --save first.")
        sys.exit(1)

    repo = JsonReferenceRepository(catalog_file)
    service = AcquisitionService(repository=repo)

    audio_ids = [args.audio_id] if args.audio_id else None

    print("\n" + "=" * 70)
    print("STARTING ACQUISITION RUN")
    print(f"Dry Run: {args.dry_run}")
    print(f"Section Filter: {args.section or 'None'}")
    print(f"Audio ID Filter: {args.audio_id or 'None'}")
    print(f"Limit: {limit or 'No limit'}")
    print(f"Retry Failed: {args.retry_failed}")
    print(f"Force: {args.force}")
    print("=" * 70 + "\n")

    results = service.acquire_batch(
        section_id=args.section,
        audio_ids=audio_ids,
        limit=limit,
        dry_run=args.dry_run,
        retry_failed=args.retry_failed,
        force=args.force,
    )

    print("\n" + "=" * 70)
    print("ACQUISITION RESULTS SUMMARY")
    print(f"Total Candidates: {results['total_candidates']}")
    print(f"Downloaded: {results['downloaded']}")
    print(f"Skipped / Dry-run: {results['skipped']}")
    print(f"Failed: {results['failed']}")
    print("=" * 70)

    for item in results["items"]:
        status_tag = f"[{item.status}]"
        print(f"{status_tag:<14} {item.id} -> {item.local_path or 'No path'} ({item.file_size_bytes or 0} bytes)")
        if item.error_message:
            print(f"   Error: {item.error_message}")


if __name__ == "__main__":
    main()

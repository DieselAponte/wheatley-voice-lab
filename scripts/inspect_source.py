"""CLI inspection script for discovering voice lines and chapters in read-only mode."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.wiki.http_client import WikiHttpClient
from src.voice_lab.infrastructure.wiki.parser import WikiParser
from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository


def inspect_source(
    fixture_path: Path | None = None,
    url: str | None = None,
    save: bool = False,
) -> None:
    """Inspect Portal Wiki voice lines hierarchy without downloading audio."""
    parser = WikiParser()
    target_url = url or settings.source_base_url

    if fixture_path:
        print(f"[*] Reading HTML from local fixture: {fixture_path}")
        html_content = fixture_path.read_text(encoding="utf-8")
    else:
        print(f"[*] Fetching live HTML from: {target_url}")
        client = WikiHttpClient(
            timeout_seconds=settings.http_timeout_seconds,
            request_delay_seconds=settings.http_request_delay_seconds,
        )
        try:
            html_content = client.fetch_page(target_url)
        finally:
            client.close()

    print("[*] Parsing document structure...")
    catalog = parser.parse_html(html_content, source_url=target_url)

    print("\n" + "=" * 70)
    print(f"SOURCE PAGE: {catalog.source_page.title}")
    print(f"URL: {catalog.source_page.url}")
    print(f"INSPECTED AT: {catalog.source_page.inspected_at}")
    print(f"TOTAL SECTIONS FOUND: {catalog.source_page.total_sections}")
    print(f"TOTAL AUDIOS DISCOVERED: {catalog.source_page.total_audios}")
    print(f"UNCLASSIFIED ENTRIES: {len(catalog.unclassified_entries)}")
    print("=" * 70 + "\n")

    # Group audios by section
    audio_counts: dict[str, int] = {}
    for a in catalog.audios:
        audio_counts[a.section_id] = audio_counts.get(a.section_id, 0) + 1

    print("--- HIERARCHICAL SECTIONS SUMMARY ---")
    for sec in catalog.sections:
        indent = "  " * (sec.level - 1)
        count = audio_counts.get(sec.id, 0)
        print(f"{indent}- [{sec.level}] {sec.title} ({count} audios) -> ID: {sec.id}")

    print("\n--- SAMPLE DISCOVERED AUDIO ENTRIES (FIRST 5) ---")
    for i, a in enumerate(catalog.audios[:5]):
        print(f"[{i+1}] ID: {a.id}")
        print(f"    Transcript: \"{a.transcript}\"")
        print(f"    Section: {a.section_path}")
        print(f"    Direct URL: {a.direct_url}")
        print(f"    File Page: {a.file_page_url}")

    if save:
        settings.ensure_directories()
        repo = JsonReferenceRepository(settings.data_dir / "metadata" / "discovery_catalog.json")
        repo.save_catalog(catalog)
        print(f"\n[+] Discovery catalog successfully saved to: {repo.catalog_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Portal Wiki voice lines hierarchy (Read-Only).")
    parser.add_argument("--fixture", type=Path, help="Path to local HTML fixture file.")
    parser.add_argument("--url", type=str, help="Live source URL to inspect.")
    parser.add_argument("--save", action="store_true", help="Persist discovered catalog to JSON.")
    args = parser.parse_args()

    inspect_source(fixture_path=args.fixture, url=args.url, save=args.save)


if __name__ == "__main__":
    main()

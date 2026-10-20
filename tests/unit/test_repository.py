"""Unit tests for the JSON reference repository."""

from src.voice_lab.domain.models import (
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
)
from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository


def test_repository_save_and_load(tmp_path):
    catalog_path = tmp_path / "metadata" / "catalog.json"
    repo = JsonReferenceRepository(catalog_path=catalog_path)

    # Initial state
    assert repo.load_catalog() is None
    assert repo.list_sections() == []
    assert repo.list_audios() == []

    sec = ReferenceSection(
        id="sec_1",
        title="Chapter 1",
        level=1,
        order_index=0,
        full_path="Chapter 1",
    )
    audio = ReferenceAudio(
        id="ref_sample_01",
        original_filename="sample_01.wav",
        direct_url="https://example.com/sample_01.wav",
        transcript="Test line",
        section_id="sec_1",
        section_path="Chapter 1",
        order_in_section=0,
        provenance=AssetProvenance(
            source_page_url="https://example.com",
            direct_audio_url="https://example.com/sample_01.wav",
        ),
    )
    source_page = SourcePage(
        url="https://example.com",
        title="Test Page",
        inspected_at="2026-10-20T00:00:00Z",
        total_sections=1,
        total_audios=1,
    )
    catalog = DiscoveryCatalog(
        source_page=source_page,
        sections=[sec],
        audios=[audio],
    )

    repo.save_catalog(catalog)
    assert catalog_path.exists()

    loaded = repo.load_catalog()
    assert loaded is not None
    assert len(loaded.audios) == 1
    assert loaded.audios[0].id == "ref_sample_01"

    # Query tests
    found = repo.get_audio_by_id("ref_sample_01")
    assert found is not None
    assert found.transcript == "Test line"

    not_found = repo.get_audio_by_id("ref_unknown")
    assert not_found is None

    # Update test
    found.status = AcquisitionStatus.DOWNLOADED
    repo.update_audio(found)

    re_loaded_repo = JsonReferenceRepository(catalog_path=catalog_path)
    updated = re_loaded_repo.get_audio_by_id("ref_sample_01")
    assert updated is not None
    assert updated.status == AcquisitionStatus.DOWNLOADED

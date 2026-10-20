"""Unit tests for domain models."""

from src.voice_lab.domain.models import (
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
    VerificationStatus,
)


def test_reference_section_creation():
    sec = ReferenceSection(
        id="capitulo-1/introduccion",
        title="Introducción",
        level=2,
        order_index=1,
        parent_id="capitulo-1",
        full_path="Capítulo 1 > Introducción",
    )
    assert sec.id == "capitulo-1/introduccion"
    assert sec.level == 2
    assert sec.parent_id == "capitulo-1"


def test_reference_audio_creation_and_defaults():
    provenance = AssetProvenance(
        source_page_url="https://theportalwiki.com/wiki/Wheatley_voice_lines/es",
        file_page_url="https://theportalwiki.com/wiki/File:Wheatley_hello.wav",
        direct_audio_url="https://i1.theportalwiki.net/img/hello.wav",
        verification_status=VerificationStatus.VERIFIED_VALVE_PROPRIETARY,
    )
    audio = ReferenceAudio(
        id="ref_wheatley_hello",
        original_filename="Wheatley_hello.wav",
        direct_url="https://i1.theportalwiki.net/img/hello.wav",
        transcript="Hola",
        section_id="capitulo-1",
        section_path="Capítulo 1",
        order_in_section=0,
        provenance=provenance,
    )
    assert audio.status == AcquisitionStatus.DISCOVERED
    assert audio.expected_format == "wav"
    assert audio.provenance.verification_status == VerificationStatus.VERIFIED_VALVE_PROPRIETARY


def test_discovery_catalog_serialization():
    source_page = SourcePage(
        url="https://theportalwiki.com",
        title="Test Page",
        inspected_at="2026-10-20T00:00:00Z",
    )
    catalog = DiscoveryCatalog(source_page=source_page)
    dumped = catalog.model_dump()
    assert dumped["source_page"]["title"] == "Test Page"
    reloaded = DiscoveryCatalog.model_validate(dumped)
    assert reloaded.source_page.title == "Test Page"

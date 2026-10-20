"""Unit tests for the AcquisitionService and LocalAudioStorage."""

import httpx
from pathlib import Path
from src.voice_lab.application.acquisition_service import AcquisitionService
from src.voice_lab.domain.models import (
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
)
from src.voice_lab.infrastructure.audio.storage import LocalAudioStorage
from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository
from src.voice_lab.infrastructure.wiki.http_client import WikiHttpClient


def test_audio_storage_path_sanitization(tmp_path):
    storage = LocalAudioStorage(reference_base_dir=tmp_path)
    path = storage.get_reference_path(
        section_id="Capítulo 1: Despertares/Introducción",
        filename="Wheatley: test.wav",
    )
    # Check that invalid characters were sanitized in relative path and filename
    rel_path = path.relative_to(tmp_path)
    assert ":" not in str(rel_path)
    assert ":" not in path.name


def test_acquisition_dry_run(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    repo = JsonReferenceRepository(catalog_path)
    storage = LocalAudioStorage(reference_base_dir=tmp_path / "refs")

    audio = ReferenceAudio(
        id="ref_dry_01",
        original_filename="dry_01.wav",
        direct_url="https://example.com/dry_01.wav",
        transcript="Dry run test",
        section_id="sec_1",
        section_path="Section 1",
        order_in_section=0,
        provenance=AssetProvenance(
            source_page_url="https://example.com",
            direct_audio_url="https://example.com/dry_01.wav",
        ),
    )
    catalog = DiscoveryCatalog(
        source_page=SourcePage(
            url="https://example.com",
            title="Test",
            inspected_at="2026-10-20T00:00:00Z",
        ),
        sections=[ReferenceSection(id="sec_1", title="Sec 1", level=1, order_index=0, full_path="Sec 1")],
        audios=[audio],
    )
    repo.save_catalog(catalog)

    service = AcquisitionService(repository=repo, storage=storage)
    res = service.acquire_batch(dry_run=True)

    assert res["dry_run"] is True
    assert res["total_candidates"] == 1
    assert res["skipped"] == 1
    assert res["downloaded"] == 0
    # Make sure no file was actually downloaded
    assert not (tmp_path / "refs" / "sec_1" / "dry_01.wav").exists()


def test_acquisition_mock_download(tmp_path):
    fake_wav_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("success.wav"):
            return httpx.Response(200, content=fake_wav_content)
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=mock_transport)

    http_client = WikiHttpClient(
        request_delay_seconds=0.0,
        max_retries=1,
        client=mock_client,
    )

    catalog_path = tmp_path / "catalog.json"
    repo = JsonReferenceRepository(catalog_path)
    storage = LocalAudioStorage(reference_base_dir=tmp_path / "refs")

    audio = ReferenceAudio(
        id="ref_mock_01",
        original_filename="success.wav",
        direct_url="https://example.com/audio/success.wav",
        transcript="Success line",
        section_id="sec_1",
        section_path="Section 1",
        order_in_section=0,
        provenance=AssetProvenance(
            source_page_url="https://example.com",
            direct_audio_url="https://example.com/audio/success.wav",
        ),
    )
    catalog = DiscoveryCatalog(
        source_page=SourcePage(
            url="https://example.com",
            title="Test",
            inspected_at="2026-10-20T00:00:00Z",
        ),
        sections=[ReferenceSection(id="sec_1", title="Sec 1", level=1, order_index=0, full_path="Sec 1")],
        audios=[audio],
    )
    repo.save_catalog(catalog)

    service = AcquisitionService(
        repository=repo,
        http_client=http_client,
        storage=storage,
    )

    # 1. Successful download
    results = service.acquire_batch(dry_run=False)
    assert results["downloaded"] == 1
    assert results["failed"] == 0

    downloaded_item = results["items"][0]
    assert downloaded_item.status == AcquisitionStatus.DOWNLOADED
    assert downloaded_item.file_size_bytes == len(fake_wav_content)
    assert downloaded_item.checksum_sha256 is not None
    assert Path(downloaded_item.local_path).exists()

    # 2. Idempotency test: download again with same sha256 should skip
    results_idempotent = service.acquire_batch(dry_run=False)
    # Since candidate status is already DOWNLOADED, candidate list should be empty
    assert results_idempotent["total_candidates"] == 0


def test_acquisition_error_handling(tmp_path):
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    mock_transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.Client(transport=mock_transport)

    http_client = WikiHttpClient(
        request_delay_seconds=0.0,
        max_retries=1,
        client=mock_client,
    )

    catalog_path = tmp_path / "catalog.json"
    repo = JsonReferenceRepository(catalog_path)
    storage = LocalAudioStorage(reference_base_dir=tmp_path / "refs")

    audio = ReferenceAudio(
        id="ref_fail_01",
        original_filename="fail.wav",
        direct_url="https://example.com/fail.wav",
        transcript="Fail line",
        section_id="sec_1",
        section_path="Section 1",
        order_in_section=0,
        provenance=AssetProvenance(
            source_page_url="https://example.com",
            direct_audio_url="https://example.com/fail.wav",
        ),
    )
    catalog = DiscoveryCatalog(
        source_page=SourcePage(
            url="https://example.com",
            title="Test",
            inspected_at="2026-10-20T00:00:00Z",
        ),
        sections=[ReferenceSection(id="sec_1", title="Sec 1", level=1, order_index=0, full_path="Sec 1")],
        audios=[audio],
    )
    repo.save_catalog(catalog)

    service = AcquisitionService(
        repository=repo,
        http_client=http_client,
        storage=storage,
    )

    results = service.acquire_batch(dry_run=False)
    assert results["failed"] == 1
    assert results["downloaded"] == 0

    failed_item = results["items"][0]
    assert failed_item.status == AcquisitionStatus.FAILED
    assert failed_item.error_message is not None

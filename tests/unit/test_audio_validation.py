"""Unit tests for acoustic inspection, technical validation, and audio derivatives."""

import numpy as np
import pytest
import soundfile as sf
from pathlib import Path

from src.voice_lab.infrastructure.audio.validation import AudioInspector
from src.voice_lab.infrastructure.audio.processing import AudioProcessor
from src.voice_lab.application.catalog_service import CatalogService
from src.voice_lab.domain.models import (
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
)
from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository


@pytest.fixture
def synthetic_wav_file(tmp_path) -> Path:
    """Generate a clean synthetic 44.1 kHz sine wave audio file for tests."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Sine wave at 440 Hz (A4) with 0.5 amplitude (-6 dBFS)
    samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    wav_path = tmp_path / "synthetic_test.wav"
    sf.write(str(wav_path), samples, sr, subtype="PCM_16")
    return wav_path


@pytest.fixture
def clipping_wav_file(tmp_path) -> Path:
    """Generate a synthetic audio file exhibiting digital clipping."""
    sr = 44100
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Over-amplitude sine wave clipped to 1.0
    samples = np.clip(1.5 * np.sin(2 * np.pi * 440 * t), -1.0, 1.0).astype(np.float32)

    wav_path = tmp_path / "clipping_test.wav"
    sf.write(str(wav_path), samples, sr, subtype="PCM_16")
    return wav_path


def test_inspect_valid_audio(synthetic_wav_file):
    profile = AudioInspector.inspect_file(synthetic_wav_file)
    assert profile.is_valid is True
    assert profile.sample_rate_hz == 44100
    assert profile.channels == 1
    assert 0.95 <= profile.duration_seconds <= 1.05
    assert profile.peak_amplitude > 0.45
    assert not profile.has_clipping
    assert profile.error_message is None


def test_inspect_clipping_audio(clipping_wav_file):
    profile = AudioInspector.inspect_file(clipping_wav_file)
    assert profile.is_valid is True
    assert profile.has_clipping is True
    assert any("clipping" in w.lower() for w in profile.warnings)


def test_inspect_non_existent_file(tmp_path):
    profile = AudioInspector.inspect_file(tmp_path / "non_existent.wav")
    assert profile.is_valid is False
    assert "File not found" in profile.error_message


def test_inspect_empty_file(tmp_path):
    empty_file = tmp_path / "empty.wav"
    empty_file.write_bytes(b"")
    profile = AudioInspector.inspect_file(empty_file)
    assert profile.is_valid is False
    assert "0 bytes" in profile.error_message


def test_create_derivative(synthetic_wav_file, tmp_path):
    deriv_dir = tmp_path / "derivatives"
    deriv_path, meta = AudioProcessor.create_derivative(
        input_path=synthetic_wav_file,
        output_dir=deriv_dir,
        target_sample_rate=24000,
        mono=True,
    )

    assert deriv_path.exists()
    assert meta.target_sample_rate == 24000
    assert meta.derived_profile.sample_rate_hz == 24000
    assert meta.derived_profile.channels == 1
    assert meta.derived_profile.is_valid is True


def test_catalog_service_validation_and_statistics(tmp_path, synthetic_wav_file):
    catalog_path = tmp_path / "catalog.json"
    repo = JsonReferenceRepository(catalog_path)

    audio = ReferenceAudio(
        id="ref_valid_01",
        original_filename="synthetic_test.wav",
        direct_url="https://example.com/audio.wav",
        transcript="Test line",
        section_id="sec_1",
        section_path="Section 1",
        order_in_section=0,
        status=AcquisitionStatus.DOWNLOADED,
        local_path=str(synthetic_wav_file),
        provenance=AssetProvenance(
            source_page_url="https://example.com",
            direct_audio_url="https://example.com/audio.wav",
        ),
    )
    catalog = DiscoveryCatalog(
        source_page=SourcePage(
            url="https://example.com",
            title="Test",
            inspected_at="2026-10-20T00:00:00Z",
            total_sections=1,
            total_audios=1,
        ),
        sections=[ReferenceSection(id="sec_1", title="Sec 1", level=1, order_index=0, full_path="Sec 1")],
        audios=[audio],
    )
    repo.save_catalog(catalog)

    service = CatalogService(repository=repo)
    val_res = service.validate_catalog()

    assert val_res["validated"] == 1
    assert val_res["invalid"] == 0

    # Verify audio updated
    updated_audio = repo.get_audio_by_id("ref_valid_01")
    assert updated_audio.status == AcquisitionStatus.VALIDATED
    assert updated_audio.sample_rate_hz == 44100
    assert updated_audio.duration_seconds > 0

    # Verify statistics
    stats = service.get_statistics()
    assert stats.total_audios == 1
    assert stats.total_validated == 1
    assert stats.total_duration_seconds > 0

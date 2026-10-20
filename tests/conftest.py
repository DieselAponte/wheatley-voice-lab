"""Pytest configuration and global fixtures."""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.voice_lab.domain.models import (  # noqa: E402
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
)
from src.voice_lab.infrastructure.persistence.json_reference_repository import (  # noqa: E402
    JsonReferenceRepository,
)


@pytest.fixture
def sample_wav_path(tmp_path: Path) -> Path:
    """Generate a clean synthetic 24 kHz audio sample for testing."""
    sr = 24000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    samples = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wav_file = tmp_path / "sample_audio.wav"
    sf.write(str(wav_file), samples, sr, subtype="PCM_16")
    return wav_file


@pytest.fixture
def sample_catalog_path(tmp_path: Path, sample_wav_path: Path) -> Path:
    """Create a populated test catalog with sections and audios."""
    cat_file = tmp_path / "metadata" / "test_catalog.json"
    repo = JsonReferenceRepository(catalog_path=cat_file)

    sec1 = ReferenceSection(
        id="capitulo-1",
        title="Capítulo 1: Cortesía",
        level=1,
        order_index=0,
        full_path="Capítulo 1",
    )
    sec2 = ReferenceSection(
        id="capitulo-2",
        title="Capítulo 2: El Pozo de Pruebas",
        level=1,
        order_index=1,
        full_path="Capítulo 2",
    )

    audio1 = ReferenceAudio(
        id="audio_01",
        original_filename="wheatley_01.wav",
        direct_url="https://example.com/audio1.wav",
        transcript="¡Hola! ¿Hay alguien ahí fuera?",
        section_id="capitulo-1",
        section_path="Capítulo 1",
        order_in_section=0,
        status=AcquisitionStatus.DOWNLOADED,
        local_path=str(sample_wav_path),
        duration_seconds=1.0,
        sample_rate_hz=24000,
        channels=1,
        provenance=AssetProvenance(
            source_page_url="https://theportalwiki.com/wiki/Wheatley_voice_lines/es",
            direct_audio_url="https://example.com/audio1.wav",
        ),
    )

    catalog = DiscoveryCatalog(
        source_page=SourcePage(
            url="https://theportalwiki.com/wiki/Wheatley_voice_lines/es",
            title="Portal Wiki - Wheatley Lines",
            inspected_at="2026-10-20T00:00:00Z",
            total_sections=2,
            total_audios=1,
        ),
        sections=[sec1, sec2],
        audios=[audio1],
    )
    repo.save_catalog(catalog)
    return cat_file

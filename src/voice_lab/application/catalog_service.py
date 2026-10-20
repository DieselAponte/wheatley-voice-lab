"""Catalog management service for acoustic validation and statistical coverage analysis."""

import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.voice_lab.domain.contracts import ReferenceRepository
from src.voice_lab.domain.models import AcquisitionStatus, ReferenceAudio
from src.voice_lab.infrastructure.audio.validation import AudioInspector, AudioTechnicalProfile

logger = logging.getLogger(__name__)


class SectionStatistics(BaseModel):
    """Aggregate acquisition and validation counts for a section."""

    model_config = ConfigDict(extra="ignore")

    section_id: str
    section_title: str
    level: int
    total_discovered: int = 0
    total_downloaded: int = 0
    total_validated: int = 0
    total_invalid: int = 0
    total_pending: int = 0


class CatalogStatisticsSummary(BaseModel):
    """Overall statistics across the entire reference catalog."""

    model_config = ConfigDict(extra="ignore")

    total_sections: int = 0
    total_audios: int = 0
    total_downloaded: int = 0
    total_validated: int = 0
    total_invalid: int = 0
    total_pending: int = 0
    total_duration_seconds: float = 0.0
    sections: list[SectionStatistics] = Field(default_factory=list)


class CatalogService:
    """Orchestrates acoustic validation across downloaded audios and compiles statistics."""

    def __init__(self, repository: ReferenceRepository):
        self.repository = repository

    def inspect_audio_entry(self, audio_id: str) -> tuple[Optional[ReferenceAudio], Optional[AudioTechnicalProfile]]:
        """Run technical inspection on a single catalog audio file."""
        audio = self.repository.get_audio_by_id(audio_id)
        if not audio or not audio.local_path:
            return audio, None

        profile = AudioInspector.inspect_file(audio.local_path)
        if profile.is_valid:
            audio.status = AcquisitionStatus.VALIDATED
            audio.duration_seconds = profile.duration_seconds
            audio.sample_rate_hz = profile.sample_rate_hz
            audio.channels = profile.channels
            audio.error_message = None
        else:
            audio.status = AcquisitionStatus.INVALID
            audio.error_message = profile.error_message

        self.repository.update_audio(audio)
        return audio, profile

    def validate_catalog(self) -> dict[str, Any]:
        """Validate all downloaded audios in the catalog and update their technical metrics."""
        catalog = self.repository.load_catalog()
        if not catalog:
            return {"total": 0, "validated": 0, "invalid": 0}

        validated_count = 0
        invalid_count = 0

        for audio in catalog.audios:
            if audio.status in (AcquisitionStatus.DOWNLOADED, AcquisitionStatus.VALIDATED) and audio.local_path:
                profile = AudioInspector.inspect_file(audio.local_path)
                if profile.is_valid:
                    audio.status = AcquisitionStatus.VALIDATED
                    audio.duration_seconds = profile.duration_seconds
                    audio.sample_rate_hz = profile.sample_rate_hz
                    audio.channels = profile.channels
                    audio.error_message = None
                    validated_count += 1
                else:
                    audio.status = AcquisitionStatus.INVALID
                    audio.error_message = profile.error_message
                    invalid_count += 1
                self.repository.update_audio(audio)

        return {
            "total_processed": validated_count + invalid_count,
            "validated": validated_count,
            "invalid": invalid_count,
        }

    def get_statistics(self) -> CatalogStatisticsSummary:
        """Compute aggregate metrics and breakdown per section."""
        catalog = self.repository.load_catalog()
        if not catalog:
            return CatalogStatisticsSummary()

        sec_map: dict[str, SectionStatistics] = {}
        for sec in catalog.sections:
            sec_map[sec.id] = SectionStatistics(
                section_id=sec.id,
                section_title=sec.title,
                level=sec.level,
            )

        total_downloaded = 0
        total_validated = 0
        total_invalid = 0
        total_pending = 0
        total_duration = 0.0

        for audio in catalog.audios:
            sec_stat = sec_map.get(audio.section_id)
            if not sec_stat:
                sec_stat = SectionStatistics(
                    section_id=audio.section_id,
                    section_title=audio.section_path or audio.section_id,
                    level=1,
                )
                sec_map[audio.section_id] = sec_stat

            sec_stat.total_discovered += 1
            if audio.status in (AcquisitionStatus.DOWNLOADED, AcquisitionStatus.VALIDATED):
                sec_stat.total_downloaded += 1
                total_downloaded += 1
            if audio.status == AcquisitionStatus.VALIDATED:
                sec_stat.total_validated += 1
                total_validated += 1
                if audio.duration_seconds:
                    total_duration += audio.duration_seconds
            elif audio.status == AcquisitionStatus.INVALID:
                sec_stat.total_invalid += 1
                total_invalid += 1
            else:
                sec_stat.total_pending += 1
                total_pending += 1

        ordered_sections = sorted(sec_map.values(), key=lambda s: s.section_id)

        return CatalogStatisticsSummary(
            total_sections=len(catalog.sections),
            total_audios=len(catalog.audios),
            total_downloaded=total_downloaded,
            total_validated=total_validated,
            total_invalid=total_invalid,
            total_pending=total_pending,
            total_duration_seconds=round(total_duration, 2),
            sections=ordered_sections,
        )

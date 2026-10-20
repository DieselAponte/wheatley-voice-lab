"""JSON-based repository implementation for reference catalog data."""

import json
import logging
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import ReferenceRepository
from src.voice_lab.domain.models import (
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
)

logger = logging.getLogger(__name__)


class JsonReferenceRepository(ReferenceRepository):
    """File-backed repository persisting catalog and references in JSON format."""

    def __init__(self, catalog_path: Path = Path("data/metadata/discovery_catalog.json")):
        self.catalog_path = catalog_path
        self._cached_catalog: Optional[DiscoveryCatalog] = None

    def save_catalog(self, catalog: DiscoveryCatalog) -> None:
        """Persist catalog safely to JSON."""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.catalog_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(catalog.model_dump(), f, indent=2, ensure_ascii=False)
        temp_path.replace(self.catalog_path)
        self._cached_catalog = catalog
        logger.info(f"Saved catalog with {len(catalog.audios)} audios to {self.catalog_path}")

    def load_catalog(self) -> Optional[DiscoveryCatalog]:
        """Load catalog from disk if it exists."""
        if self._cached_catalog is not None:
            return self._cached_catalog

        if not self.catalog_path.exists():
            return None

        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cached_catalog = DiscoveryCatalog.model_validate(data)
            return self._cached_catalog
        except Exception as e:
            logger.error(f"Error loading catalog from {self.catalog_path}: {e}")
            return None

    def get_audio_by_id(self, audio_id: str) -> Optional[ReferenceAudio]:
        """Find an audio entry by its stable ID."""
        catalog = self.load_catalog()
        if not catalog:
            return None
        for audio in catalog.audios:
            if audio.id == audio_id:
                return audio
        return None

    def update_audio(self, audio: ReferenceAudio) -> None:
        """Update an audio record and save catalog."""
        catalog = self.load_catalog()
        if not catalog:
            raise ValueError("Cannot update audio: catalog has not been initialized.")

        for i, existing in enumerate(catalog.audios):
            if existing.id == audio.id:
                catalog.audios[i] = audio
                self.save_catalog(catalog)
                return

        # If not found, append
        catalog.audios.append(audio)
        self.save_catalog(catalog)

    def list_sections(self) -> list[ReferenceSection]:
        """Return all sections ordered by document sequence."""
        catalog = self.load_catalog()
        if not catalog:
            return []
        return sorted(catalog.sections, key=lambda s: s.order_index)

    def list_audios(self, section_id: Optional[str] = None) -> list[ReferenceAudio]:
        """Return all audios or filtered by section."""
        catalog = self.load_catalog()
        if not catalog:
            return []
        if section_id:
            return [a for a in catalog.audios if a.section_id == section_id or a.section_id.startswith(f"{section_id}/")]
        return catalog.audios

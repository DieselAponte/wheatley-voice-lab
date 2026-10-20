"""JSON-based repository implementation for synthetic generation experiments."""

import json
import logging
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import GenerationRepository
from src.voice_lab.domain.generation_models import GenerationRecord
from src.voice_lab.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class JsonGenerationRepository(GenerationRepository):
    """Stores generation records and manifests in the generated output directory."""

    def __init__(self, generated_dir: Optional[Path] = None):
        self.generated_dir = generated_dir or settings.generated_dir
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.generated_dir / "generation_manifest.json"

    def _get_record_path(self, generation_id: str) -> Path:
        return self.generated_dir / f"{generation_id}.json"

    def save_generation(self, record: GenerationRecord) -> None:
        """Persist a single generation experiment record."""
        target_path = self._get_record_path(record.generation_id)
        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))
        temp_path.replace(target_path)
        logger.info(f"Saved generation record {record.generation_id} to {target_path}")

    def get_generation_by_id(self, generation_id: str) -> Optional[GenerationRecord]:
        """Retrieve a generation record by its unique ID."""
        target_path = self._get_record_path(generation_id)
        if not target_path.exists():
            return None
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GenerationRecord.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to read generation record {target_path}: {e}")
            return None

    def list_generations(self) -> list[GenerationRecord]:
        """List all generation records found in the directory ordered chronologically."""
        records: list[GenerationRecord] = []
        for json_file in self.generated_dir.glob("gen_*.json"):
            if json_file.name == "generation_manifest.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append(GenerationRecord.model_validate(data))
            except Exception as e:
                logger.warning(f"Skipping unreadable generation file {json_file}: {e}")

        # Sort descending by creation date (newest first)
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    def link_evaluation(self, generation_id: str, evaluation_id: str) -> None:
        """Link an evaluation ID to an existing generation record."""
        record = self.get_generation_by_id(generation_id)
        if not record:
            raise ValueError(f"Generation '{generation_id}' not found.")
        if evaluation_id not in record.evaluation_ids:
            record.evaluation_ids.append(evaluation_id)
            self.save_generation(record)

    # Alias for API flexibility
    attach_evaluation = link_evaluation


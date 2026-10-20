"""Comparison and export application service for evaluation and portfolio delivery."""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import GenerationRepository
from src.voice_lab.domain.generation_models import GenerationComparison, GenerationRecord

logger = logging.getLogger(__name__)


class ComparisonService:
    """Provides side-by-side comparison between generation experiments and selective exporting."""

    def __init__(self, generation_repo: GenerationRepository):
        self.generation_repo = generation_repo

    def compare_generations(self, generation_ids: list[str]) -> GenerationComparison:
        """Analyze multiple generation records to produce structured comparative metrics."""
        records: list[GenerationRecord] = []
        for gid in generation_ids:
            rec = self.generation_repo.get_generation_by_id(gid)
            if rec:
                records.append(rec)

        if not records:
            raise ValueError("No valid generation records found for the requested IDs.")

        texts = {r.text for r in records}
        has_same_text = len(texts) == 1
        unique_profiles = list({r.profile_name for r in records})

        durations = [r.duration_seconds for r in records if r.duration_seconds > 0]
        min_dur = min(durations) if durations else 0.0
        max_dur = max(durations) if durations else 0.0

        summary_lines = [
            f"Comparando {len(records)} experimentos de síntesis:",
            f"- Mismo texto base: {'Sí' if has_same_text else 'No'}",
            f"- Perfiles comparados: {', '.join(unique_profiles)}",
            f"- Rango de duración: {min_dur:.2f}s - {max_dur:.2f}s",
        ]

        return GenerationComparison(
            records=records,
            has_same_text=has_same_text,
            unique_profiles=unique_profiles,
            duration_range_seconds=(min_dur, max_dur),
            summary_text="\n".join(summary_lines),
        )

    def export_bundle(
        self,
        generation_ids: list[str],
        destination_dir: Path | str,
        include_audio: bool = True,
    ) -> Path:
        """Export a reproducible JSON metadata manifest and selected audio files for portfolio use."""
        dest = Path(destination_dir)
        dest.mkdir(parents=True, exist_ok=True)

        exported_records = []
        for gid in generation_ids:
            rec = self.generation_repo.get_generation_by_id(gid)
            if not rec:
                continue
            record_dict = rec.model_dump()

            if include_audio and rec.audio_path:
                source_audio = Path(rec.audio_path)
                if source_audio.exists():
                    target_audio = dest / f"{rec.generation_id}_{rec.profile_id}.wav"
                    shutil.copy2(source_audio, target_audio)
                    record_dict["exported_audio_file"] = target_audio.name

            exported_records.append(record_dict)

        manifest_path = dest / "export_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_items": len(exported_records),
                "exported_items": exported_records,
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported bundle with {len(exported_records)} items to {dest}")
        return dest

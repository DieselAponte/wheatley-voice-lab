"""Unit tests for GenerationService, JsonGenerationRepository, and ComparisonService."""

import pytest
from pathlib import Path

from src.voice_lab.application.comparison_service import ComparisonService
from src.voice_lab.application.generation_service import GenerationService
from src.voice_lab.domain.generation_models import GenerationRecord
from src.voice_lab.domain.profiles import ProfileManager
from src.voice_lab.infrastructure.models.chatterbox_adapter import ChatterboxAdapter
from src.voice_lab.infrastructure.persistence.json_generation_repository import JsonGenerationRepository


def test_generation_phrase_success(tmp_path):
    repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    adapter = ChatterboxAdapter(sample_rate=24000)
    manager = ProfileManager(config_path=Path("configs/emotion_profiles.json"))
    service = GenerationService(
        generator=adapter,
        repository=repo,
        profile_manager=manager,
        output_dir=tmp_path / "gen",
    )

    record = service.generate_phrase(
        text="Frase de prueba para síntesis de voz.",
        profile_id="entusiasmado",
        custom_params={"speed": 1.2},
    )

    assert record.generation_id.startswith("gen_")
    assert record.profile_id == "entusiasmado"
    assert record.parameters["speed"] == 1.2
    assert record.status == "SUCCESS"
    assert record.duration_seconds > 0
    assert Path(record.audio_path).exists()
    assert (tmp_path / "gen" / f"{record.generation_id}.json").exists()


def test_generation_invalid_text(tmp_path):
    repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    adapter = ChatterboxAdapter()
    service = GenerationService(generator=adapter, repository=repo, output_dir=tmp_path / "gen")

    with pytest.raises(ValueError):
        service.generate_phrase(text=" ")


def test_generation_batch(tmp_path):
    repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    adapter = ChatterboxAdapter()
    manager = ProfileManager(config_path=Path("configs/emotion_profiles.json"))
    service = GenerationService(
        generator=adapter,
        repository=repo,
        profile_manager=manager,
        output_dir=tmp_path / "gen",
    )

    records = service.generate_batch(
        texts=["Texto de prueba uno.", "Texto de prueba dos."],
        profile_ids=["conversacional", "nervioso"],
    )

    assert len(records) == 4
    all_ids = {r.generation_id for r in records}
    assert len(all_ids) == 4  # All unique IDs


def test_comparison_and_bundle_export(tmp_path):
    repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    adapter = ChatterboxAdapter()
    manager = ProfileManager(config_path=Path("configs/emotion_profiles.json"))
    service = GenerationService(generator=adapter, repository=repo, profile_manager=manager, output_dir=tmp_path / "gen")
    comp_service = ComparisonService(generation_repo=repo)

    r1 = service.generate_phrase("Misma frase base para comparar.", profile_id="conversacional")
    r2 = service.generate_phrase("Misma frase base para comparar.", profile_id="nervioso")

    # Link evaluation test
    repo.link_evaluation(r1.generation_id, "mock_eval_001")
    reloaded_r1 = repo.get_generation_by_id(r1.generation_id)
    assert "mock_eval_001" in reloaded_r1.evaluation_ids

    # Comparison test
    comparison = comp_service.compare_generations([r1.generation_id, r2.generation_id])
    assert comparison.has_same_text is True
    assert len(comparison.unique_profiles) == 2
    assert "conversacional" in [p.lower() for p in comparison.unique_profiles]

    # Export bundle test
    export_dest = tmp_path / "exported_bundle"
    comp_service.export_bundle([r1.generation_id, r2.generation_id], destination_dir=export_dest, include_audio=True)

    assert (export_dest / "export_manifest.json").exists()
    assert (export_dest / f"{r1.generation_id}_{r1.profile_id}.wav").exists()
    assert (export_dest / f"{r2.generation_id}_{r2.profile_id}.wav").exists()

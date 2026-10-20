"""Unit tests for the Gradio interactive presentation layer."""

from pathlib import Path

import gradio as gr

from src.voice_lab.infrastructure.persistence.json_generation_repository import (
    JsonGenerationRepository,
)
from src.voice_lab.infrastructure.persistence.json_reference_repository import (
    JsonReferenceRepository,
)
from src.voice_lab.presentation.gradio_app import VoiceLabApp


def test_voicelab_app_initialization(sample_catalog_path: Path, tmp_path: Path):
    """Test that VoiceLabApp initializes cleanly with custom repositories."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    assert app.ref_repo is not None
    assert app.gen_repo is not None
    assert app.acquisition_service is not None
    assert app.catalog_service is not None
    assert app.generation_service is not None
    assert app.evaluation_service is not None
    assert app.comparison_service is not None


def test_build_app_structure(sample_catalog_path: Path, tmp_path: Path):
    """Test that build_app returns a valid gr.Blocks instance."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    demo = app.build_app()
    assert isinstance(demo, gr.Blocks)
    assert demo.title == "Wheatley Voice Lab — Aperture Science Audio Division"


def test_tab1_acquisition_helpers(sample_catalog_path: Path, tmp_path: Path):
    """Test acquisition tab helper methods."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    choices = app.get_section_choices()
    assert len(choices) >= 2
    assert choices[0] == ("Todas las secciones", "ALL")

    summary_md = app.get_catalog_summary_markdown()
    assert "Secciones de Wiki" in summary_md
    assert "Líneas Descubiertas" in summary_md

    # Test dry-run acquisition from UI
    result_text, updated_stats = app.run_acquisition(
        section_id="ALL",
        limit=2,
        dry_run=True,
        force=False,
        retry_failed=False,
    )
    assert "SIMULACIÓN (DRY-RUN)" in result_text
    assert "Candidatos evaluados" in result_text


def test_tab2_reference_inspection(sample_catalog_path: Path, tmp_path: Path, sample_wav_path: Path):
    """Test reference catalog inspection helper methods."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    # Attach sample wav path to catalog entry
    audio = ref_repo.get_audio_by_id("audio_01")
    assert audio is not None
    audio.local_path = str(sample_wav_path)
    ref_repo.update_audio(audio)

    choices = app.get_downloaded_audio_choices("ALL")
    assert len(choices) >= 1
    assert choices[0][1] == "audio_01"

    path, md = app.inspect_selected_reference("audio_01")
    assert path == str(sample_wav_path)
    assert "Diagnóstico Acústico" in md
    assert "Frecuencia de Muestreo" in md
    assert "Nivel RMS" in md


def test_tab3_synthesis_and_profiles(sample_catalog_path: Path, tmp_path: Path):
    """Test speech generation tab methods."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    # Profile selection
    desc, spd, exag, temp, cfg, phrases = app.on_profile_selected("Entusiasmado")
    assert "Perfil: Entusiasmado" in desc
    assert spd > 1.0
    assert exag > 0.5
    assert len(phrases) > 0

    # Synthesis execution
    audio_path, summary_md, choices = app.synthesize_speech(
        text="¡Hola! ¿Hay alguien ahí fuera?",
        profile_name="Nervioso",
        speed=1.2,
        exaggeration=0.8,
        temperature=0.9,
        cfg_weight=0.6,
    )
    assert audio_path is not None
    assert Path(audio_path).exists()
    assert "Síntesis Completada" in summary_md
    assert len(choices) >= 1


def test_tab4_evaluation_privacy_shield(sample_catalog_path: Path, tmp_path: Path, sample_wav_path: Path):
    """Test evaluation tab with Privacy Shield enforcement."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    audio = ref_repo.get_audio_by_id("audio_01")
    assert audio is not None
    audio.local_path = str(sample_wav_path)
    ref_repo.update_audio(audio)

    # Synthetic audio evaluation with mock
    gen_record = app.generation_service.generate_phrase(
        text="Frase de prueba sintética para evaluar",
        profile_id="conversacional",
    )

    eval_md = app.run_evaluation(
        audio_target_type="Audio Sintético",
        generation_id=gen_record.generation_id,
        reference_id="",
        evaluator_choice="Simulador Offline (Mock)",
        privacy_consent=False,
    )
    assert "Diagnóstico de Evaluación" in eval_md
    assert "Claridad / Inteligibilidad" in eval_md


def test_tab5_history_and_comparison(sample_catalog_path: Path, tmp_path: Path):
    """Test history, side-by-side comparison, and bundle export."""
    ref_repo = JsonReferenceRepository(catalog_path=sample_catalog_path)
    gen_repo = JsonGenerationRepository(generated_dir=tmp_path / "gen")
    app = VoiceLabApp(ref_repo=ref_repo, gen_repo=gen_repo)

    # Generate 2 records
    rec1 = app.generation_service.generate_phrase("Frase comparativa número 1", "conversacional")
    rec2 = app.generation_service.generate_phrase("Frase comparativa número 1", "sarcastico")

    # History dataframe rows
    rows = app.get_history_dataframe()
    assert len(rows) >= 2

    # Side-by-side comparison
    a_path, b_path, comp_md = app.compare_two_generations(rec1.generation_id, rec2.generation_id)
    assert a_path is not None
    assert b_path is not None
    assert "Comparativa Lado a Lado" in comp_md
    assert "Texto idéntico" in comp_md

    # Bundle export
    bundle_dest = tmp_path / "exported_test_ui"
    export_msg = app.export_bundle_ui(str(bundle_dest))
    assert "Paquete de auditoría exportado exitosamente" in export_msg
    assert (bundle_dest / "manifest.json").exists()
    assert (bundle_dest / "export_manifest.json").exists()

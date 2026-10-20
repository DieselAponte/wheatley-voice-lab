"""Interactive Gradio Web Dashboard for Wheatley Voice Lab.

Decoupled presentation layer strictly invoking application services:
- AcquisitionService
- CatalogService
- GenerationService
- EvaluationService
- ComparisonService
"""

import argparse
import logging
from pathlib import Path
from typing import Any, Optional

import gradio as gr

from src.voice_lab.application.acquisition_service import AcquisitionService
from src.voice_lab.application.catalog_service import CatalogService
from src.voice_lab.application.comparison_service import ComparisonService
from src.voice_lab.application.evaluation_service import (
    EvaluationService,
    PrivacyPolicyViolationError,
)
from src.voice_lab.application.generation_service import GenerationService
from src.voice_lab.domain.contracts import AudioEvaluator
from src.voice_lab.domain.models import AcquisitionStatus, DiscoveryCatalog
from src.voice_lab.domain.profiles import ProfileManager
from src.voice_lab.infrastructure.audio.storage import LocalAudioStorage
from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.evaluation.gemini_adapter import GeminiAudioEvaluator
from src.voice_lab.infrastructure.evaluation.mock_evaluator import MockAudioEvaluator
from src.voice_lab.infrastructure.models.chatterbox_adapter import ChatterboxAdapter
from src.voice_lab.infrastructure.persistence.json_generation_repository import (
    JsonGenerationRepository,
)
from src.voice_lab.infrastructure.persistence.json_reference_repository import (
    JsonReferenceRepository,
)

logger = logging.getLogger(__name__)

# Custom Aperture Science / Wheatley Theme Styling
APERTURE_CSS = """
:root {
    --primary-blue: #00a2ff;
    --primary-hover: #0084d1;
    --aperture-orange: #ff7300;
    --surface-dark: #0f141c;
    --surface-card: #161e2b;
    --surface-border: #233145;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
}

body, .gradio-container {
    background-color: var(--surface-dark) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

.aperture-header {
    background: linear-gradient(135deg, #0b111a 0%, #152233 100%);
    border: 1px solid var(--surface-border);
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0, 162, 255, 0.08);
}

.aperture-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background-color: rgba(0, 162, 255, 0.15);
    color: var(--primary-blue);
    border: 1px solid rgba(0, 162, 255, 0.3);
}

.privacy-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background-color: rgba(255, 115, 0, 0.15);
    color: var(--aperture-orange);
    border: 1px solid rgba(255, 115, 0, 0.4);
}

.metric-card {
    background: var(--surface-card);
    border: 1px solid var(--surface-border);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}

.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--primary-blue);
}

.metric-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-transform: uppercase;
}
"""


class VoiceLabApp:
    """Encapsulates the presentation logic and service dispatching for the Gradio dashboard."""

    def __init__(
        self,
        ref_repo: Optional[JsonReferenceRepository] = None,
        gen_repo: Optional[JsonGenerationRepository] = None,
        acquisition_service: Optional[AcquisitionService] = None,
        catalog_service: Optional[CatalogService] = None,
        generation_service: Optional[GenerationService] = None,
        evaluation_service: Optional[EvaluationService] = None,
        comparison_service: Optional[ComparisonService] = None,
        profile_manager: Optional[ProfileManager] = None,
    ):
        self.ref_repo = ref_repo or JsonReferenceRepository()
        self.gen_repo = gen_repo or JsonGenerationRepository()
        self.profile_manager = profile_manager or ProfileManager()

        self.acquisition_service = acquisition_service or AcquisitionService(repository=self.ref_repo)
        self.catalog_service = catalog_service or CatalogService(repository=self.ref_repo)

        # TTS Generator (Chatterbox with deterministic simulation fallback)
        generator = ChatterboxAdapter()
        self.generation_service = generation_service or GenerationService(
            generator=generator,
            repository=self.gen_repo,
            profile_manager=self.profile_manager,
        )

        # Evaluator service defaults to Gemini if key exists, otherwise Mock for local offline testing
        evaluator = GeminiAudioEvaluator() if settings.gemini_api_key else MockAudioEvaluator()
        self.evaluation_service = evaluation_service or EvaluationService(
            evaluator=evaluator,
            allow_reference_upload=settings.allow_reference_external_eval,
        )

        self.comparison_service = comparison_service or ComparisonService(generation_repo=self.gen_repo)

    # -------------------------------------------------------------------------
    # Helper Data Methods
    # -------------------------------------------------------------------------

    def get_section_choices(self) -> list[tuple[str, str]]:
        """Get dropdown choices for catalog sections."""
        catalog = self.ref_repo.load_catalog()
        if not catalog:
            return [("Todas las secciones", "ALL")]
        choices = [("Todas las secciones", "ALL")]
        for sec in catalog.sections:
            display = f"{'—' * (sec.level - 1)} {sec.title} ({sec.id})"
            choices.append((display, sec.id))
        return choices

    def _get_section_and_descendant_ids(self, section_id: str, catalog: DiscoveryCatalog) -> set[str]:
        """Find the section ID and all descendant section IDs recursively."""
        target_ids = {section_id}
        added = True
        while added:
            added = False
            for sec in catalog.sections:
                if (sec.parent_id in target_ids or sec.id.startswith(f"{section_id}/")) and sec.id not in target_ids:
                    target_ids.add(sec.id)
                    added = True
        return target_ids

    def get_downloaded_audio_choices(self, section_filter: str = "ALL") -> list[tuple[str, str]]:
        """Get list of downloaded reference audios for playback/inspection."""
        catalog = self.ref_repo.load_catalog()
        if not catalog:
            return []

        allowed_sections: Optional[set[str]] = None
        if section_filter and section_filter != "ALL":
            allowed_sections = self._get_section_and_descendant_ids(section_filter, catalog)

        items = []
        for a in catalog.audios:
            if a.status in (AcquisitionStatus.DOWNLOADED, AcquisitionStatus.VALIDATED) and a.local_path:
                if allowed_sections is not None:
                    if (
                        a.section_id not in allowed_sections
                        and a.section_id != section_filter
                        and not a.section_id.startswith(f"{section_filter}/")
                    ):
                        continue
                transcript_preview = (a.transcript or "")[:35]
                label = f"[{a.id}] {a.original_filename} - {transcript_preview}..."
                items.append((label, a.id))

        return items

    def get_all_reference_choices(self) -> list[tuple[str, str]]:
        """Get list of downloaded references for cloning prompt."""
        return self.get_downloaded_audio_choices(section_filter="ALL")

    def get_generation_choices(self) -> list[tuple[str, str]]:
        """Get list of generated records for comparison and evaluation."""
        records = self.gen_repo.list_generations()
        if not records:
            return []
        items = []
        for r in records:
            label = f"[{r.generation_id}] {r.profile_name} - {r.text[:30]}... ({r.duration_seconds:.1f}s)"
            items.append((label, r.generation_id))
        return items

    # -------------------------------------------------------------------------
    # Tab 1: Fuente y Adquisición
    # -------------------------------------------------------------------------

    def get_catalog_summary_markdown(self) -> str:
        """Render markdown summary of catalog stats."""
        stats = self.catalog_service.get_statistics()
        if stats.total_audios == 0:
            return "⚠️ **Catálogo no inicializado**. Ejecute `scripts/inspect_source.py` para descubrir la wiki."

        return f"""
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
  <div class="metric-card">
    <div class="metric-value">{stats.total_sections}</div>
    <div class="metric-label">Secciones de Wiki</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{stats.total_audios}</div>
    <div class="metric-label">Líneas Descubiertas</div>
  </div>
  <div class="metric-card">
    <div class="metric-value" style="color: #ffaa00;">{stats.total_downloaded}</div>
    <div class="metric-label">Audios Descargados</div>
  </div>
  <div class="metric-card">
    <div class="metric-value" style="color: #00e676;">{stats.total_validated}</div>
    <div class="metric-label">Validados ({stats.total_duration_seconds:.1f}s)</div>
  </div>
</div>
"""

    def run_acquisition(
        self,
        section_id: str,
        limit: int,
        dry_run: bool,
        force: bool,
        retry_failed: bool,
    ) -> tuple[str, str]:
        """Trigger controlled acquisition batch from the UI."""
        target_sec = None if section_id == "ALL" else section_id
        try:
            res = self.acquisition_service.acquire_batch(
                section_id=target_sec,
                limit=limit if limit > 0 else None,
                dry_run=dry_run,
                force=force,
                retry_failed=retry_failed,
            )
            mode_tag = "SIMULACIÓN (DRY-RUN)" if dry_run else "DESCARGA REAL"
            summary = (
                f"### Resultado de Adquisición [{mode_tag}]\n"
                f"- **Candidatos evaluados**: {res['total_candidates']}\n"
                f"- **Descargados exitosamente**: {res['downloaded']}\n"
                f"- **Omitidos (ya existentes o simulación)**: {res['skipped']}\n"
                f"- **Fallidos**: {res['failed']}\n\n"
            )
            if res["items"]:
                summary += "**Archivos procesados en este lote:**\n"
                for item in res["items"][:15]:
                    summary += f"- `[{item.id}]` {item.original_filename} → Status: **{item.status.value}**\n"
                if len(res["items"]) > 15:
                    summary += f"- *... y {len(res['items']) - 15} audios más.*"

            updated_stats = self.get_catalog_summary_markdown()
            return summary, updated_stats
        except Exception as exc:
            logger.error(f"Error in UI acquisition: {exc}")
            return f"❌ **Error durante la adquisición**: {exc}", self.get_catalog_summary_markdown()

    # -------------------------------------------------------------------------
    # Tab 2: Catálogo de Referencias
    # -------------------------------------------------------------------------

    def inspect_selected_reference(self, audio_id: str) -> tuple[Optional[str], str]:
        """Load technical profile and audio player for reference audio."""
        if not audio_id:
            return None, "Seleccione un audio de referencia válido."

        audio, profile = self.catalog_service.inspect_audio_entry(audio_id)
        if not audio:
            return None, f"❌ No se encontró el registro con ID `{audio_id}`."

        if not audio.local_path or not Path(audio.local_path).exists():
            return None, f"⚠️ El archivo local `{audio.local_path}` no está presente en disco."

        clip_warning = "⚠️ **SÍ (Riesgo de distorsión)**" if (profile and profile.has_clipping) else "✅ No detectado"
        channels_desc = f"{audio.channels} ({'Mono' if audio.channels == 1 else 'Estéreo'})"

        md = f"""
### Ficha Técnica de Referencia: `{audio.id}`

- **Archivo Original**: `{audio.original_filename}`
- **Capítulo / Sección**: `{audio.section_path or audio.section_id}`
- **Texto Transcrito**:
  > *\"{audio.transcript or '(Sin transcripción)'}\"*

#### Diagnóstico Acústico (SoundFile / NumPy)
| Parámetro | Valor Medido | Estado |
| :--- | :--- | :--- |
| **Duración** | `{audio.duration_seconds or 0.0:.2f} s` | Nominal |
| **Frecuencia de Muestreo** | `{audio.sample_rate_hz or 0} Hz` | Nominal |
| **Canales** | `{channels_desc}` | Nominal |
| **Pico Máximo (dBFS)** | `{f'{profile.peak_dbfs:.2f} dBFS' if profile else 'N/A'}` | Normalizado |
| **Nivel RMS (Amplitud)** | `{f'{profile.rms_amplitude:.4f}' if profile else 'N/A'}` | Nominal |
| **Clipping Detectado** | {clip_warning} | Inspección |
| **Ratio de Silencio** | `{f'{profile.silence_ratio * 100:.1f}%' if profile else 'N/A'}` | Nominal |

- **Ruta Local**: `{audio.local_path}`
- **Hash SHA-256**: `{audio.checksum_sha256}`
- **Procedencia Wiki**: [Enlace al recurso]({audio.direct_url})
"""
        return audio.local_path, md

    # -------------------------------------------------------------------------
    # Tab 3: Laboratorio de Generación
    # -------------------------------------------------------------------------

    def on_profile_selected(self, profile_name: str) -> tuple[str, float, float, float, float, list[str]]:
        """Update sliders and description when the user changes profile."""
        profile = self.profile_manager.resolve_profile(profile_name.lower())
        defaults = profile.parameters

        info = f"""
<div class="aperture-badge">Perfil: {profile.name}</div>
<p style="margin-top: 8px; font-size: 0.95rem; color: #cbd5e1;">
  {profile.description}
</p>
<div style="font-size: 0.85rem; color: #94a3b8;">
  <strong>Intención expresiva:</strong> {profile.expressive_intent} |
  <strong>Límites validados:</strong> Velocidad [{profile.parameter_bounds['speed'][0]} - {profile.parameter_bounds['speed'][1]}],
  Exageración [{profile.parameter_bounds['exaggeration'][0]} - {profile.parameter_bounds['exaggeration'][1]}]
</div>
"""
        return (
            info,
            defaults.get("speed", 1.0),
            defaults.get("exaggeration", 0.5),
            defaults.get("temperature", 0.7),
            defaults.get("cfg_weight", 0.5),
            profile.recommended_phrases,
        )

    def synthesize_speech(
        self,
        text: str,
        profile_name: str,
        speed: float,
        exaggeration: float,
        temperature: float,
        cfg_weight: float,
        reference_audio_id: Optional[str] = None,
    ) -> tuple[Optional[str], str, Any]:
        """Orchestrate speech generation from the interactive laboratory."""
        try:
            ref_path = None
            if reference_audio_id and reference_audio_id != "NONE":
                ref_audio = self.ref_repo.get_audio_by_id(reference_audio_id)
                if ref_audio and ref_audio.local_path:
                    ref_path = Path(ref_audio.local_path)

            params = {
                "speed": float(speed),
                "exaggeration": float(exaggeration),
                "temperature": float(temperature),
                "cfg_weight": float(cfg_weight),
            }

            rec = self.generation_service.generate_phrase(
                text=text,
                profile_id=profile_name.lower(),
                custom_params=params,
                reference_audio_path=ref_path,
                reference_audio_id=reference_audio_id if reference_audio_id != "NONE" else None,
            )

            status_icon = "✅" if rec.status == "SUCCESS" else "❌"
            is_sim = "simulat" in rec.generator_device.lower() or "simula" in rec.model_name.lower()
            banner = ""
            if is_sim:
                banner = (
                    "> [!WARNING]\n"
                    "> **MODO SIMULACIÓN ACÚSTICA (Fallback Local)**: No se ha detectado un motor neuronal de voz "
                    "(Chatterbox / PyTorch no instalados). Se generó una onda senoidal acústica modulada a ~220 Hz como prueba técnica de tubería.\n\n"
                )
            summary_md = f"""
{banner}### {status_icon} Síntesis Completada: `{rec.generation_id}`

- **Perfil**: **{rec.profile_name}** (`{rec.profile_id}`)
- **Texto**: *\"{rec.text}\"*
- **Parámetros**: `speed={rec.parameters.get('speed', 1.0)}`, `exaggeration={rec.parameters.get('exaggeration', 0.5)}`, `temp={rec.parameters.get('temperature', 0.7)}`, `cfg={rec.parameters.get('cfg_weight', 0.5)}`
- **Métricas Acústicas**:
  - **Duración**: `{rec.duration_seconds:.2f} s`
  - **Muestreo**: `{rec.sample_rate_hz} Hz`
  - **Tamaño**: `{rec.file_size_bytes} bytes`
  - **SHA-256**: `{rec.audio_sha256[:16]}...`
- **Dispositivo**: `{rec.generator_device}` ({rec.model_name})
- **Ruta**: `{rec.audio_path}`
"""
            new_gen_choices = self.get_generation_choices()
            return rec.audio_path, summary_md, gr.Dropdown(choices=new_gen_choices, value=rec.generation_id)
        except Exception as exc:
            logger.error(f"Generation error: {exc}")
            return None, f"❌ **Error en la síntesis**: {exc}", gr.Dropdown(choices=self.get_generation_choices())

    # -------------------------------------------------------------------------
    # Tab 4: Evaluación Asistida
    # -------------------------------------------------------------------------

    def run_evaluation(
        self,
        audio_target_type: str,
        generation_id: str,
        reference_id: str,
        evaluator_choice: str,
        privacy_consent: bool,
    ) -> str:
        """Run multimodal evaluation adhering strictly to the Privacy Shield."""
        try:
            is_reference = audio_target_type == "Audio de Referencia"
            audio_path: Optional[Path] = None
            audio_id_str: str = ""
            expected_transcript: Optional[str] = None

            if is_reference:
                if not reference_id:
                    return "⚠️ Seleccione un audio de referencia para evaluar."
                ref = self.ref_repo.get_audio_by_id(reference_id)
                if not ref or not ref.local_path:
                    return f"❌ Audio de referencia `{reference_id}` no encontrado o no descargado."
                audio_path = Path(ref.local_path)
                audio_id_str = ref.id
                expected_transcript = ref.transcript
            else:
                if not generation_id:
                    return "⚠️ Seleccione un audio sintético para evaluar."
                gen = self.gen_repo.get_generation_by_id(generation_id)
                if not gen or not gen.audio_path:
                    return f"❌ Generación `{generation_id}` no encontrada."
                audio_path = Path(gen.audio_path)
                audio_id_str = gen.generation_id
                expected_transcript = gen.text

            if not audio_path.exists():
                return f"❌ El archivo de audio `{audio_path}` no existe en disco."

            audio_sha = LocalAudioStorage.calculate_sha256(audio_path)

            evaluator_instance: AudioEvaluator
            if evaluator_choice == "Simulador Offline (Mock)":
                evaluator_instance = MockAudioEvaluator()
            else:
                evaluator_instance = (
                    GeminiAudioEvaluator() if settings.gemini_api_key else MockAudioEvaluator()
                )

            eval_service = EvaluationService(
                evaluator=evaluator_instance,
                allow_reference_upload=privacy_consent,
            )

            evaluation = eval_service.evaluate_audio(
                audio_path=audio_path,
                audio_id=audio_id_str,
                audio_sha256=audio_sha,
                is_reference=is_reference,
                expected_transcript=expected_transcript,
            )

            if not is_reference:
                self.gen_repo.link_evaluation(generation_id, evaluation.evaluation_id)

            is_mock_eval = "mock" in evaluation.evaluator_provider.lower()
            badge = "🔍 EVALUACIÓN GEMINI" if not is_mock_eval else "🧪 SIMULACIÓN OFFLINE (MOCK)"

            return f"""
<div class="aperture-badge">{badge}</div>

### Diagnóstico de Evaluación: `{evaluation.evaluation_id}`

<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 15px 0;">
  <div class="metric-card">
    <div class="metric-value">{evaluation.expressive_intensity:.1f}/5</div>
    <div class="metric-label">Intensidad ({evaluation.perceived_emotion})</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{evaluation.intelligibility_score:.1f}/5</div>
    <div class="metric-label">Claridad / Inteligibilidad</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{evaluation.confidence * 100:.0f}%</div>
    <div class="metric-label">Confianza del Modelo</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{evaluation.perceived_language}</div>
    <div class="metric-label">Idioma Detectado</div>
  </div>
</div>

#### Observaciones y Prosodia
> **Justificación**: {evaluation.explanation or '(Sin justificación)'}
>
> **Notas Prosódicas**: {evaluation.prosody_notes or '(Sin notas adicionales)'}
>
> **Características Vocales**: {evaluation.vocal_characteristics or 'Estándar'}

- **Emoción Primaria**: **{evaluation.perceived_emotion}**
- **Matices Secundarios**: {', '.join(evaluation.secondary_emotions) if evaluation.secondary_emotions else 'Ninguno'}
- **Evaluador**: `{evaluation.evaluator_provider}` ({evaluation.evaluator_model})
- **Hash de Audio Evaluado**: `{evaluation.audio_sha256[:16]}...`
- **Timestamp**: `{evaluation.evaluated_at}`
"""
        except PrivacyPolicyViolationError as priv_err:
            return f"""
<div class="privacy-badge">PRIVACY SHIELD BLOQUEO PREVENTIVO</div>

### 🛡️ Transmisión Bloqueada por Política de Privacidad

{priv_err}

> **Instrucción**: Si desea evaluar audios de referencia protegidos de Portal 2 con Google Gemini, active la casilla de verificación **"Autorizo explícitamente el envío de este audio a Google Gemini"**.
"""
        except Exception as exc:
            logger.error(f"Evaluation error: {exc}")
            return f"❌ **Error en la evaluación**: {exc}"

    # -------------------------------------------------------------------------
    # Tab 5: Historial y Comparación
    # -------------------------------------------------------------------------

    def get_history_dataframe(self) -> list[list[Any]]:
        """Populate table of recorded generations."""
        records = self.gen_repo.list_generations()
        rows = []
        for r in records:
            eval_str = f"{len(r.evaluation_ids)} eval(s)" if r.evaluation_ids else "Sin evaluar"
            speed_val = r.parameters.get("speed", 1.0)
            exag_val = r.parameters.get("exaggeration", 0.5)
            rows.append(
                [
                    r.generation_id,
                    r.created_at[:19].replace("T", " "),
                    r.profile_name,
                    r.text,
                    f"{r.duration_seconds:.2f}s",
                    f"spd={speed_val:.2f}, exag={exag_val:.2f}",
                    r.generator_device,
                    eval_str,
                ]
            )
        return rows

    def compare_two_generations(self, id_a: str, id_b: str) -> tuple[Optional[str], Optional[str], str]:
        """Perform side-by-side comparison between two generated experiments."""
        if not id_a or not id_b:
            return None, None, "Seleccione dos generaciones distintas para comparar."

        rec_a = self.gen_repo.get_generation_by_id(id_a)
        rec_b = self.gen_repo.get_generation_by_id(id_b)

        if not rec_a or not rec_b:
            return None, None, "Una o ambas generaciones seleccionadas no existen."

        audio_a = rec_a.audio_path if Path(rec_a.audio_path).exists() else None
        audio_b = rec_b.audio_path if Path(rec_b.audio_path).exists() else None

        comparison = self.comparison_service.compare_generations([id_a, id_b])

        diff_dur = rec_b.duration_seconds - rec_a.duration_seconds
        dur_sign = "+" if diff_dur > 0 else ""

        md = f"""
### Comparativa Lado a Lado: `{id_a}` vs `{id_b}`

| Atributo | Experimento A ({rec_a.generation_id}) | Experimento B ({rec_b.generation_id}) | Diferencia / Contraste |
| :--- | :--- | :--- | :--- |
| **Perfil** | **{rec_a.profile_name}** | **{rec_b.profile_name}** | {'Mismo perfil' if rec_a.profile_id == rec_b.profile_id else 'Variación de perfil'} |
| **Duración** | `{rec_a.duration_seconds:.2f} s` | `{rec_b.duration_seconds:.2f} s` | `{dur_sign}{diff_dur:.2f} s` |
| **Velocidad (`speed`)** | `{rec_a.parameters.get('speed', 1.0)}` | `{rec_b.parameters.get('speed', 1.0)}` | Variación de tempo |
| **Exageración (`exaggeration`)** | `{rec_a.parameters.get('exaggeration', 0.5)}` | `{rec_b.parameters.get('exaggeration', 0.5)}` | Variación de dinamismo |
| **Texto Base** | *\"{rec_a.text}\"* | *\"{rec_b.text}\"* | {'Texto idéntico' if comparison.has_same_text else 'Textos distintos'} |
| **Dispositivo** | `{rec_a.generator_device}` | `{rec_b.generator_device}` | — |

```text
{comparison.summary_text}
```
"""
        return audio_a, audio_b, md

    def export_bundle_ui(self, target_dir_str: str) -> str:
        """Export audit package from all current generations."""
        records = self.gen_repo.list_generations()
        if not records:
            return "⚠️ No hay experimentos registrados para exportar."

        gen_ids = [r.generation_id for r in records]
        out_path = Path(target_dir_str.strip() or "data/exported_bundle")

        try:
            bundle_dir = self.comparison_service.export_bundle(
                generation_ids=gen_ids,
                destination_dir=out_path,
                include_audio=True,
            )
            return f"✅ **Paquete de auditoría exportado exitosamente** en: `{bundle_dir.resolve()}`\n\nTotal de experimentos incluidos: **{len(gen_ids)}** (manifiesto `manifest.json` y audios copiados)."
        except Exception as exc:
            return f"❌ **Error al exportar paquete**: {exc}"

    # -------------------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------------------

    def build_app(self) -> Any:
        """Construct the complete 5-tab Gradio interface."""
        initial_sections = self.get_section_choices()
        initial_references = self.get_all_reference_choices()
        initial_generations = self.get_generation_choices()

        with gr.Blocks(title="Wheatley Voice Lab — Aperture Science Audio Division") as demo:
            # Header with embedded Aperture styling
            gr.HTML(
                f"""
<style>
{APERTURE_CSS}
</style>
<div class="aperture-header">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <span class="aperture-badge">Aperture Science Experimental Audio Division</span>
      <h1 style="margin: 8px 0 4px 0; color: #f0f6fc; font-size: 1.8rem; font-weight: 800;">
        Wheatley Voice Lab
      </h1>
      <p style="margin: 0; color: #8b949e; font-size: 0.95rem;">
        Banco de pruebas para catalogación de audios de referencia, análisis acústico, síntesis expresiva y evaluación multimodal (Portal 2 / es-ES).
      </p>
    </div>
    <div style="text-align: right;">
      <span class="privacy-badge">Privacy Shield: Activo</span>
      <div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">Host: GTX 1650 (4GB) / Python 3.13</div>
    </div>
  </div>
</div>
"""
            )

            with gr.Tabs():
                # -------------------------------------------------------------
                # TAB 1: Fuente y Adquisición
                # -------------------------------------------------------------
                with gr.Tab("1. Fuente y Adquisición", id="tab_acquisition"):
                    catalog_stats_md = gr.Markdown(self.get_catalog_summary_markdown())

                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Configuración de Descarga Controlada")
                            section_dropdown = gr.Dropdown(
                                label="Sección de la Wiki",
                                choices=initial_sections,
                                value="ALL",
                            )
                            limit_slider = gr.Slider(
                                label="Límite de Audios",
                                minimum=1,
                                maximum=50,
                                value=5,
                                step=1,
                            )
                            dry_run_check = gr.Checkbox(
                                label="Modo Simulación (--dry-run)",
                                value=False,
                                info="Valida enlaces y procedencia sin descargar ficheros.",
                            )
                            force_check = gr.Checkbox(
                                label="Forzar re-descarga (--force)",
                                value=False,
                            )
                            retry_failed_check = gr.Checkbox(
                                label="Reintentar audios con error previo",
                                value=False,
                            )
                            btn_acquire = gr.Button("⬇️ Iniciar Adquisición Controlada", variant="primary")
                            btn_refresh_catalog = gr.Button("🔄 Actualizar Estadísticas")

                        with gr.Column(scale=2):
                            gr.Markdown("### Estado del Lote de Adquisición")
                            acquisition_output_md = gr.Markdown("Presione *Iniciar Adquisición Controlada* para procesar audios.")

                    btn_acquire.click(
                        fn=self.run_acquisition,
                        inputs=[section_dropdown, limit_slider, dry_run_check, force_check, retry_failed_check],
                        outputs=[acquisition_output_md, catalog_stats_md],
                    )

                    btn_refresh_catalog.click(
                        fn=self.get_catalog_summary_markdown,
                        inputs=[],
                        outputs=[catalog_stats_md],
                    )

                # -------------------------------------------------------------
                # TAB 2: Catálogo de Referencias
                # -------------------------------------------------------------
                with gr.Tab("2. Catálogo de Referencias", id="tab_references"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Selección de Audio")
                            ref_filter_sec = gr.Dropdown(
                                label="Filtrar por Sección",
                                choices=initial_sections,
                                value="ALL",
                            )
                            ref_audio_dropdown = gr.Dropdown(
                                label="Audios Descargados Disponibles",
                                choices=initial_references,
                                value=initial_references[0][1] if initial_references else None,
                            )
                            btn_load_ref = gr.Button("🔍 Inspeccionar Audio", variant="primary")

                        with gr.Column(scale=2):
                            ref_audio_player = gr.Audio(label="Reproductor de Audio de Referencia", type="filepath")
                            ref_info_md = gr.Markdown("Seleccione un audio de referencia a la izquierda y presione *Inspeccionar Audio*.")

                    def update_ref_choices(sec: str):
                        new_choices = self.get_downloaded_audio_choices(sec)
                        if new_choices:
                            val = new_choices[0][1]
                            audio_path, md = self.inspect_selected_reference(val)
                            return gr.Dropdown(choices=new_choices, value=val), audio_path, md
                        else:
                            sec_label = sec if sec != "ALL" else "Todas las secciones"
                            empty_md = (
                                f"### ⚠️ No hay audios descargados en esta sección (`{sec_label}`)\n\n"
                                "Actualmente no existen archivos `.wav` descargados localmente para esta sección del doblaje.\n\n"
                                "👉 **Cómo obtenerlos:**\n"
                                "1. Vaya a la pestaña **1. Fuente y Adquisición**.\n"
                                f"2. Seleccione esta sección (`{sec_label}`) en la configuración de descarga.\n"
                                "3. Ajuste el límite deseado y presione **⬇️ Iniciar Adquisición Controlada**."
                            )
                            return gr.Dropdown(choices=[], value=None), None, empty_md

                    ref_filter_sec.change(
                        fn=update_ref_choices,
                        inputs=[ref_filter_sec],
                        outputs=[ref_audio_dropdown, ref_audio_player, ref_info_md],
                    )
                    ref_audio_dropdown.input(
                        fn=self.inspect_selected_reference,
                        inputs=[ref_audio_dropdown],
                        outputs=[ref_audio_player, ref_info_md],
                    )
                    btn_load_ref.click(
                        fn=self.inspect_selected_reference,
                        inputs=[ref_audio_dropdown],
                        outputs=[ref_audio_player, ref_info_md],
                    )

                # -------------------------------------------------------------
                # TAB 3: Laboratorio de Generación
                # -------------------------------------------------------------
                with gr.Tab("3. Laboratorio de Generación", id="tab_generation"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Parámetros de Síntesis")
                            input_text = gr.Textbox(
                                label="Texto a Sintetizar (Español)",
                                value="¡Menos mal que estás bien! Bueno, relativamente bien...",
                                lines=3,
                            )
                            profile_dropdown = gr.Dropdown(
                                label="Perfil Emocional Declarativo",
                                choices=[
                                    "Conversacional",
                                    "Entusiasmado",
                                    "Confundido",
                                    "Enfadado",
                                    "Nervioso",
                                    "Sarcástico",
                                ],
                                value="Conversacional",
                            )

                            profile_desc_md = gr.Markdown()

                            with gr.Accordion("Ajuste Fino de Hiperparámetros", open=True):
                                slider_speed = gr.Slider(label="Velocidad (speed)", minimum=0.5, maximum=2.0, value=1.0, step=0.02)
                                slider_exag = gr.Slider(label="Exageración (exaggeration)", minimum=0.0, maximum=1.5, value=0.25, step=0.05)
                                slider_temp = gr.Slider(label="Temperatura (temperature)", minimum=0.1, maximum=1.5, value=0.65, step=0.05)
                                slider_cfg = gr.Slider(label="Peso CFG (cfg_weight)", minimum=0.0, maximum=1.0, value=0.5, step=0.05)

                            with gr.Accordion("Clonación / Prompt de Voz (Opcional)", open=False):
                                ref_prompt_choices = [("Sin audio prompt", "NONE")] + initial_references
                                prompt_audio_dropdown = gr.Dropdown(
                                    label="Audio de Referencia como Prompt",
                                    choices=ref_prompt_choices,
                                    value="NONE",
                                )

                            btn_synthesize = gr.Button("🎙️ Sintetizar Expresión de Wheatley", variant="primary")

                        with gr.Column(scale=1):
                            gr.Markdown("### Salida Sintética")
                            gen_audio_player = gr.Audio(label="Audio Sintetizado", type="filepath")
                            gen_summary_md = gr.Markdown("Defina los parámetros y presione *Sintetizar Expresión de Wheatley*.")

                    def on_profile_change_handler(prof: str):
                        desc, spd, ex, tmp, cfg, _ = self.on_profile_selected(prof)
                        return (
                            desc,
                            gr.Slider(value=spd),
                            gr.Slider(value=ex),
                            gr.Slider(value=tmp),
                            gr.Slider(value=cfg),
                        )

                    profile_dropdown.change(
                        fn=on_profile_change_handler,
                        inputs=[profile_dropdown],
                        outputs=[profile_desc_md, slider_speed, slider_exag, slider_temp, slider_cfg],
                    )

                # -------------------------------------------------------------
                # TAB 4: Evaluación Asistida
                # -------------------------------------------------------------
                with gr.Tab("4. Evaluación Asistida", id="tab_evaluation"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### Selección de Audio para Evaluación")
                            target_type_radio = gr.Radio(
                                label="Tipo de Audio a Evaluar",
                                choices=["Audio Sintético", "Audio de Referencia"],
                                value="Audio Sintético",
                            )

                            eval_gen_dropdown = gr.Dropdown(
                                label="Experimento Sintético a Evaluar",
                                choices=initial_generations,
                                value=initial_generations[0][1] if initial_generations else None,
                                visible=True,
                            )

                            eval_ref_dropdown = gr.Dropdown(
                                label="Audio de Referencia a Evaluar",
                                choices=initial_references,
                                value=initial_references[0][1] if initial_references else None,
                                visible=False,
                            )

                            evaluator_choice = gr.Radio(
                                label="Motor Evaluador",
                                choices=["Google Gemini (Multimodal)", "Simulador Offline (Mock)"],
                                value="Google Gemini (Multimodal)" if settings.gemini_api_key else "Simulador Offline (Mock)",
                            )

                            gr.Markdown(
                                """
> [!NOTE]
> **Privacy Shield**: Valve Corporation posee los derechos de los audios de Portal 2. La política del laboratorio bloquea el envío de audios de referencia a servicios externos salvo consentimiento explícito.
"""
                            )

                            privacy_checkbox = gr.Checkbox(
                                label="Autorizo explícitamente el envío de este audio a Google Gemini (Privacy Shield Opt-in)",
                                value=False,
                            )

                            btn_evaluate = gr.Button("🔍 Ejecutar Evaluación Perceptiva", variant="primary")

                        with gr.Column(scale=2):
                            eval_result_md = gr.Markdown("Seleccione un audio y presione *Ejecutar Evaluación Perceptiva*.")

                    def on_target_type_changed(choice: str):
                        is_synth = choice == "Audio Sintético"
                        return gr.Dropdown(visible=is_synth), gr.Dropdown(visible=not is_synth)

                    target_type_radio.change(
                        fn=on_target_type_changed,
                        inputs=[target_type_radio],
                        outputs=[eval_gen_dropdown, eval_ref_dropdown],
                    )

                    btn_evaluate.click(
                        fn=self.run_evaluation,
                        inputs=[target_type_radio, eval_gen_dropdown, eval_ref_dropdown, evaluator_choice, privacy_checkbox],
                        outputs=[eval_result_md],
                    )

                # -------------------------------------------------------------
                # TAB 5: Historial y Comparación
                # -------------------------------------------------------------
                with gr.Tab("5. Historial y Comparación", id="tab_comparison"):
                    gr.Markdown("### Historial de Experimentos de Síntesis")
                    history_df = gr.DataFrame(
                        headers=["ID", "Fecha", "Perfil", "Texto", "Duración", "Parámetros", "Dispositivo", "Evaluaciones"],
                        value=self.get_history_dataframe(),
                        interactive=False,
                    )
                    btn_refresh_history = gr.Button("🔄 Actualizar Historial")

                    gr.Markdown("---")
                    gr.Markdown("### Comparación Lado a Lado de Experimentos")
                    with gr.Row():
                        with gr.Column():
                            compare_a_dropdown = gr.Dropdown(
                                label="Experimento A",
                                choices=initial_generations,
                                value=initial_generations[0][1] if initial_generations else None,
                            )
                            player_a = gr.Audio(label="Audio A", type="filepath")

                        with gr.Column():
                            compare_b_dropdown = gr.Dropdown(
                                label="Experimento B",
                                choices=initial_generations,
                                value=initial_generations[1][1] if len(initial_generations) > 1 else (initial_generations[0][1] if initial_generations else None),
                            )
                            player_b = gr.Audio(label="Audio B", type="filepath")

                    btn_compare = gr.Button("⚖️ Comparar Experimentos Seleccionados", variant="primary")
                    comparison_diff_md = gr.Markdown()

                    btn_compare.click(
                        fn=self.compare_two_generations,
                        inputs=[compare_a_dropdown, compare_b_dropdown],
                        outputs=[player_a, player_b, comparison_diff_md],
                    )

                    gr.Markdown("---")
                    gr.Markdown("### Exportación de Paquetes de Auditoría")
                    with gr.Row():
                        export_path_input = gr.Textbox(
                            label="Directorio Destino",
                            value="data/exported_bundle",
                        )
                        btn_export = gr.Button("📦 Exportar Paquete Completo", variant="secondary")
                    export_result_md = gr.Markdown()

                    btn_export.click(
                        fn=self.export_bundle_ui,
                        inputs=[export_path_input],
                        outputs=[export_result_md],
                    )

                    btn_refresh_history.click(
                        fn=self.get_history_dataframe,
                        inputs=[],
                        outputs=[history_df],
                    )

                    btn_synthesize.click(
                        fn=self.synthesize_speech,
                        inputs=[input_text, profile_dropdown, slider_speed, slider_exag, slider_temp, slider_cfg, prompt_audio_dropdown],
                        outputs=[gen_audio_player, gen_summary_md, eval_gen_dropdown],
                    )

        return demo


def launch(host: str = "127.0.0.1", port: int = 7860, share: bool = False, debug: bool = False) -> None:
    """Launch the Gradio application."""
    app = VoiceLabApp()
    demo = app.build_app()
    demo.launch(
        server_name=host,
        server_port=port,
        share=share,
        debug=debug,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wheatley Voice Lab - Interactive Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Server port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Generate public Gradio share link")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    launch(host=args.host, port=args.port, share=args.share, debug=args.debug)

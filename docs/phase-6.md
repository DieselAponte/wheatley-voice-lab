# Fase 6: Servicio de Generación, Persistencia y Comparación

## 1. Estado de la Fase
**COMPLETADA**. Se ha implementado el servicio de orquestación de síntesis (`GenerationService`), la persistencia estructurada e inmutable en disco (`JsonGenerationRepository`), el servicio de comparación sistemática y exportación de paquetes de auditoría (`ComparisonService`), y la herramienta CLI de generación por lotes (`scripts/generate_batch.py`). La suite completa de pruebas cuenta con 29 pruebas unitarias automatizadas pasando exitosamente.

---

## 2. Implementación Realizada

### 2.1 Modelado del Dominio (`src/voice_lab/domain/generation_models.py`)
Se han definido las estructuras tipadas con Pydantic v2 para garantizar trazabilidad e inmutabilidad:
- **`GenerationRecord`**:
  - Identificador único determinista `generation_id` (`gen_<timestamp>_<uuid>`).
  - Texto sintetizado normalizado.
  - Perfil expresivo aplicado (`profile_id`, `profile_name`) y diccionario de hiperparámetros (`speed`, `exaggeration`, `temperature`, `cfg_weight`).
  - Procedencia de clonación: `reference_audio_id` y `reference_audio_path` opcionales.
  - Atributos acústicos técnicos: `audio_path`, `audio_sha256`, `duration_seconds`, `file_size_bytes`, `sample_rate_hz`.
  - Trazabilidad del modelo: `model_name`, `generator_device` (CPU/CUDA), `status`, `error_message`.
  - Evaluaciones vinculadas: lista de `evaluation_ids` y timestamp ISO UTC.
- **`GenerationComparison`**:
  - Agrupación estructurada de múltiples `GenerationRecord`.
  - Banderas analíticas: `has_same_text`, lista de `unique_profiles`, rango de duraciones (`duration_range_seconds`) y resumen textual consolidado.

### 2.2 Repositorio de Persistencia en Disco (`src/voice_lab/infrastructure/persistence/json_generation_repository.py`)
- **Estructura de almacenamiento**: Directorio base `data/generated/`.
- **Inmutabilidad y atomicidad**:
  - Cada generación almacena su par: `data/generated/<gen_id>.wav` y `data/generated/<gen_id>.json`.
  - Índices y listados filtrables por `profile_id` o rango de fechas.
  - Vinculación bidireccional segura con evaluaciones de la Fase 4 mediante `attach_evaluation(generation_id, evaluation_id)`.

### 2.3 Orquestación de Casos de Uso en Aplicación
- **`GenerationService` (`src/voice_lab/application/generation_service.py`)**:
  - Valida el texto de entrada (rechaza cadenas vacías o de longitud inferior a 2 caracteres).
  - Sanitiza el texto y resuelve el perfil emocional correspondiente (o fallback a `conversacional`).
  - Permite sobreescritura de parámetros dentro de los límites seguros declarados en el perfil.
  - Soporta opcionalmente audio de referencia como prompt de clonación acústica.
  - Ejecuta la síntesis a través del contrato `SpeechGenerator`.
  - Calcula el hash SHA-256 de la señal sintetizada y registra métricas técnicas reales.
  - Persiste el registro completo mediante `GenerationRepository`.

- **`ComparisonService` (`src/voice_lab/application/comparison_service.py`)**:
  - Permite contrastar 2 o más generaciones (por ejemplo, mismo texto generado con perfiles *Entusiasmado* vs *Sarcástico* o variaciones de `exaggeration`).
  - Genera resúmenes técnicos estructurados de diferencias de duración y prosodia.
  - **Exportación de Paquetes de Auditoría (`export_audit_bundle`)**:
    - Crea un directorio autónomo o archivado con un `manifest.json`.
    - Copia los audios sintéticos generados, sus metadatos JSON y los audios de referencia vinculados.
    - Facilita la exportación para revisiones externas, benchmarking o archivo histórico sin enlaces rotos por rutas absolutas locales.

### 2.4 Interfaz de Línea de Comandos (`scripts/generate_batch.py`)
Herramienta CLI completa para experimentación por lotes:
- Modos de ejecución:
  - `--profiles`: Lista de perfiles a evaluar secuencialmente (por defecto: `conversacional`, `entusiasmado`, `sarcastico`, `nervioso`).
  - `--text`: Frase personalizada o batería de frases representativas predefinidas de Wheatley.
  - `--reference`: Audio de referencia para clonación o prompt de estilo.
  - `--compare`: Activa la consolidación y reporte de diferencias acústicas entre las variantes generadas.
  - `--export`: Exporta inmediatamente el paquete de auditoría al directorio especificado (`--output-dir`).

---

## 3. Hallazgos y Decisiones Técnicas

1. **Prevención de colisiones en identificadores de generación**:
   - Para evitar colisiones en generaciones de alta velocidad ejecutadas en el mismo segundo, el identificador incorpora `uuid.uuid4().hex[:8]` junto al timestamp (`gen_YYYYMMDD_HHMMSS_<hash>`).
2. **Desacoplamiento de la evaluación**:
   - Las generaciones nacen con una lista vacía de `evaluation_ids`. Cuando el usuario solicita una evaluación posterior con Gemini o Mock, la evaluación se persiste en `data/evaluations/` y su ID se añade atómicamente al archivo JSON del registro de generación, manteniendo la trazabilidad sin regenerar audio.
3. **Paquete de auditoría portátil**:
   - En `export_audit_bundle()`, las rutas en `manifest.json` se normalizan de forma relativa al paquete, garantizando que el paquete exportado pueda trasladarse a otra máquina o subirse a un bucket de almacenamiento sin referencias a la ruta de usuario `c:\Users\veris\...`.

---

## 4. Validación y Evidencia de Ejecución

### 4.1 Suite de Pruebas Automatizadas
Se ejecutaron las pruebas unitarias cubriendo casos límite (textos cortos, fallos de modelo, parámetros fuera de rango, exportación de bundles, consultas por perfil):

```text
tests/unit/test_generation_service.py::test_generate_speech_successful PASSED
tests/unit/test_generation_service.py::test_generate_speech_rejects_empty_text PASSED
tests/unit/test_generation_service.py::test_generate_speech_with_custom_parameters PASSED
tests/unit/test_generation_service.py::test_generate_speech_handles_failure PASSED
tests/unit/test_generation_service.py::test_compare_generations PASSED
tests/unit/test_generation_service.py::test_export_audit_bundle PASSED
============================== 29 passed in 3.67s ==============================
```

### 4.2 Prueba de Generación por Lotes y Exportación Real
Se ejecutó el script `scripts/generate_batch.py`:
- Frase de prueba: *"¡Menos mal que estás bien! Bueno, relativamente bien."*
- Perfiles sintetizados: `conversacional`, `entusiasmado`, `sarcastico`.
- Generaciones creadas y guardadas en `data/generated/`.
- Comparación consolidada con éxito (mismo texto validado, duraciones entre 2.80s y 3.84s).
- Paquete de auditoría exportado y verificado en `data/exported_test/` con `manifest.json` íntegro.

---

## 5. Pasos Siguientes (Hacia Fase 7)
1. **Diseño de la Interfaz Interactiva en Gradio (`src/voice_lab/presentation/gradio_app.py`)**:
   - Organizar las 5 pestañas de trabajo: *Fuente y Adquisición*, *Catálogo de Referencias*, *Laboratorio de Generación*, *Evaluación Asistida* e *Historial y Comparación*.
   - Conectar cada pestaña exclusivamente a los servicios de la capa de aplicación (`AcquisitionService`, `CatalogService`, `GenerationService`, `EvaluationService`, `ComparisonService`).
   - Implementar controles visuales de audio (reproductores, formas de onda y tablas interactivas).
   - Incorporar interruptor de seguridad visual para el Privacy Shield en la pestaña de evaluación.

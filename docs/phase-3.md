# Fase 3: Validación, Inspección Técnica y Preparación del Catálogo de Audio

## 1. Estado de la Fase
**COMPLETADA**. Se ha implementado el analizador acústico determinista con SoundFile y NumPy/Librosa, el generador de derivados no destructivo con resampleo de alta calidad (SOXR), la clasificación de estados de integridad (`VALIDATED` / `INVALID`) y el cálculo de estadísticas de cobertura por sección.

---

## 2. Implementación Realizada

### 2.1 Analizador Acústico Determinista (`src/voice_lab/infrastructure/audio/validation.py`)
- `AudioInspector`:
  - Extracción de propiedades físicas: duración, sample rate, canales y subtype PCM.
  - Mediciones de amplitud: pico lineal y en escala logarítmica dBFS, RMS lineal y dBFS.
  - Detección de clipping digital: disparado si el pico alcanza o supera el umbral de 0.999 (-0.01 dBFS).
  - Detección de silencios: umbral configurado a -50 dBFS para calcular el ratio de silencios y advertir en audios anómalos.
  - Separación conceptual estricta: las mediciones son puramente físicas y acústicas; no se infieren emociones a partir de la amplitud.
  - Modelo tipado `AudioTechnicalProfile` con advertencias (`warnings`) y estado `is_valid`.

### 2.2 Gestor de Derivados (`src/voice_lab/infrastructure/audio/processing.py`)
- `AudioProcessor`:
  - **Inmutabilidad de fuentes**: Los archivos originales de referencia nunca se sobrescriben.
  - **Generación de derivados**: Conversión a formatos requeridos por modelos TTS (ej. 24,000 Hz, mono, 16 bits PCM) con resampleo SOXR de alta calidad.
  - **Trazabilidad**: Genera `DerivativeMetadata` registrando el hash, transformación aplicada, perfil técnico original y perfil técnico resultante.

### 2.3 Servicio de Catálogo y Estadísticas (`src/voice_lab/application/catalog_service.py`)
- `CatalogService`:
  - Inspección unitaria y por lote de todos los audios descargados en el repositorio.
  - Actualización de estado en el catálogo a `VALIDATED` (o `INVALID` si no es decodificable).
  - Generación del reporte `CatalogStatisticsSummary` con desglose por cada una de las secciones (descubiertos, descargados, validados, inválidos y duración acumulada).

---

## 3. Hallazgos Técnicos de la Inspección Acústica
- **Propiedades de las referencias de Portal Wiki**:
  - Sample rate: 44,100 Hz (mono).
  - Formato: WAV PCM de 16 bits.
  - Rango dinámico y compresión: Las líneas de Wheatley presentan un procesado original de radio/intercomunicador con ecualización de paso banda y compresión de dinámica, con picos cercanos a -1.0 dBFS pero sin clipping digital destructivo.
- **Validación de audios de muestra descargados**:
  - `Wheatley_openinghello01_es.wav`: 1.85s, 44.1 kHz, 1 canal, estado `VALIDATED`.
  - `Wheatley_openinghello12_es.wav`: 0.78s, 44.1 kHz, 1 canal, estado `VALIDATED`.
  - `Wheatley_openinghello13_es.wav`: 3.19s, 44.1 kHz, 1 canal, estado `VALIDATED`.
  - `Wheatley_openinghello15_es.wav`: 1.46s, 44.1 kHz, 1 canal, estado `VALIDATED`.
  - Duración total acumulada validada: **7.29 segundos**.

---

## 4. Pruebas y Evidencia de Verificación

```powershell
# 1. Ejecución de la suite completa de pruebas unitarias
.\.venv\Scripts\pytest.exe -v tests/
# Resultado: 17 passed in 3.27s (incluyendo clipping, silencios, archivos vacíos y derivados)

# 2. Validación y estadísticas sobre el catálogo real
.\.venv\Scripts\python.exe -c "from src.voice_lab.infrastructure.config.settings import settings; from src.voice_lab.infrastructure.persistence.json_reference_repository import JsonReferenceRepository; from src.voice_lab.application.catalog_service import CatalogService; repo = JsonReferenceRepository(settings.data_dir / 'metadata' / 'discovery_catalog.json'); service = CatalogService(repo); print(service.validate_catalog()); print(service.get_statistics().total_duration_seconds)"
# Resultado: {'total_processed': 4, 'validated': 4, 'invalid': 0}, 7.29 segundos
```

---

## 5. Pasos Siguientes e Información Útil (Fase 4)
1. **Contrato de evaluación desacoplado (`AudioEvaluator`)**:
   - Definir esquema Pydantic para observaciones estructuradas (transcripción estimada, idioma/dialecto percibido, expresión/emoción percibida, prosodia, inteligibilidad, incertidumbre, modelo y versión de prompt).
2. **Adaptador para Gemini (`GeminiAudioEvaluator`)**:
   - Usar el SDK oficial `google-genai` (`client = genai.Client()`).
   - Clave API leída exclusivamente de variables de entorno.
3. **Control de privacidad estricto**:
   - Por defecto, `allow_reference_external_eval = False`. Bloquear el envío de referencias originales a servidores externos salvo que el usuario lo habilite conscientemente.
4. **Caché y Mocks**:
   - Sistema de caché persistente indexado por hash del audio + modelo + versión del prompt.
   - Modo de simulación mock para pruebas deterministas sin consumo de cuota ni dependencia de API keys.

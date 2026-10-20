# Fase 2: Descarga Controlada y Organización de los Audios de Referencia

## 1. Estado de la Fase
**COMPLETADA**. Se ha implementado el servicio de descarga resiliente e idempotente, el gestor de almacenamiento jerárquico sanitizado para Windows/Linux, el cálculo y validación de sumas de verificación SHA-256, el reemplazo atómico mediante archivos `.tmp`, el control de tamaño máximo, el modo de simulación (`--dry-run`) y la herramienta CLI de adquisición selectiva.

---

## 2. Implementación Realizada

### 2.1 Almacenamiento Jerárquico en Disco (`src/voice_lab/infrastructure/audio/storage.py`)
- `LocalAudioStorage`:
  - Sanitización de rutas y nombres de ficheros para evitar errores en Windows con caracteres prohibidos (`:`, `*`, `?`, `"`, `<`, `>`, `|`) o directorios anidados inválidos.
  - Generación determinista de rutas relativas: `data/references/<capitulo>/<subseccion>/<filename>.wav`.
  - Verificación de presencia y tamaño real en disco.
  - Cálculo de hash SHA-256 para integridad de datos.

### 2.2 Servicio de Adquisición (`src/voice_lab/application/acquisition_service.py`)
- `AcquisitionService`:
  - **Idempotencia**: Si el archivo ya existe en disco y su hash SHA-256 coincide con el registrado en el catálogo, la descarga se omite automáticamente.
  - **Descarga atómica**: Los archivos se descargan en un fichero temporal `.tmp`. Solo si la descarga finaliza con éxito, no está vacía y no supera `max_download_bytes` (25 MB), se reemplaza atómicamente la ruta final. Si ocurre cualquier error, el temporal se destruye para no dejar archivos corruptos.
  - **Trazabilidad**: Actualiza `checksum_sha256`, `file_size_bytes`, `acquired_at` (ISO 8601 UTC), `local_path` y `status = DOWNLOADED` en el catálogo persistido.
  - **Filtrado flexible**: Permite seleccionar por capítulo (`section_id`), lista de IDs de audio (`audio_ids`), reintentar fallidos (`retry_failed`), forzar re-descarga (`force`) o limitar la cantidad (`limit`).
  - **Modo Dry-Run**: Muestra la ruta de destino y la URL de origen sin realizar transferencias HTTP.

### 2.3 Script CLI (`scripts/acquire_references.py`)
- Herramienta de línea de comandos para operadores y desarrollo.
- Protegida contra descargas masivas involuntarias: si no se especifica `--all`, `--section` o `--audio-id`, aplica un límite de cortesía de 5 archivos.

---

## 3. Hallazgos Técnicos de la Descarga
- **Respeto a los servidores de Portal Wiki**: El cliente aplica un retardo de 1.5 segundos entre peticiones (`HTTP_REQUEST_DELAY_SECONDS`) y cabeceras descriptivas.
- **Formato real de audios**: Los archivos `.wav` de Portal Wiki tienen una frecuencia de muestreo estándar de 44.1 kHz, 16 bits PCM (mono). Su tamaño típico varía entre 50 KB y 400 KB por frase.
- **Estructura en disco verificada**:
  - `data/references/capitulo-1-despertares/introduccion/antes-de-abrir-la-puerta/Wheatley_openinghello01_es.wav`
  - `data/references/capitulo-1-despertares/introduccion/antes-de-abrir-la-puerta/Wheatley_openinghello12_es.wav`
- **Exclusión en Git**: Los ficheros binarios `.wav` quedan automáticamente ignorados por `.gitignore`, preservando únicamente los metadatos en `data/metadata/discovery_catalog.json`.

---

## 4. Pruebas y Evidencia de Verificación

```powershell
# 1. Pruebas unitarias completas con MockTransport (sin red externa)
.\.venv\Scripts\pytest.exe -v tests/
# Resultado: 11 passed in 0.95s

# 2. Simulación de adquisición con Dry-Run
.\.venv\Scripts\python.exe scripts/acquire_references.py --dry-run --limit 3
# Resultado: 3 candidatos evaluados, 0 bytes descargados, rutas validadas.

# 3. Descarga controlada real de prueba
.\.venv\Scripts\python.exe scripts/acquire_references.py --limit 2
# Resultado: 2 audios descargados, SHA-256 calculados, estado persistido.

# 4. Comprobación de idempotencia
.\.venv\Scripts\python.exe scripts/acquire_references.py --audio-id ref_wheatley-openinghello01-es
# Resultado: 0 descargas necesarias (ya descargado y verificado).
```

---

## 5. Pasos Siguientes e Información Útil (Fase 3)
1. **Analizador acústico y técnico (`AudioInspector`)**:
   - Integrar `soundfile` y `librosa` para calcular duración exacta, frecuencia de muestreo, número de canales, pico de amplitud, clipping (> -0.1 dBFS), silencios anómalos y nivel RMS.
   - Detectar archivos truncados, vacíos o no decodificables.
2. **Estados del catálogo y derivados**:
   - Clasificar recursos en `VALID`, `INVALID` o `WARNING`.
   - Generar derivados identificables (ej. remuestreo a 24 kHz mono si el modelo TTS lo requiere) sin alterar el archivo original.
   - Generar reporte estadístico de cobertura por sección.

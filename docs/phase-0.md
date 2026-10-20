# Fase 0: Auditoría del Repositorio y Planificación

## 1. Estado de la Fase
**COMPLETADA**. Se ha realizado la auditoría técnica completa del entorno de ejecución, hardware, software, dependencias instaladas en `.venv` y herramientas en PATH, estableciendo la arquitectura modular y las pautas de conservación del entorno existente.

---

## 2. Diagnóstico del Entorno de Ejecución

### 2.1 Hardware y Acelerador
- **Sistema Operativo**: Windows 11 Home / Pro (10.0.22631, AMD64).
- **GPU**: NVIDIA GeForce GTX 1650 (4096 MiB / 4 GB VRAM, driver 610.88, CUDA 13.3).
- **Memoria VRAM Libre en Reposo**: ~3.1 GB.
- **Implicación de Hardware**:
  - La VRAM es insuficiente para fine-tuning o entrenamiento completo de modelos TTS de difusión de 500M parámetros (requeriría >= 16 GB).
  - La inferencia debe incorporar fallback automático en CPU (`device = "cpu"`) si la VRAM libre es inferior a 5.0 GB para garantizar estabilidad y evitar fallos CUDA Out of Memory (OOM).

### 2.2 Intérprete y Entorno Virtual
- **Intérprete**: Python 3.13.12 (64-bit).
- **Entorno Virtual**: `.venv` preexistente en la raíz del repositorio.
- **Decisión de Conservación**: Se mantiene estrictamente el entorno virtual existente en lugar de forzar recreaciones con Python 3.11 o gestores alternativos, preservando las dependencias funcionales ya instaladas.

### 2.3 Diagnóstico de Dependencias Instaladas (16 bibliotecas verificadas)
| Paquete | Versión | Estado de Verificación |
| :--- | :--- | :--- |
| `httpx` | 0.28.1 | Operativo (cliente HTTP asíncrono/síncrono) |
| `beautifulsoup4` | 4.15.0 | Operativo (parser de DOM HTML de la wiki) |
| `pydantic` | 2.14.1 | Operativo (modelado estricto y validación de esquemas) |
| `pydantic-settings` | 2.16.0 | Operativo (configuración centralizada vía `.env`) |
| `soundfile` | 0.14.0 | Operativo (libsndfile: 26 formatos soportados nativamente) |
| `librosa` | 1.0.0 | Operativo (extracción de métricas espectrales y resampling) |
| `numpy` | 2.5.4 | Operativo (procesamiento numérico de señales) |
| `google-genai` | 2.31.0 | Operativo (SDK oficial para Gemini 2.5 Flash) |
| `gradio` | 6.30.0 | Operativo (framework para la UI web interactiva) |
| `ruff` | 0.17.1 | Operativo (linter y formateador ultrarrápido) |
| `mypy` | 2.4.0 | Operativo (verificación estática de tipos) |
| `pytest` | 9.1.1 | Operativo (ejecutor de pruebas unitarias y de integración) |

### 2.4 Binarios en PATH del Sistema
- `git`: Presente (`C:\Program Files\Git\cmd\git.EXE`).
- `ffmpeg` / `ffprobe`: Ausentes en PATH del sistema. Mitigación: El laboratorio opera nativamente con `soundfile` para archivos WAV, FLAC y OGG.
- `uv`: Ausente en PATH del sistema. Mitigación: Uso del entorno virtual estándar `.venv`.

---

## 3. Decisiones Arquitectónicas y Configuración

1. **Arquitectura Hexagonal (Puertos y Adaptadores)**:
   - Capa de Dominio: pura, tipada con Pydantic v2, cero dependencias de UI o redes.
   - Capa de Aplicación: orquestación de casos de uso desacoplados.
   - Capa de Infraestructura: implementaciones concretas para HTTP, audio, persistencia y modelos.
   - Capa de Presentación: interfaz interactiva Gradio delegando 100% en la capa de aplicación.
2. **Plantilla de Entorno Versionada (`.env.example`)**:
   - Creación de `.env.example` sincronizado con todas las variables requeridas (claves de API, directorios de almacenamiento, parámetros de red y límites).
3. **Política Privacy Shield**:
   - Inclusión de directriz preventiva `ALLOW_REFERENCE_EXTERNAL_EVAL = False` para proteger la propiedad intelectual de Valve Corporation sobre los audios de Portal 2.

---

## 4. Pasos Siguientes
- Iniciar la **Fase 1**: Modelado del dominio en Pydantic y desarrollo del cliente y parser de la wiki de Portal.

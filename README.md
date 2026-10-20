# Wheatley Voice Lab

Laboratorio experimental local en Python para la catalogación de audios de referencia, análisis acústico y perceptivo, síntesis de voz expresiva y comparación interactiva de resultados, tomando como sujeto de estudio al personaje Wheatley de *Portal 2* (centrado en su doblaje al español de España).

---

## 1. Objetivo, Alcance y Exclusiones del MVP

### 1.1 Objetivo General
Desarrollar un banco de pruebas modular, auditable y extensible para evaluar la viabilidad de modelos de síntesis de voz neural (específicamente la familia Chatterbox para español de España) en la reproducción de estilos expresivos complejos (prosodia errática, nerviosismo, sarcasmo, entusiasmo desmedido), asistido por evaluación acústica determinista y evaluación multimodal mediante la API de Google Gemini.

### 1.2 Alcance del MVP (Fases 0 a 8)
- **Adquisición jerárquica**: Scraping respetuoso y estructurado de la wiki de Portal (`https://theportalwiki.com/wiki/Wheatley_voice_lines/es`), preservando la organización original por capítulos, subsecciones, anclas y textos asociados.
- **Descarga controlada**: Servicio de descarga idempotente, con limitación de frecuencia (rate limiting), reintentos con backoff, verificación de integridad SHA-256 y registro de procedencia.
- **Inspección técnica de audio**: Diagnóstico acústico determinista (duración, sample rate, canales, clipping, RMS, silencios) mediante SoundFile y Librosa sin modificar archivos originales.
- **Evaluación asistida por IA**: Contrato agnóstico `AudioEvaluator` con implementación para Google Gemini (SDK `google-genai`), con control explícito de privacidad (opt-in para audios de referencia) y caché persistente.
- **Síntesis expresiva**: Adaptador `SpeechGenerator` para Chatterbox, con perfiles expresivos declarativos validados (Conversacional, Entusiasmado, Confundido, Enfadado, Nervioso, Sarcástico).
- **Persistencia y comparación**: Catálogo e historial basados en esquemas JSON versionados con metadatos reproducibles.
- **Interfaz interactiva**: Dashboard local en Gradio desacoplado de la lógica de negocio, estructurado en pestañas de trabajo.

### 1.3 Exclusiones Explícitas del MVP
- Entrenamiento o fine-tuning de modelos TTS desde cero.
- Arquitectura cliente-servidor distribuida o multiusuario.
- Autenticación, control de accesos o gestión de cuentas de usuario.
- Bases de datos relacionales pesadas o brokers de mensajería (Redis, Celery, PostgreSQL).
- Despliegue en producción o ejecución desatendida en la nube sin supervisión de costes.
- Publicación o redistribución automática de audios protegidos por derechos de autor.

---

## 2. Arquitectura y Estructura del Proyecto

### 2.1 Estilo Arquitectónico
El proyecto sigue el patrón de **Monolito Modular** con principios de **Puertos y Adaptadores (Arquitectura Hexagonal)**:
- **Capa de Dominio (`src/voice_lab/domain`)**: Entidades de datos puras, modelos Pydantic, definiciones de perfiles y contratos abstractos (`Protocol` / `ABC`). Cero dependencias de Gradio, SDKs de red o bibliotecas de inferencia.
- **Capa de Aplicación (`src/voice_lab/application`)**: Servicios de orquestación de casos de uso (adquisición, análisis, evaluación, generación y comparación).
- **Capa de Infraestructura (`src/voice_lab/infrastructure`)**: Implementaciones concretas de contratos: clientes HTTP (httpx), parsers HTML (BeautifulSoup4), procesamiento de audio (soundfile, librosa), conectores de IA (google-genai), adaptadores de síntesis (chatterbox) y persistencia JSON.
- **Capa de Presentación (`src/voice_lab/presentation`)**: Interfaz gráfica en Gradio que consume exclusivamente los servicios de la capa de aplicación.

### 2.2 Estructura de Directorios Prevista

```text
wheatley-voice-lab/
├── .env.example                  # Plantilla de variables de entorno (versionada)
├── .gitignore                    # Reglas de exclusión para Git
├── LLM-Context.md                # Especificación funcional y técnica de referencia
├── README.md                     # Documentación técnica viva del proyecto
├── requirements.txt              # Especificación declarativa de dependencias
├── configs/                      # Configuraciones declarativas (perfiles, parámetros)
│   ├── settings.toml             # Parámetros de ejecución generales
│   └── emotion_profiles.json     # Perfiles expresivos y rangos validados
├── data/                         # Almacenamiento local (ignorado en Git excepto metadatos)
│   ├── metadata/                 # Catálogos maestros en JSON
│   ├── references/               # Audios de referencia adquiridos
│   ├── generated/                # Muestras sintéticas generadas
│   └── evaluations/              # Resultados estructurados de evaluación
├── scripts/                      # Comandos CLI y utilidades auxiliares
│   ├── inspect_source.py         # Inspección y descubrimiento de la fuente
│   ├── acquire_references.py     # Descargador selectivo/masivo
│   ├── evaluate_audio.py         # Evaluación de audio mediante API
│   └── generate_batch.py         # Generación de voz por lotes
├── src/
│   └── voice_lab/
│       ├── __init__.py
│       ├── domain/               # Entidades, contratos y perfiles
│       ├── application/          # Servicios de orquestación de casos de uso
│       ├── infrastructure/       # Adaptadores de red, audio, modelos y persistencia
│       └── presentation/         # Aplicación interactiva Gradio
└── tests/                        # Suite de pruebas automatizadas
    ├── fixtures/                 # Muestras HTML y audios sintéticos de prueba
    ├── unit/                     # Pruebas unitarias aisladas
    ├── integration/              # Pruebas de integración de componentes
    └── conftest.py               # Configuración global y fixtures de pytest
```

---

## 3. Tecnologías y Dependencias Verificadas

### 3.1 Entorno de Ejecución Diagnosticado (Fase 0)
- **Sistema Operativo**: Windows 11 Home / Pro (10.0.22631, AMD64).
- **Intérprete Python**: Python 3.13.12 (tags/v3.13.12:1cbe481, MSC v.1944 64 bit).
- **Entorno Virtual**: Directorio `.venv` preexistente en la raíz del proyecto.
- **Control de Versiones**: Git 2.x instalado en el sistema (`C:\Program Files\Git\cmd\git.EXE`). Repositorio inicializado en rama `main`.
- **Hardware de Aceleración**:
  - GPU: NVIDIA GeForce GTX 1650 (4096 MiB VRAM / 4 GB VRAM, modo WDDM).
  - Driver NVIDIA: 610.88 | Compatibilidad CUDA UMD: 13.3.
  - Memoria VRAM libre en reposo: ~3.1 GB.

### 3.2 Matriz de Bibliotecas Instaladas y Comprobadas en `.venv`

| Paquete | Versión Instalada | Propósito en el Proyecto | Estado de Verificación |
| :--- | :--- | :--- | :--- |
| `httpx` | 0.28.1 | Cliente HTTP asíncrono/síncrono para adquisición | Importación y API verificada |
| `beautifulsoup4` | 4.15.0 | Parser HTML y navegación del DOM de la wiki | Importación y API verificada |
| `pydantic` | 2.14.1 | Modelado tipado de datos y validación de esquemas | Importación y API verificada |
| `pydantic-settings` | 2.16.0 | Gestión centralizada de configuración mediante `.env` | Importación y API verificada |
| `soundfile` | 0.14.0 | Lectura/escritura de audio (libsndfile: 26 formatos) | Formatos y backend verificados |
| `librosa` | 1.0.0 | Extracción de características acústicas (RMS, espectro) | Importación y API verificada |
| `numpy` | 2.5.4 | Manipulación numérica de señales y arrays | Importación y API verificada |
| `scipy` | 1.18.1 | Procesamiento de señales y filtros | Importación y API verificada |
| `gradio` | 6.30.0 | Interfaz de usuario interactiva | Componentes Blocks y Audio verificados |
| `python-dotenv` | 1.2.4 | Carga de variables de entorno locales | Importación y API verificada |
| `google-genai` | 2.31.0 | SDK oficial de Google Gemini (`genai.Client`) | Clientes y tipos verificados |
| `tenacity` | 9.1.4 | Políticas de reintentos y resiliencia ante caídas HTTP | Importación y API verificada |
| `pytest` | 9.1.1 | Framework de pruebas automatizadas | Ejecución de CLI verificada |
| `pytest-cov` | 7.1.0 | Medición de cobertura de pruebas | Ejecución verificada |
| `ruff` | 0.17.1 | Linter y formateador ultrarrápido | Ejecución de CLI verificada |
| `mypy` | 2.4.0 | Verificación estática de tipos | Ejecución de CLI verificada |

### 3.3 Utilidades y Componentes Pendientes o Ausentes

| Componente | Estado | Impacto Técnico | Solución Planificada |
| :--- | :--- | :--- | :--- |
| `ffmpeg` / `ffprobe` | No encontrado en PATH | Decodificación restringida a formatos nativos de `soundfile` (WAV, FLAC, OGG). No se pueden transcodificar formatos privativos o contenedores complejos vía CLI. | Utilizar WAV/OGG nativos para referencias y derivados; documentar FFmpeg como prerrequisito opcional del sistema. |
| `uv` | No encontrado en PATH | El documento `LLM-Context.md` contemplaba `uv` y `pyproject.toml`, pero el proyecto fue inicializado con `venv` tradicional y `requirements.txt`. | Respetar la regla de no alterar el entorno; gestionar dependencias mediante `requirements.txt` y `pip` dentro de `.venv`. |
| `torch` / `torchaudio` | No instalado en `.venv` | Requisito fundamental para la ejecución de modelos de síntesis de voz locales (Chatterbox). | Evaluar instalación controlada de PyTorch compatible con Python 3.13 en Fase 5. |
| `chatterbox` / `chatterbox-tts` | No instalado en `.venv` | La biblioteca de síntesis no está presente en el entorno actual. | Definir adaptador abstracto en Fase 1-4; instalar e integrar la versión adecuada en Fase 5 verificando compatibilidad de hardware. |

---

## 4. Configuración del Entorno y Variables

El archivo `.env.example` contiene la plantilla declarativa de variables soportadas por el sistema. Para su uso local:

1. Copiar `.env.example` a `.env` (archivo excluido del control de versiones).
2. Asignar los valores requeridos según el entorno local.

```bash
# Variables del proveedor de evaluación asistida (Gemini)
GEMINI_API_KEY=                   # Clave de API de Google AI Studio (obligatoria para Fase 4)
GEMINI_MODEL=gemini-2.5-flash     # Modelo por defecto para análisis multimodal de audio

# Rutas de almacenamiento local
DATA_DIR=data                     # Directorio raíz de datos
REFERENCE_DIR=data/references     # Directorio para audios descargados de referencia
GENERATED_DIR=data/generated      # Directorio para audios sintéticos generados
EVALUATION_DIR=data/evaluations   # Directorio para evaluaciones estructuradas

# Parámetros del servicio de adquisición
SOURCE_BASE_URL=https://theportalwiki.com/wiki/Wheatley_voice_lines/es
HTTP_TIMEOUT_SECONDS=30           # Tiempo límite por solicitud HTTP
HTTP_REQUEST_DELAY_SECONDS=1.5    # Pausa de cortesía entre peticiones sucesivas
MAX_DOWNLOAD_BYTES=25000000       # Tamaño máximo admitido por archivo (25 MB)
MAX_RETRIES=3                     # Reintentos máximos para fallos transitorios
LOG_LEVEL=INFO                    # Nivel de logging (DEBUG, INFO, WARNING, ERROR)
```

---

## 5. Estado de Ejecución por Fases

| Fase | Denominación | Estado | Entregables Principales |
| :---: | :--- | :---: | :--- |
| **0** | **Auditoría del repositorio y planificación** | **COMPLETADA** | Auditoría técnica de hardware/software, diagnóstico de dependencias, matriz de requisitos, creación de `.env.example` y `README.md` evolutivo. |
| **1** | **Modelado del dominio y adquisición de estructura** | **COMPLETADA** | Modelos Pydantic v2, contratos de repositorio, cliente HTTP resiliente con tenacity, parser BeautifulSoup4 de ToC y audios, tests offline y CLI inspect. |
| **2** | **Descarga controlada y organización jerárquica** | **COMPLETADA** | Downloader resiliente con rate-limit, SHA-256, jerarquía de directorios por capítulo, modo dry-run y persistencia JSON. |
| **3** | **Validación, inspección técnica y catálogo** | **COMPLETADA** | Analizador acústico determinista (SoundFile/Librosa), estados de integridad, derivados inmutables y estadísticas por sección. |
| **4** | Evaluación expresiva con Gemini API | *Pendiente* | Contrato `AudioEvaluator`, adaptador para `google-genai`, control de consentimiento para envío de referencias, caché y pruebas con mocks. |
| **5** | Integración de Chatterbox y perfiles expresivos | *Pendiente* | Diagnóstico de API de Chatterbox, gestión de recursos GPU/CPU (GTX 1650), definición de perfiles JSON y generación base. |
| **6** | Servicio de generación, persistencia y comparación | *Pendiente* | Orquestación de casos de uso, persistencia de metadatos de generación, historial reproducible y exportación selectiva. |
| **7** | Interfaz interactiva con Gradio | *Pendiente* | UI con 5 pestañas conectadas a servicios de aplicación, sin lógica de negocio en la vista y con indicadores claros de estado. |
| **8** | Integración final, calidad, seguridad y cierre | *Pendiente* | Validación E2E de flujos A, B, C y D, suite completa de pruebas, verificación de seguridad y matriz de aceptación. |

---

## 6. Funcionalidades: Matriz de Implementación

- [x] **Auditoría de entorno y dependencias**: Diagnóstico de Python 3.13, GPU GTX 1650, bibliotecas instaladas y compatibilidad de herramientas.
- [x] **Especificación y documentación evolutiva**: Creación de `README.md` técnico y consolidación de `.env.example`.
- [x] **Modelos de dominio tipados**: Entidades `ReferenceSection`, `ReferenceAudio`, `AssetProvenance`, `SourcePage`, `DiscoveryCatalog` en Pydantic v2.
- [x] **Parser de Portal Wiki**: Extracción de ToC, jerarquía de 92 capítulos/subsecciones y 823 URLs de audio asociadas.
- [x] **Pruebas unitarias de adquisición**: Pruebas offline mediante fixtures HTML locales con 100% de éxito.
- [x] **Descargador resiliente con rate-limiting**: Gestión de reintentos, validación de contenido, modo dry-run y cálculo SHA-256.
- [x] **Organización jerárquica de ficheros**: Estructura de carpetas en disco reflejando los capítulos sanitizados para Windows.
- [x] **Analizador acústico determinista**: Extracción de duración, frecuencia, canales, RMS, silencios, clipping y gestión de derivados.
- [ ] **Adaptador de evaluación Gemini**: Integración con el SDK `google-genai` con esquemas estructurados de prosodia y transcripción.
- [ ] **Control de privacidad de referencias**: Mecanismo de bloqueo por defecto antes de transmitir audios protegidos a la API externa.
- [ ] **Adaptador de síntesis Chatterbox**: Envoltorio sobre Chatterbox Multilingual (es-ES) con soporte para aceleración o CPU fallback.
- [ ] **Catálogo de perfiles expresivos**: Configuración declarativa con rangos validados para los estilos requeridos.
- [ ] **Servicio de orquestación de generación**: Generación individual y por lotes con persistencia de parámetros reproducibles.
- [ ] **Historial y comparador de experimentos**: Comparación lado a lado de frases sintéticas bajo distintos perfiles y parámetros.
- [ ] **Dashboard interactivo Gradio**: Navegación de catálogo, generación en vivo, evaluación y comparación.

---

## 7. Comandos Verificados en el Entorno

Los siguientes comandos han sido probados y validados en el entorno activo:

```powershell
# 1. Verificación del intérprete Python del entorno virtual
.\.venv\Scripts\python.exe --version
# Salida: Python 3.13.12

# 2. Comprobación de herramientas de calidad
.\.venv\Scripts\ruff.exe --version
# Salida: ruff 0.17.1

.\.venv\Scripts\mypy.exe --version
# Salida: mypy 2.4.0 (compiled: yes)

.\.venv\Scripts\pytest.exe --version
# Salida: pytest 9.1.1

# 3. Comprobación del acelerador de hardware (GPU)
nvidia-smi
# Salida: NVIDIA GeForce GTX 1650, Driver 610.88, CUDA 13.3

# 4. Estado del repositorio Git
git status
# Salida: On branch main
```

---

## 8. Decisiones Técnicas y Justificaciones

1. **Conservación estricta del entorno virtual existente (`.venv`)**:
   - *Decisión*: Se mantiene el entorno Python 3.13.12 creado por el usuario en lugar de forzar la recreación con Python 3.11 y `uv` sugerida en el borrador preliminar de `LLM-Context.md`.
   - *Justificación*: Evita alterar el entorno local del usuario y previene la reinstalación destructiva de dependencias funcionales (Gradio, Librosa, Google-GenAI, Pydantic, etc.).
2. **Creación de `.env.example` sincronizado**:
   - *Decisión*: Se extrajeron las variables de configuración de `LLM-Context.md` y `.env` para crear `.env.example` en el repositorio.
   - *Justificación*: Permite el seguimiento de la plantilla de configuración en Git sin arriesgar la exposición accidental de claves de API en `.env`.
3. **Desacoplamiento estricto de adaptadores de síntesis y evaluación**:
   - *Decisión*: El dominio y la aplicación solo interactuarán con contratos abstractos (`SpeechGenerator` y `AudioEvaluator`).
   - *Justificación*: Facilita probar componentes mediante simulaciones (mocks/fakes), permite cambiar de proveedor de IA sin reescribir la lógica del laboratorio y aísla las particularidades de Chatterbox y Gemini.
4. **Protección preventiva de privacidad en llamadas externas**:
   - *Decisión*: La evaluación de audios de referencia mediante Gemini estará inhabilitada por defecto en la configuración hasta que el usuario la active conscientemente.
   - *Justificación*: Cumple con los principios de uso responsable de datos, evita consumo innecesario de cuota y protege audios de referencia de transmisiones no deseadas a servidores externos.

---

## 9. Limitaciones Conocidas, Riesgos y Problemas Abiertos

1. **Disponibilidad de PyTorch y Chatterbox en Python 3.13 en Windows**:
   - *Riesgo*: Los paquetes de Deep Learning (`torch`, `torchaudio`, `chatterbox-tts`) históricamente publican primero ruedas precompiladas para versiones estables anteriores (3.10-3.12).
   - *Mitigación*: En la Fase 5 se investigará la disponibilidad de ruedas oficiales de PyTorch para Windows AMD64 en Python 3.13. De no haber soporte directo, se evaluará la alternativa técnica más limpia sin desestabilizar el entorno actual.
2. **Capacidad de Memoria de Video (VRAM de 4 GB en GTX 1650)**:
   - *Riesgo*: Modelos de difusión de voz o transformadores de ~500M parámetros pueden exceder los ~3.1 GB de VRAM disponibles al cargar pesos y tensores de atención, provocando un error CUDA Out of Memory (OOM).
   - *Mitigación*: El adaptador de Chatterbox deberá contemplar inferencia en modo CPU como fallback configurable, así como control estricto del ciclo de vida del modelo en memoria.
3. **Ausencia de binarios FFmpeg en PATH**:
   - *Riesgo*: Archivos que utilicen contenedores MP3 o códecs propietarios no podrán ser procesados mediante SoundFile si no están soportados por libsndfile.
   - *Mitigación*: El catálogo de Portal Wiki aloja principalmente archivos `.wav` y `.ogg`, ambos soportados nativamente por `soundfile` 0.14.0 (26 formatos soportados). Se notificará al usuario si se requiere FFmpeg para formatos adicionales.

---

## 10. Procedencia de las Fuentes y Consideraciones de Uso

- **Fuente Primaria**: `https://theportalwiki.com/wiki/Wheatley_voice_lines/es`
- **Sujeto de Estudio**: Líneas de voz del personaje Wheatley de *Portal 2* (Valve Corporation), doblado al español de España.
- **Régimen de Derechos**: Los audios enlazados en Portal Wiki son propiedad de Valve Corporation y sus respectivos actores de doblaje. La licencia general del texto de la wiki no se transfiere a los archivos multimedia enlazados.
- **Uso Exclusivo en el Laboratorio**: El material se adquiere únicamente como referencia analítica privada para experimentación local de procesamiento y comparación fonética.
- **Restricciones de Distribución**: Los archivos descargados están excluidos de los commits (`.gitignore`) y la aplicación no publicará, empaquetará ni redistribuirá audios de referencia a repositorios ni a servicios públicos.

---

## 11. Registro de Cambios por Fase

### Fase 0: Auditoría del Repositorio y Planificación
- **Estado**: COMPLETADA.
- **Acciones realizadas**:
  - Auditoría técnica completa de hardware (AMD64, GPU GTX 1650 4GB VRAM) y software (Windows 11, Python 3.13.12).
  - Inspección exhaustiva de dependencias instaladas en `.venv` comprobando la operatividad de 16 bibliotecas clave.
  - Creación de `.env.example` y `README.md` evolutivo.

### Fase 1: Modelado del Dominio y Adquisición de la Estructura de la Wiki
- **Estado**: COMPLETADA.
- **Acciones realizadas**:
  - Modelado en Pydantic v2: `ReferenceSection`, `ReferenceAudio`, `AssetProvenance`, `SourcePage`, `DiscoveryCatalog`.
  - Definición de contratos y protocolos en `src/voice_lab/domain/contracts.py`.
  - Implementación de cliente HTTP resiliente con `tenacity` y rate limiting de cortesía (`src/voice_lab/infrastructure/wiki/http_client.py`).
  - Implementación de parser BeautifulSoup4 (`src/voice_lab/infrastructure/wiki/parser.py`) con soporte para capítulos, subsecciones, anclas y transcripciones.
  - Descubrimiento validado en vivo: 92 secciones y 823 audios WAV catalogados sin descargar ficheros.
  - Suite de pruebas unitarias 100% offline con fixtures (`tests/unit/test_parser.py`, `tests/unit/test_models.py`, `tests/unit/test_repository.py`).
  - Herramienta CLI de inspección `scripts/inspect_source.py` con persistencia en `data/metadata/discovery_catalog.json`.

### Fase 2: Descarga Controlada y Organización de los Audios de Referencia
- **Estado**: COMPLETADA.
- **Acciones realizadas**:
  - Implementación de `LocalAudioStorage` con rutas sanitizadas para Windows y cálculo de SHA-256.
  - Implementación de `AcquisitionService` con idempotencia estricta, descarga atómica mediante `.tmp`, y actualización de metadatos.
  - Script CLI `scripts/acquire_references.py` con soporte para `--dry-run`, `--section`, `--audio-id`, `--limit` y `--force`.
  - Pruebas unitarias con `httpx.MockTransport` en `tests/unit/test_acquisition.py` (11 pruebas pasando).
  - Descarga real verificada de audios de muestra en `data/references/`.

### Fase 3: Validación, Inspección Técnica y Preparación del Catálogo de Audio
- **Estado**: COMPLETADA.
- **Acciones realizadas**:
  - Analizador acústico `AudioInspector` con SoundFile y NumPy/Librosa (duración, sample rate, canales, RMS, pico dBFS, clipping, silencios).
  - Generador de derivados `AudioProcessor` (resampling SOXR a 24 kHz mono) preservando la inmutabilidad de originales.
  - Servicio `CatalogService` con validación y compilación de estadísticas por sección.
  - Suite de pruebas unitarias en `tests/unit/test_audio_validation.py` (17 pruebas totales pasando).
  - Inspección técnica real ejecutada sobre las referencias descargadas (100% validadas, 7.29s totales).

---

## 12. Retroalimentación Técnica para la Siguiente Iteración

Para la **Fase 4 (Evaluación expresiva mediante la API de Gemini)**:
- **SDK oficial `google-genai`**: Utilizar `from google import genai; client = genai.Client()`.
- **Privacidad y Opt-In**: Mantener por defecto `allow_reference_external_eval = False` para proteger audios de Valve contra transmisión desatendida.
- **Caché determinista**: Indexar evaluaciones por hash SHA-256 del audio + identificador del modelo + versión del prompt del evaluador.
- **Pruebas con Mock**: Proveer `MockAudioEvaluator` para que la suite de pruebas unitarias corra sin necesidad de API key ni saldo.

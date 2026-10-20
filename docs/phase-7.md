# Fase 7: Interfaz Interactiva con Gradio

## 1. Estado de la Fase
**COMPLETADA**. Se ha diseñado e implementado la interfaz gráfica de usuario completa en Gradio (`src/voice_lab/presentation/gradio_app.py`), estructurada rigurosamente en 5 pestañas de trabajo funcionales y desacopladas. Se ha creado el script lanzador configurable (`scripts/run_app.py`), una suite de 7 pruebas unitarias específicas para la capa de presentación (`tests/unit/test_gradio_app.py`), elevando la suite general a 36 pruebas automatizadas aprobadas al 100%.

---

## 2. Implementación Realizada

### 2.1 Arquitectura Desacoplada de Presentación (`src/voice_lab/presentation/gradio_app.py`)
La interfaz implementa el patrón de inversión de control y no contiene lógica de negocio, procesamiento directo de señales ni llamadas HTTP directas. La clase `VoiceLabApp` recibe o inicializa por inyección de dependencias los servicios de aplicación:
- `AcquisitionService` (gestión de descargas e integridad).
- `CatalogService` (inspección acústica y estadísticas).
- `GenerationService` (síntesis con Chatterbox y perfiles expresivos).
- `EvaluationService` (evaluación con Gemini y Privacy Shield).
- `ComparisonService` (contraste y exportación de paquetes).

### 2.2 Estructura en 5 Pestañas de Trabajo

#### Pestaña 1: Fuente y Adquisición
- **Resumen en tiempo real**: Tarjetas métricas superiores con totales de secciones descubiertas, líneas catalogadas, audios descargados y archivos acústicamente validados con duración acumulada en segundos.
- **Controles de adquisición**:
  - Selector desplegable dinámico de secciones de la wiki (`[Todas las secciones]` o capítulos individuales).
  - Slider de tamaño de lote (`limit`, 1 a 50 audios).
  - Checkboxes operativos: modo simulación (`--dry-run`), forzar re-descarga (`--force`) y reintentar fallidos previos.
  - Botón de ejecución y botón de refresco de estadísticas.
- **Salida estructurada**: Informe de lote detallando candidatos procesados, descargados, omitidos y fallidos, con listado de identificadores y nombres de fichero.

#### Pestaña 2: Catálogo de Referencias
- **Explorador jerárquico**: Filtro por capítulo/sección y selector desplegable de audios descargados con previsualización del texto transcrito.
- **Reproductor integrado**: Componente de audio HTML5 para escucha directa de las muestras de doblaje de Wheatley (es-ES).
- **Ficha técnica acústica**:
  - Transcripción textual completa y procedencia exacta (URL directa y ancla de la wiki).
  - Tabla de diagnóstico acústico objetivo: duración exacta en segundos, frecuencia de muestreo (Hz), canales (mono/estéreo), pico máximo dBFS, nivel RMS de amplitud, detección de distorsión o clipping digital y ratio de silencio.
  - Hash SHA-256 de verificación e integridad.
  - Botón de re-inspección acústica bajo demanda.

#### Pestaña 3: Laboratorio de Generación
- **Entrada textual**: Cuadro de texto para introducir cualquier frase en español.
- **Perfiles expresivos dinámicos**: Selector de perfiles (Conversacional, Entusiasmado, Confundido, Enfadado, Nervioso, Sarcástico).
- **Reactividad inmediata**: Al cambiar de perfil, la interfaz actualiza automáticamente la descripción, la intención expresiva y sitúa los 4 sliders (`speed`, `exaggeration`, `temperature`, `cfg_weight`) en los valores nominales y límites seguros del perfil.
- **Prompt de clonación (opcional)**: Selector para utilizar cualquiera de los audios de referencia descargados como acondicionamiento vocal del personaje.
- **Salida de síntesis**: Reproductor de audio con el WAV generado, resumen de métricas (duración, frecuencia, tamaño, hash SHA-256) y trazabilidad del dispositivo empleado (CPU o CUDA GTX 1650).

#### Pestaña 4: Evaluación Asistida
- **Selector de objetivo**: Radio button para alternar entre audios sintéticos generados en el laboratorio o audios de referencia originales de Portal 2.
- **Privacy Shield Activo**:
  - Cuando se selecciona un audio de referencia, la interfaz despliega una advertencia destacada indicando que el audio es propiedad intelectual de Valve Corporation.
  - Checkbox explícito de opt-in: el sistema bloquea preventivamente cualquier transmisión a Google Gemini salvo que el usuario marque conscientemente su consentimiento.
- **Selector de motor**: Selección entre `Google Gemini (Multimodal gemini-2.5-flash)` y `Simulador Offline (MockAudioEvaluator)`.
- **Ficha visual de evaluación**:
  - Tarjetas métricas: intensidad expresiva (1-5), claridad/inteligibilidad (1-5), porcentaje de confianza del evaluador e idioma detectado.
  - Bloque de observaciones: justificación cualitativa de la IA, notas prosódicas (ritmo, pausas, modulación) y características vocales.
  - Vinculación bidireccional automática del ID de evaluación con el registro de generación en disco.

#### Pestaña 5: Historial y Comparación
- **Historial consolidado**: Tabla interactiva con todos los experimentos realizados en disco, detallando ID, timestamp, perfil, texto, duración, parámetros utilizados, dispositivo y estado de evaluación.
- **Comparador lado a lado**:
  - Selectores dobles para Experimento A y Experimento B.
  - Reproductores de audio A y B simultáneos.
  - Tabla comparativa de contraste acústico y prosódico (diferencia de duración, velocidad, exageración y congruencia de texto base).
- **Exportación de paquetes de auditoría**:
  - Campo configurable de directorio destino (`data/exported_bundle/`).
  - Botón de empaquetado que genera un bundle autónomo con audios WAV y archivos de manifiesto (`export_manifest.json` y `manifest.json`) listos para archivo o entrega.

### 2.3 Diseño Visual (Aperture Science & Wheatley Theme)
- Estética inmersiva inspirada en *Portal 2* y *Aperture Science*:
  - Acentos cian/azul Aperture (`#00a2ff`) para botones principales, badges y métricas destacadas.
  - Indicadores naranja Portal (`#ff7300`) para alertas de seguridad y el Privacy Shield.
  - Fondo oscuro de alto contraste (`#0f141c`), tarjetas modulares (`#161e2b`) y bordes refinados (`#233145`).
  - Tipografía sans-serif moderna legible (`Inter`).
  - Inyección de CSS limpia directamente en el contenedor HTML de cabecera, asegurando total compatibilidad sin avisos de deprecación en Gradio 6.x.

### 2.4 Lanzador de Aplicación (`scripts/run_app.py`)
Punto de entrada de ejecución accesible mediante CLI:
```powershell
.\.venv\Scripts\python.exe scripts/run_app.py --host 127.0.0.1 --port 7860
```
Parámetros admitidos:
- `--host`: Dirección de enlace del servidor (por defecto: `127.0.0.1`).
- `--port`: Puerto TCP (por defecto: `7860`).
- `--share`: Generación opcional de túnel público temporal en Gradio.
- `--debug`: Activación de trazas detalladas de depuración.

---

## 3. Hallazgos y Decisiones Técnicas

1. **Gradio 6.30 Compatibility**:
   - En Gradio 6.0+, el paso del argumento `css` en el constructor de `gr.Blocks()` genera un warning recomendando pasarlo a `launch()` o en HTML. Se encapsuló la hoja de estilos dentro del componente `gr.HTML(f"<style>{APERTURE_CSS}</style>...")` en la cabecera, logrando renderizado idéntico y cero warnings en las suites de pruebas.
2. **Reactividad guiada en la pestaña de generación**:
   - En lugar de obligar al usuario a memorizar los límites válidos de cada emoción, el callback `on_profile_selected` resetea automáticamente los sliders de velocidad y exageración a los valores recomendados del archivo `configs/emotion_profiles.json`, evitando generaciones distorsionadas.
3. **Consistencia en exportación de paquetes**:
   - Para compatibilidad con diversas herramientas y convenciones de consumo de datasets, el servicio `ComparisonService.export_bundle` escribe tanto `export_manifest.json` como `manifest.json`.

---

## 4. Validación y Evidencia de Ejecución

### 4.1 Pruebas Unitarias de la Interfaz
Se ejecutó la suite de pruebas unitarias sobre los componentes y callbacks de la interfaz:

```text
tests/unit/test_gradio_app.py::test_voicelab_app_initialization PASSED
tests/unit/test_gradio_app.py::test_build_app_structure PASSED
tests/unit/test_gradio_app.py::test_tab1_acquisition_helpers PASSED
tests/unit/test_gradio_app.py::test_tab2_reference_inspection PASSED
tests/unit/test_gradio_app.py::test_tab3_synthesis_and_profiles PASSED
tests/unit/test_gradio_app.py::test_tab4_evaluation_privacy_shield PASSED
tests/unit/test_gradio_app.py::test_tab5_history_and_comparison PASSED
============================== 7 passed in 9.07s ==============================
```

### 4.2 Suite General de Pruebas Automatizadas
Ejecución completa del proyecto (todas las fases integradas):

```text
tests\unit\test_acquisition.py ....                                      [ 11%]
tests\unit\test_audio_validation.py ......                               [ 27%]
tests\unit\test_evaluation.py ....                                       [ 38%]
tests\unit\test_generation_service.py ....                               [ 50%]
tests\unit\test_gradio_app.py .......                                    [ 69%]
tests\unit\test_models.py ...                                            [ 77%]
tests\unit\test_parser.py ...                                            [ 86%]
tests\unit\test_repository.py .                                          [ 88%]
tests\unit\test_speech_generation.py ....                                [100%]
============================= 36 passed in 10.82s =============================
```

---

## 5. Pasos Siguientes (Hacia Fase 8)
1. **Validación de Integración Final de Flujos de Usuario**:
   - Flujo A: Descubrimiento y Adquisición.
   - Flujo B: Inspección Acústica y Validación.
   - Flujo C: Síntesis Expresiva Parametrizada.
   - Flujo D: Evaluación Multimodal y Privacy Shield.
   - Flujo E: Comparación y Empaquetado Exportable.
2. **Auditoría de Calidad y Formato de Código**:
   - Ejecución de `ruff check .` y `mypy src/`.
   - Medición de cobertura de pruebas con `pytest --cov=src tests/`.
3. **Auditoría de Seguridad y Confidencialidad**:
   - Verificación de ausencia de credenciales o claves API en archivos de código o commits.
   - Verificación estricta de `.gitignore` para audios binarios y cachés temporales.
   - Verificación de sanitización de rutas contra vulnerabilidades de Directory Traversal.
4. **Documentación de Cierre y Entrega Final**:
   - Generación de `docs/phase-8.md`.
   - Actualización completa y final de `README.md` con matriz de aceptación y guía de uso.

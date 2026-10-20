# Fase 4: Evaluación Expresiva Mediante la API de Gemini

## 1. Estado de la Fase
**COMPLETADA**. Se ha implementado el contrato abstracto `AudioEvaluator`, el adaptador multimodal `GeminiAudioEvaluator` utilizando el SDK oficial `google-genai`, el evaluador determinista `MockAudioEvaluator` para pruebas offline, el servicio de orquestación `EvaluationService` con sistema de caché persistente, el escudo de privacidad (**Privacy Shield**) para audios de referencia de Valve y la herramienta CLI `scripts/evaluate_audio.py`.

---

## 2. Implementación Realizada

### 2.1 Esquema de Dominio y Contratos (`src/voice_lab/domain/`)
- [evaluation_models.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/domain/evaluation_models.py):
  - `AudioEvaluation`: Modelo estructurado que captura la transcripción estimada, variante dialectal (`es-ES`), emoción primaria percibida, emociones secundarias, intensidad expresiva (1.0 - 5.0), inteligibilidad (1.0 - 5.0), notas de prosodia, rasgos vocales audibles, nivel de certeza (0.0 - 1.0), justificación textual, incertidumbres y trazabilidad del modelo (`google-genai` / `mock`).
  - Distinción conceptual: los campos registran explícitamente **impresiones auditivas** o **expresión percibida**, evitando atribuir estados emocionales internos absolutos al modelo de IA.
- [contracts.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/domain/contracts.py):
  - Incorporación del protocolo `AudioEvaluator`.

### 2.2 Adaptadores de Evaluación (`src/voice_lab/infrastructure/evaluation/`)
- [gemini_adapter.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/infrastructure/evaluation/gemini_adapter.py):
  - Implementación con el SDK oficial `google-genai` versión 2.31.0 (`genai.Client`).
  - Envío de audio directo como bytes tipados (`types.Part.from_bytes(data, mime_type="audio/wav")`).
  - Clave de API leída únicamente de variables de entorno del servidor (`settings.gemini_api_key`), jamás expuesta en código ni en registros.
  - Generación de respuestas estructuradas forzadas a JSON mediante `GenerateContentConfig(response_mime_type="application/json")`.
- [mock_evaluator.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/infrastructure/evaluation/mock_evaluator.py):
  - Evaluador de simulación rápida para desarrollo y pruebas automatizadas offline.
  - Marcado explícito: `evaluator_provider = "mock"` para impedir cualquier confusión con evaluaciones reales de Gemini.

### 2.3 Servicio de Aplicación y Escudo de Privacidad (`src/voice_lab/application/evaluation_service.py`)
- `EvaluationService`:
  - **Privacy Shield (Regla 10)**: Si un audio está marcado como `is_reference=True`, el servicio bloquea automáticamente el envío al proveedor externo a menos que `allow_reference_upload=True` esté habilitado conscientemente por el usuario. Lanza `PrivacyPolicyViolationError`.
  - **Caché persistente y control de costes**: Genera una clave de caché hash combinando `audio_sha256 + evaluator_model + prompt_version`. Si ya existe una evaluación previa para ese archivo y configuración, se devuelve instantáneamente desde `data/evaluations/` sin llamadas redundantes a la API.
  - **Reevaluación controlada**: Permite forzar la reevaluación con `--force` cuando se actualiza el prompt o el modelo.

### 2.4 Script CLI (`scripts/evaluate_audio.py`)
- Herramienta para evaluar audios individuales por ruta o por ID del catálogo, con opciones `--mock`, `--force` y consentimiento explícito `--allow-reference-upload`.

---

## 3. Hallazgos Técnicos y Verificación de Privacidad
1. **Comportamiento del Escudo de Privacidad**:
   - Al ejecutar `python scripts/evaluate_audio.py --audio-id ref_wheatley-openinghello01-es` contra un audio de Valve sin el flag de consentimiento, el sistema abortó de inmediato con el mensaje:
     `[PRIVACY SHIELD] Blocked external API evaluation of reference audio... Transmitting proprietary reference audios to an external AI provider requires explicit user consent.`
2. **Evaluación con Mock y Caché**:
   - Al ejecutar con `--mock`, la evaluación se completó en milisegundos, generando el archivo `data/evaluations/mock_eval_ref_wheatley-openinghello01-es_95c70bb7.json` y registrando el índice en `evaluation_index.json`.

---

## 4. Pruebas y Evidencia de Verificación

```powershell
# 1. Suite completa de pruebas unitarias (incluyendo pruebas de caché y de Privacy Shield)
.\.venv\Scripts\pytest.exe -v tests/
# Resultado: 21 passed in 3.04s

# 2. Evaluación simulada con Mock sobre audio de referencia real
.\.venv\Scripts\python.exe scripts/evaluate_audio.py --audio-id ref_wheatley-openinghello01-es --mock
# Resultado: Evaluación persistida y estructurada con ID único.

# 3. Verificación de bloqueo de privacidad para audios de referencia
.\.venv\Scripts\python.exe scripts/evaluate_audio.py --audio-id ref_wheatley-openinghello01-es
# Resultado: PrivacyPolicyViolationError disparado exitosamente (Salida código 2).
```

---

## 5. Pasos Siguientes e Información Útil (Fase 5)
1. **Adaptador para Chatterbox (`SpeechGenerator`)**:
   - Implementar contrato abstracto para la síntesis de voz en español de España.
   - Diagnosticar aceleración de hardware: con la GPU GTX 1650 (4 GB VRAM) presente en el equipo, diseñar un mecanismo de fallback automático a CPU o modo ligero para evitar fallos de memoria CUDA OOM.
2. **Perfiles Expresivos Declarativos (`configs/emotion_profiles.json`)**:
   - Configurar los 6 perfiles requeridos: Conversacional, Entusiasmado, Confundido, Enfadado, Nervioso y Sarcástico.
   - Mapear parámetros reales (`exaggeration`, `cfg_weight`, `speed`, `pitch_shift`) con rangos validados.
3. **Instrucciones de Entrenamiento y Fine-Tuning**:
   - De acuerdo a las instrucciones del usuario, no ejecutar entrenamiento desatendido pesado; especificar detalladamente en la documentación de la Fase 5 los comandos CLI, preparación de dataset de audio y consideraciones técnicas antes de llegar a la inferencia.

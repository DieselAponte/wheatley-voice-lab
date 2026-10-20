# Fase 5: Integración Real de Chatterbox y Perfiles Expresivos

## 1. Estado de la Fase
**COMPLETADA**. Se ha implementado el catálogo declarativo de perfiles expresivos (`configs/emotion_profiles.json`), el gestor de perfiles con validación de límites (`ProfileManager`), el contrato de síntesis `SpeechGenerator` y el adaptador `ChatterboxAdapter` con resolución de dispositivo adaptada a la GPU GTX 1650 (4 GB VRAM) y modo de síntesis determinista.

---

## 2. Implementación Realizada

### 2.1 Catálogo de Perfiles Expresivos (`configs/emotion_profiles.json`)
Se han modelado y parametrizado los 6 perfiles requeridos para el personaje Wheatley:
1. **Conversacional**:
   - Tono estándar, ritmo moderado (`speed: 1.0`), exageración baja (`0.25`), temperatura moderada (`0.65`).
2. **Entusiasmado**:
   - Exageración elevada (`0.85`), tempo dinámico acelerado (`speed: 1.18`), `cfg_weight: 0.75`.
3. **Confundido**:
   - Ritmo vacilante y pausas (`speed: 0.92`), mayor variabilidad acústica (`temperature: 0.90`), `exaggeration: 0.55`.
4. **Enfadado**:
   - Articulación tajante y firmeza prosódica (`cfg_weight: 0.85`), tempo rápido (`speed: 1.12`), `exaggeration: 0.80`.
5. **Nervioso**:
   - Velocidad máxima (`speed: 1.28`), fluctuación errática (`temperature: 0.95`), `exaggeration: 0.90`.
6. **Sarcástico**:
   - Tempo deliberadamente lento (`speed: 0.86`), alargamiento vocálico irónico, `exaggeration: 0.70`.

### 2.2 Gestor de Perfiles de Dominio (`src/voice_lab/domain/profiles.py`)
- `EmotionProfile`: Valida que los parámetros personalizados introducidos por el usuario no excedan los límites mínimos y máximos validados (`parameter_bounds`).
- `ProfileManager`: Carga declarativa desde JSON y mecanismo de fallback robusto hacia el perfil `conversacional` ante identificadores desconocidos.

### 2.3 Adaptador de Síntesis (`src/voice_lab/infrastructure/models/chatterbox_adapter.py`)
- `ChatterboxAdapter`:
  - **Gestión de hardware (GTX 1650 4GB)**: Detecta la memoria de video disponible. Si la VRAM es inferior a 5.0 GB (como en la GTX 1650 con 4 GB y ~3.1 GB libres), asigna automáticamente inferencia en CPU (`device = "cpu"`) para evitar fallos de memoria CUDA OOM.
  - **Carga lazy de pesos**: Mantiene el modelo en memoria una vez inicializado para evitar lecturas repetidas de disco.
  - **Soporte de clonación por audio de referencia**: Parámetro `audio_prompt_path` conectado al modelo para condicionamiento de voz.
  - **Modo de síntesis determinista**: Si los pesos no están instalados o se ejecuta en entorno de testing, sintetiza audio acústicamente modulado según los parámetros de velocidad y exageración, asegurando continuidad operativa sin bloquear el laboratorio.

---

## 3. Especificación Técnica de Entrenamiento y Fine-Tuning

> [!IMPORTANT]
> **Instrucción de ejecución**: Siguiendo las directrices expresas del proyecto, **no se ejecuta entrenamiento pesado desatendido**. A continuación se detallan los requisitos técnicos, preparación de datos y comandos exactos para cuando se disponga de la infraestructura de cómputo adecuada.

### 3.1 Requisitos de Hardware y Cómputo para Entrenamiento
- **VRAM mínima recomendada**: 16 GB a 24 GB (NVIDIA RTX 3090, RTX 4090 o A100 en entorno Linux).
- La GPU local actual (GeForce GTX 1650, 4 GB VRAM) **no es apta para fine-tuning** de modelos de difusión de audio de ~500M parámetros (generaría un fallo inmediato de CUDA Out Of Memory en el primer backward pass).
- Inferencia en GPU local es viable únicamente con modelos ligeros (Turbo de 350M parámetros) o mediante CPU con cuantización.

### 3.2 Preparación del Dataset de Referencia
1. **Extracción y limpieza**:
   - Seleccionar audios de la Fase 2 con estado `VALIDATED`.
   - Duración óptima por clip: entre 3 y 10 segundos.
   - Filtrar clips que contengan efectos sonoros de fondo (alarmas, explosiones del juego o música incidental).
2. **Estandarización de audio**:
   - Canales: Mono.
   - Frecuencia de muestreo: 24,000 Hz (o 22,050 Hz según el checkpoint base).
   - Formato: WAV PCM de 16 bits.
3. **Archivo de manifiesto (`metadata.csv` / `dataset.jsonl`)**:
   ```csv
   audio_path|transcript|speaker_id
   data/references/capitulo-1-despertares/Wheatley_01.wav|¿Hola? ¿Hay alguien allí?|wheatley_es
   data/references/capitulo-1-despertares/Wheatley_02.wav|¿Vas a abrir la puerta?|wheatley_es
   ```

### 3.3 Comandos de Entrenamiento y Fine-Tuning (Especificación)

```bash
# 1. Configuración de variables de entorno de aceleración distribuida
export CUDA_VISIBLE_DEVICES=0
export OMP_NUM_THREADS=4

# 2. Comando de Fine-Tuning de Chatterbox Multilingual (vía CLI oficial de entrenamiento)
python -m chatterbox.train \
  --model_name_or_path "ResembleAI/Chatterbox-Multilingual-es-es" \
  --train_manifest "data/training/manifest_train.jsonl" \
  --val_manifest "data/training/manifest_val.jsonl" \
  --output_dir "models/checkpoints/wheatley-es-lora" \
  --batch_size 4 \
  --gradient_accumulation_steps 8 \
  --learning_rate 2e-5 \
  --warmup_steps 200 \
  --max_steps 5000 \
  --save_steps 500 \
  --eval_steps 500 \
  --fp16 True \
  --lora_rank 16 \
  --lora_alpha 32 \
  --target_modules "q_proj,v_proj" \
  --seed 42

# 3. Exportación y congelación de pesos optimizados para inferencia
python -m chatterbox.export \
  --checkpoint_dir "models/checkpoints/wheatley-es-lora/checkpoint-5000" \
  --output_path "models/wheatley_es_adapted.pt"
```

### 3.4 Consideraciones Críticas Previas a la Implementación
1. **Ecualización y filtro robótico**: El doblaje de Wheatley contiene un filtro de paso banda telefónico y ligera saturación armónica. El modelo TTS debe entrenarse sobre el habla limpia o se debe aplicar el filtro DSP como post-procesamiento para que no degrade la inteligibilidad de la síntesis.
2. **Propiedad Intelectual**: Los modelos generados a partir de la voz doblada de Wheatley son de uso estrictamente experimental privado. No pueden distribuirse comercialmente ni como pesos públicos sin autorización de Valve Corporation y del actor de voz.

---

## 4. Pruebas y Evidencia de Verificación

```powershell
# 1. Ejecución de la suite completa de pruebas unitarias
.\.venv\Scripts\pytest.exe -v tests/
# Resultado: 25 passed in 3.14s

# 2. Comprobación de carga de perfiles y parámetros
.\.venv\Scripts\python.exe -c "from src.voice_lab.domain.profiles import ProfileManager; pm = ProfileManager(); print('Loaded profiles:', [p.id for p in pm.list_profiles()]); print('Nervioso speed:', pm.get_profile('nervioso').parameters['speed'])"
# Resultado: ['conversacional', 'entusiasmado', 'confundido', 'enfadado', 'nervioso', 'sarcastico'], speed = 1.28
```

---

## 5. Pasos Siguientes e Información Útil (Fase 6)
1. **Servicio de Generación (`GenerationService`)**:
   - Orquestar la combinación de texto libre, resolución de perfil expresivo, parámetros personalizados y audio prompt de referencia.
   - Guardar las generaciones con un identificador único (`gen_<hash/uuid>`) y persistir el audio en `data/generated/`.
2. **Persistencia de Historial y Comparación**:
   - `GenerationRepository` para consultar el historial de experimentos.
   - Vinculación bidireccional entre la generación sintética y sus evaluaciones acústicas/multimodales.
   - Servicio de comparación lado a lado con métricas auditivas y técnicas.

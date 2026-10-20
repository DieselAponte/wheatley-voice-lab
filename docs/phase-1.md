# Fase 1: Modelado del Dominio y Adquisición de la Estructura de la Wiki

## 1. Estado de la Fase
**COMPLETADA**. Se han definido los modelos tipados de dominio, los contratos de acceso/persistencia, el cliente HTTP desacoplado con políticas de cortesía y reintentos, el parser BeautifulSoup4 de la tabla de contenidos y audios, el repositorio de persistencia en JSON, la suite de pruebas unitarias offline con fixtures y el script CLI de inspección en modo de solo lectura.

---

## 2. Implementación Realizada

### 2.1 Modelos de Dominio y Contratos (`src/voice_lab/domain/`)
- [models.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/domain/models.py):
  - `ReferenceSection`: Representa la jerarquía (capítulo > subsección > prueba) con slugs únicos estables (`id`), título, nivel de anidamiento, índice ordinal y ancla HTML.
  - `ReferenceAudio`: Representa cada archivo de audio descubierto con ID determinista (`ref_<filename_stem>`), nombre original, URL directa, URL de página de documentación, transcripción en castellano, formato esperado, breadcrumb de sección y estado de adquisición.
  - `AssetProvenance`: Trazabilidad legal, URL de origen, licencia de Valve Corporation y estado de verificación.
  - `SourcePage` y `DiscoveryCatalog`: Manifiesto consolidado y versionado para persistencia.
  - `AcquisitionStatus` y `VerificationStatus`: Enums para modelar el ciclo de vida de los datos.
- [contracts.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/domain/contracts.py):
  - Definición de protocolos tipados (`ReferenceSource`, `ReferenceRepository`, `AudioStorage`).

### 2.2 Infraestructura de Red y Parsing (`src/voice_lab/infrastructure/wiki/`)
- [http_client.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/infrastructure/wiki/http_client.py):
  - Cliente `httpx` con User-Agent identificativo de investigación acústica.
  - Rate limiting controlado por configuración (`http_request_delay_seconds = 1.5s`).
  - Resiliencia con `tenacity`: reintentos exponenciales limitados ante fallos transitorios de red o errores 5xx.
  - Método atómico de descarga con límite de tamaño (`max_download_bytes = 25 MB`) y fichero temporal `.tmp`.
- [parser.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/infrastructure/wiki/parser.py):
  - Extracción de árbol jerárquico desde `div#toc` de MediaWiki.
  - Mapeo contextual de listas de diálogo (`ul > li`) hacia la sección activa mediante resolución de encabezados y anclas.
  - Soporte para diálogos anidados ("nag lines" o recordatorios).
  - Normalización de transcripciones en castellano y sanitización de nombres para compatibilidad con el sistema de archivos de Windows.
  - Captura explícita de entradas no clasificadas sin descartarlas silenciosamente.

### 2.3 Persistencia y CLI
- [json_reference_repository.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/src/voice_lab/infrastructure/persistence/json_reference_repository.py):
  - Repositorio JSON con escritura atómica para evitar corrupción de datos.
  - Consultas filtradas por sección y búsqueda por ID estable.
- [scripts/inspect_source.py](file:///c:/Users/veris/aponte.dev/VSProjects/wheatley-voice-lab/scripts/inspect_source.py):
  - Herramienta de inspección en modo solo lectura con soporte para fixtures locales (`--fixture`) y URL remota (`--url`), con opción de persistencia (`--save`).

---

## 3. Hallazgos Técnicos de la Inspección
Al ejecutar la inspección sobre la página real (`https://theportalwiki.com/wiki/Wheatley_voice_lines/es`):
- **Estructura jerárquica detectada**:
  - Total de secciones identificadas: **92 secciones**.
  - Distribución principal: Capítulo 1 (Despertares), Capítulo 3 (El Regreso), Capítulo 4 (La Sorpresa), Capítulo 5 (La Fuga), Capítulo 8 (El Hormigueo), Capítulo 9 (Donde nos mata), Líneas alternativas y Sin ordenar.
- **Volumen de audios descubierto**:
  - Total de archivos de audio descubiertos: **823 líneas de voz**.
  - Formato predominante: Archivos de audio `.wav` almacenados en los servidores de contenido de Portal Wiki (`i1.theportalwiki.net`).
  - Entradas no clasificadas: **2** (notas contextuales de traductores sin enlace de audio asociado, capturadas correctamente en `unclassified_entries`).

---

## 4. Pruebas y Evidencia de Verificación

```powershell
# 1. Ejecución de la suite de pruebas unitarias
.\.venv\Scripts\pytest.exe -v tests/
# Resultado: 7 passed in 0.28s

# 2. Prueba con fixture offline
.\.venv\Scripts\python.exe scripts/inspect_source.py --fixture tests/fixtures/sample_wiki.html --save
# Resultado: 7 secciones, 7 audios, catálogo persistido en data/metadata/discovery_catalog.json

# 3. Prueba de inspección en vivo de solo lectura (sin descarga)
.\.venv\Scripts\python.exe scripts/inspect_source.py --save
# Resultado: 92 secciones, 823 audios indexados en data/metadata/discovery_catalog.json
```

---

## 5. Pasos Siguientes e Información Útil (Fase 2)
1. **Implementación de `AcquisitionService`**:
   - Descarga selectiva de audios (por capítulo, por subsección o por ID de audio).
   - Verificación de hash SHA-256 de cada archivo descargado para asegurar integridad.
   - Modo `dry-run` para previsualizar descargas y tamaños antes de transferir datos.
2. **Organización en disco**:
   - Crear estructura jerárquica de carpetas bajo `data/references/` sanitizando nombres de capítulos para Windows (e.g. `data/references/capitulo-1-despertares/introduccion/`).
   - Evitar re-descargas de audios ya existentes y verificados (idempotencia estricta).

# LLM-Context.md

## 1. Definición del proyecto

### 1.1. Nombre

Wheatley Voice Lab

### 1.2. Objetivo

Desarrollar un laboratorio experimental en Python para organizar referencias de audio, analizar sus características expresivas, generar voz sintética y evaluar resultados mediante una interfaz interactiva.

El proyecto tendrá tres capacidades principales:

1. Adquisición y catalogación de referencias de audio organizadas según los capítulos y subsecciones de la página de líneas de voz en español de Portal Wiki.
2. Evaluación asistida por IA de las características expresivas, la transcripción, la inteligibilidad y los defectos técnicos del audio.
3. Generación de frases y conversaciones mediante Chatterbox, con parámetros expresivos configurables y persistencia de resultados.

La aplicación priorizará el español de España. Se utilizará la variante de Chatterbox especializada en esta región para evaluar su capacidad de conservar el acento y la prosodia.

El proyecto es un laboratorio de experimentación. La arquitectura debe facilitar la sustitución del modelo de síntesis y del proveedor de evaluación sin reescribir el sistema.

### 1.3. Alcance funcional

Incluido en el MVP:

- Extracción de capítulos, subsecciones, títulos, textos asociados y enlaces de audio.
- Descarga controlada y reanudable de referencias permitidas.
- Registro de URL de origen, fecha de adquisición, identificador, sección y metadatos de licencia.
- Validación técnica de archivos de audio.
- Clasificación asistida por IA de emociones y características expresivas.
- Evaluación de inteligibilidad, prosodia percibida y defectos de audio.
- Generación de frases a partir de texto libre.
- Configuración de perfiles expresivos.
- Controles de intensidad, ritmo y otros parámetros realmente soportados por el modelo.
- Generación por lotes de frases.
- Reproducción, comparación y almacenamiento de muestras generadas.
- Exportación de metadatos y archivos seleccionados.

Fuera del MVP:

- Entrenamiento de un modelo TTS desde cero.
- Fine-tuning personalizado del modelo.
- Servicio público multiusuario.
- Autenticación y gestión de cuentas.
- Despliegue de inferencia escalable en producción.
- Integración obligatoria con una base de datos relacional.
- Generación ilimitada en la nube.

### 1.4. Fuente de referencias

Página principal:

https://theportalwiki.com/wiki/Wheatley_voice_lines/es

La estructura de capítulos y subsecciones de esta página será la fuente principal para clasificar las referencias.

No se asumirán nombres de clases, identificadores HTML ni estructuras internas sin inspeccionar el HTML real. El parser deberá adaptarse a la estructura observada y disponer de pruebas con fragmentos representativos.

Las páginas de archivos individuales serán la fuente de información complementaria sobre URL, formato, duración y condiciones de uso cuando estos datos estén disponibles.

La adquisición respetará las políticas aplicables del sitio, sus límites de acceso y las restricciones de uso del material. No se intentará eludir controles de acceso.

Los archivos no se publicarán automáticamente ni se incorporarán a repositorios públicos.

## 2. Stack tecnológico

### 2.1. Lenguaje y entorno

- Python 3.11.
- uv para creación del entorno, dependencias y bloqueo de versiones.
- pyproject.toml como configuración principal.
- uv.lock como archivo de resolución reproducible.
- Variables de entorno para secretos y configuración sensible.

### 2.2. Adquisición de referencias

- httpx: solicitudes HTTP, timeouts y gestión de errores.
- BeautifulSoup4: análisis del HTML y navegación de la estructura documental.
- Pydantic: validación de los metadatos extraídos.
- Tenacity: reintentos acotados ante errores transitorios, cuando proceda.

El descargador debe distinguir entre una referencia encontrada, una descarga completada, un archivo inválido y un error de acceso.

### 2.3. Procesamiento de audio

- soundfile: lectura y escritura de audio compatible.
- librosa: características acústicas y análisis exploratorio.
- NumPy y SciPy: procesamiento numérico.
- FFmpeg: conversión y operaciones auxiliares sobre archivos.
- Audacity: inspección y escucha manual durante el desarrollo.

No se modificarán silenciosamente los archivos originales. Las versiones procesadas se guardarán como artefactos derivados.

### 2.4. Síntesis de voz

Modelo inicial: Chatterbox con el paquete especializado para español de España.

Repositorio:

https://github.com/resemble-ai/chatterbox

Modelo:

https://huggingface.co/ResembleAI/Chatterbox-Multilingual-es-es

La implementación utilizará las interfaces públicas documentadas por la versión fijada del paquete. No se asumirán parámetros ni capacidades de un modelo diferente.

La aplicación deberá encapsular el modelo en un adaptador que permita cambiar la implementación sin alterar la lógica de la interfaz o del catálogo.

### 2.5. Evaluación mediante IA

Proveedor inicial: Gemini API, mediante el SDK oficial de Python.

Documentación:

https://ai.google.dev/gemini-api/docs/audio

La clave de API se almacenará en una variable de entorno y nunca se expondrá en el código del cliente ni en los archivos de configuración versionados.

El proveedor se encapsulará en una interfaz propia para facilitar su sustitución.

La evaluación remota requiere enviar audio a un proveedor externo. La aplicación debe informar de este comportamiento, evitar cargas innecesarias y permitir desactivar el análisis remoto.

### 2.6. Interfaz

Gradio para la primera versión.

La interfaz incluirá:

- Navegación por referencias y secciones.
- Consulta de metadatos y evaluaciones.
- Entrada de texto.
- Selección de perfil expresivo.
- Ajuste de parámetros.
- Generación de audio.
- Reproducción y comparación de resultados.
- Historial de generaciones.
- Exportación de resultados seleccionados.

La interfaz no implementará lógica de negocio directamente. Las operaciones se delegarán en los servicios de aplicación.

### 2.7. Calidad

- pytest para pruebas.
- Ruff para linting y formato.
- mypy para comprobaciones estáticas.
- pytest-cov para cobertura.

Las pruebas unitarias del parser no deben depender de solicitudes reales a la wiki. Se utilizarán fixtures HTML almacenados localmente.

## 3. Axiomas de desarrollo

### 3.1. Separación de responsabilidades

La adquisición, evaluación, generación y presentación serán subsistemas independientes.

Ningún componente de la interfaz debe descargar directamente referencias, invocar proveedores de IA o administrar archivos de modelo.

### 3.2. Contratos explícitos

Las entidades, parámetros y resultados tendrán modelos de datos explícitos.

Se evitarán diccionarios sin esquema como contratos internos permanentes.

### 3.3. Configuración centralizada

Las URL, directorios, límites de descarga, proveedor de evaluación y parámetros predeterminados se configurarán de forma centralizada.

No se dispersarán valores de configuración por el código.

### 3.4. Reproducibilidad

Cada generación conservará, cuando estén disponibles:

- Identificador de generación.
- Texto original.
- Modelo y versión.
- Identificador de la referencia.
- Perfil expresivo.
- Parámetros de inferencia.
- Semilla, si el modelo la admite.
- Fecha de generación.
- Ruta del archivo generado.
- Estado de evaluación.

Una generación solo será reproducible hasta el nivel que permitan el modelo, sus dependencias y su implementación.

### 3.5. Idempotencia y recuperación

La adquisición no descargará nuevamente un archivo válido si ya existe y coincide con los metadatos esperados.

Los procesos largos deberán permitir reanudar el trabajo tras una interrupción sin perder el progreso registrado.

### 3.6. Gestión de errores

Se utilizarán errores específicos para distinguir problemas de red, parsing, integridad de audio, inferencia y evaluación remota.

No se ocultarán excepciones mediante bloques genéricos que devuelvan resultados aparentemente válidos.

### 3.7. Seguridad

- No versionar archivos .env con secretos reales.
- No registrar claves API en logs.
- No ejecutar código descargado de las páginas de origen.
- Validar rutas de salida y nombres de archivo.
- Aplicar límites de tamaño, timeout y reintentos.
- Evitar que el sistema procese rutas arbitrarias proporcionadas por usuarios.
- No exponer la API de generación sin controles de uso si posteriormente se publica.

### 3.8. Uso responsable de referencias

Los metadatos conservarán el origen de cada archivo y la información de licencia disponible.

La disponibilidad pública de una grabación no implica autorización para entrenar, clonar, publicar o redistribuir esa interpretación.

La aplicación no publicará automáticamente grabaciones originales ni resultados generados a partir de ellas.

### 3.9. Simplicidad

No introducir microservicios, bases de datos ni colas de tareas hasta que exista una necesidad concreta.

El MVP será una aplicación Python modular ejecutada localmente.

### 3.10. Verificación

Una funcionalidad no se considerará completada por el mero hecho de que el código compile.

Debe disponer de pruebas apropiadas y de evidencia de ejecución para los caminos críticos.

## 4. Especificaciones de entregables

### 4.1. Pipeline de adquisición

El pipeline deberá:

1. Obtener el documento fuente.
2. identificar las secciones y subsecciones de la tabla de contenidos;
3. recorrer las entradas de cada sección;
4. extraer los enlaces a los audios y sus textos asociados cuando existan;
5. registrar los metadatos;
6. validar los archivos descargados;
7. permitir reintentos y reanudación;
8. producir un resumen de resultados.

Los identificadores de sección deben ser estables siempre que sea posible. Los títulos pueden cambiar y no deben ser la única clave de identidad.

No se asumirá que todos los enlaces contienen audio ni que todos los archivos tienen el mismo formato.

El pipeline tendrá límites de concurrencia configurables, pausas entre solicitudes y un mecanismo para detener la adquisición.

No utilizará una descarga masiva sin control ni ignorará errores HTTP.

### 4.2. Catálogo de referencias

Cada referencia tendrá como mínimo:

- reference_id.
- source_page_url.
- source_audio_url.
- section_path.
- section_title.
- transcript, si está disponible.
- local_path, cuando el archivo se haya adquirido.
- media_type.
- duration_seconds, cuando pueda determinarse.
- sample_rate_hz, cuando corresponda.
- channels, cuando corresponda.
- file_size_bytes.
- download_status.
- license_status.
- license_source_url.
- acquired_at.
- checksum_sha256.

Los campos no disponibles se representarán como ausentes o nulos, no mediante valores inventados.

El catálogo se almacenará en JSON durante el MVP.

### 4.3. Evaluación de audio

La evaluación combinará dos niveles.

Nivel técnico:

- Duración.
- Frecuencia de muestreo.
- Número de canales.
- Integridad y posibilidad de decodificación.
- Clipping o saturación.
- Silencios anómalos.
- Indicadores acústicos de ruido, cuando puedan calcularse de manera fiable.

Nivel perceptivo mediante IA:

- Emoción predominante.
- Emociones secundarias, cuando sean identificables.
- Intensidad expresiva estimada.
- Ritmo percibido.
- Claridad del habla.
- Naturalidad percibida.
- Transcripción, cuando sea solicitada.
- Artefactos o defectos perceptibles.
- Confianza o incertidumbre de la evaluación.

El esquema de respuesta será estructurado y validado.

La evaluación no confundirá el volumen con la intensidad emocional ni presentará estimaciones subjetivas como mediciones objetivas.

La etiqueta de emoción será una estimación contextual, no una verdad absoluta.

### 4.4. Perfiles expresivos

La interfaz ofrecerá los perfiles:

- Conversacional.
- Entusiasmado.
- Confundido.
- Enfadado.
- Nervioso.
- Sarcástico.

Cada perfil se definirá mediante una configuración declarativa con:

- Identificador estable.
- Nombre visible.
- Descripción.
- Instrucciones expresivas o estrategia de generación.
- Parámetros soportados por el modelo.
- Valores predeterminados.
- Límites válidos.
- Ejemplos de texto recomendados.

No se asumirán controles de emoción nativos que el modelo no ofrezca.

Si una emoción no puede controlarse directamente, se utilizará una estrategia explícita de aproximación mediante texto, parámetros compatibles o selección de referencias autorizadas.

### 4.5. Generación de voz

El usuario podrá introducir texto libre y generar audio.

La operación deberá:

1. Validar el texto.
2. Resolver el perfil expresivo.
3. Validar los parámetros.
4. Seleccionar una referencia permitida, cuando corresponda.
5. Ejecutar la inferencia.
6. Guardar el archivo de salida.
7. Registrar sus metadatos.
8. Devolver el resultado a la interfaz.

Se implementará generación individual y por lotes.

Los errores de inferencia no deben bloquear permanentemente la interfaz.

### 4.6. Historial y comparación

El usuario podrá consultar las generaciones anteriores, escuchar los archivos y comparar variantes de una misma frase.

Se conservarán las configuraciones empleadas para cada resultado.

La interfaz distinguirá claramente entre referencias originales y audio sintético.

### 4.7. Evaluación de generaciones

Una generación podrá enviarse al evaluador para obtener una evaluación independiente de su calidad y expresividad.

La evaluación se asociará al identificador de generación, al modelo evaluador y a su versión o identificador disponible.

Se evitarán llamadas repetidas al proveedor si el audio y la configuración de evaluación no han cambiado.

### 4.8. Exportación

Se permitirá exportar los metadatos y los audios seleccionados para su uso en el portafolio, siempre que su publicación esté autorizada.

La exportación no incluirá automáticamente referencias originales, claves API, rutas locales privadas ni archivos de configuración sensibles.

## 5. Arquitectura de software

### 5.1. Estilo arquitectónico

Monolito modular con separación por capas y puertos y adaptadores en las integraciones externas.

No se adoptará una implementación completa de DDD porque el MVP no requiere un dominio empresarial complejo.

### 5.2. Capas

Dominio:

- Entidades de referencia y generación.
- Perfiles expresivos.
- Estados de adquisición.
- Contratos y reglas independientes de la infraestructura.

Aplicación:

- Casos de uso de adquisición.
- Casos de uso de evaluación.
- Casos de uso de generación.
- Catálogo e historial.
- Orquestación de procesos.

Infraestructura:

- Cliente HTTP y parser de la wiki.
- Acceso a archivos.
- Adaptador Chatterbox.
- Adaptador del proveedor de IA.
- Persistencia JSON.
- Procesamiento técnico del audio.

Presentación:

- Interfaz Gradio.
- Validación de entradas de usuario.
- Visualización de estados y resultados.
- Reproducción y comparación.

### 5.3. Flujo de dependencias

La presentación invoca los servicios de aplicación.

Los servicios de aplicación dependen de contratos definidos por el proyecto.

La infraestructura implementa esos contratos.

El dominio no importa Gradio, SDK de proveedores, clientes HTTP ni clases específicas de Chatterbox.

### 5.4. Contratos principales

Se definirán interfaces o protocolos para:

- ReferenceSource.
- AudioStorage.
- SpeechGenerator.
- AudioEvaluator.
- ReferenceRepository.
- GenerationRepository.

Las implementaciones concretas se inyectarán desde el punto de composición de la aplicación.

### 5.5. Estructura inicial de archivos

```text
wheatley-voice-lab/
├── LLM-Context.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── configs/
│   ├── settings.toml
│   └── emotion_profiles.json
├── data/
│   ├── metadata/
│   ├── references/
│   ├── generated/
│   └── evaluations/
├── scripts/
│   ├── inspect_source.py
│   ├── acquire_references.py
│   ├── evaluate_audio.py
│   └── generate_batch.py
├── src/
│   └── voice_lab/
│       ├── __init__.py
│       ├── domain/
│       │   ├── models.py
│       │   ├── profiles.py
│       │   └── contracts.py
│       ├── application/
│       │   ├── acquisition_service.py
│       │   ├── evaluation_service.py
│       │   └── generation_service.py
│       ├── infrastructure/
│       │   ├── wiki/
│       │   │   ├── http_client.py
│       │   │   └── parser.py
│       │   ├── audio/
│       │   │   ├── validation.py
│       │   │   └── processing.py
│       │   ├── models/
│       │   │   └── chatterbox_adapter.py
│       │   ├── evaluation/
│       │   │   └── gemini_adapter.py
│       │   └── persistence/
│       │       ├── json_reference_repository.py
│       │       └── json_generation_repository.py
│       ├── presentation/
│       │   └── gradio_app.py
│       └── bootstrap.py
└── tests/
    ├── fixtures/
    ├── unit/
    ├── integration/
    └── conftest.py
```

Los archivos podrán reorganizarse si la implementación lo justifica, pero no se crearán módulos vacíos únicamente para aparentar una arquitectura completa.

## 6. Procedimiento de actuación del agente de código

### 6.1. Debug de errores

Ante un error:

1. Reproducirlo y obtener el traceback completo.
2. Identificar la capa y el componente responsable.
3. Determinar si se trata de un defecto de código, configuración, dependencia, datos o servicio externo.
4. Reducir el caso a una reproducción mínima.
5. Proponer una corrección que preserve los contratos existentes.
6. Añadir una prueba de regresión.
7. Ejecutar las pruebas relevantes.
8. Documentar la causa raíz y la evidencia de la corrección.

No se realizarán cambios indiscriminados de dependencias ni se ocultarán excepciones para hacer desaparecer el error.

### 6.2. Implementación de funcionalidades

Antes de implementar:

1. Revisar este documento y los módulos existentes.
2. Identificar los contratos afectados.
3. Comprobar las capacidades reales de las dependencias.
4. Definir entradas, salidas, estados y errores.
5. Implementar el caso de uso y su infraestructura.
6. Añadir pruebas unitarias y de integración cuando correspondan.
7. Verificar la funcionalidad mediante una ejecución reproducible.
8. Actualizar documentación y configuración si procede.

Las funcionalidades se implementarán de manera incremental, sin anticipar componentes futuros innecesarios.

### 6.3. Refactorización

Antes de refactorizar:

1. Identificar el problema concreto que justifica el cambio.
2. Revisar dependencias y consumidores.
3. Establecer pruebas de referencia.
4. Preservar el comportamiento observable, salvo que el cambio sea deliberado.
5. Mantener la separación entre dominio, aplicación, infraestructura y presentación.
6. Evitar introducir abstracciones que no resuelvan una necesidad real.
7. Ejecutar las pruebas afectadas y revisar el diff final.

Una refactorización no debe combinarse con cambios funcionales ajenos al objetivo.

### 6.4. Dependencias y APIs externas

- Consultar documentación oficial para comprobar las interfaces actuales.
- Fijar versiones compatibles y actualizar uv.lock.
- Mantener las llamadas remotas detrás de adaptadores.
- Aplicar timeouts y manejo explícito de límites y errores.
- No inventar parámetros de modelos ni asumir que una API ofrece funciones no documentadas.
- Mantener las claves API fuera del repositorio.
- Registrar el consumo y evitar llamadas redundantes.

### 6.5. Criterio de finalización de una tarea

Una tarea estará completada cuando:

- El código esté implementado.
- Se hayan ejecutado las pruebas pertinentes.
- No existan errores conocidos introducidos por el cambio.
- Los contratos y tipos sean coherentes.
- La configuración y documentación estén actualizadas.
- Se informe de cualquier limitación no resuelta.

No se afirmará que una tarea está validada si solo se ha revisado el código sin ejecutarlo.

## 7. Variables de entorno

El archivo .env.example documentará las variables admitidas sin incluir secretos.

Variables previstas:

- GEMINI_API_KEY.
- GEMINI_MODEL.
- DATA_DIR.
- REFERENCE_DIR.
- GENERATED_DIR.
- EVALUATION_DIR.
- SOURCE_BASE_URL.
- HTTP_TIMEOUT_SECONDS.
- HTTP_REQUEST_DELAY_SECONDS.
- MAX_DOWNLOAD_BYTES.
- MAX_RETRIES.
- LOG_LEVEL.

Los valores predeterminados deberán ser conservadores. Las rutas se resolverán desde una configuración centralizada.

La configuración de cómputo del modelo se determinará después de verificar el hardware y la compatibilidad de PyTorch.

## 8. Criterios generales de calidad

- Tipado explícito en las interfaces públicas.
- Funciones pequeñas y con responsabilidades delimitadas.
- Sin credenciales ni rutas privadas versionadas.
- Sin solicitudes HTTP en las pruebas unitarias del parser.
- Sin dependencia de un proveedor concreto en el dominio.
- Sin llamadas remotas innecesarias.
- Sin publicación automática de referencias originales.
- Sin afirmar que una emoción se controla de manera nativa si solo se aproxima.
- Sin declarar completada una integración que no se haya probado.
- Documentación actualizada junto al código.

El objetivo es obtener un laboratorio local, reproducible y extensible, capaz de adquirir referencias permitidas, evaluarlas y generar voz expresiva en español de España mediante una interfaz interactiva.

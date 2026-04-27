# Guia Paso a Paso para Desarrollar el Sistema RAG a Gran Escala

Este documento traduce el contenido de PROJECT_BRIEF.md a un plan de implementacion ejecutable, con fases, entregables, validaciones y criterios de exito.

## 1. Resultado Esperado

Construir una aplicacion web desplegada en GCP que:

1. Ingiera mas de 100 PDFs desde GCS.
2. Procese texto y genere embeddings de forma distribuida con PySpark.
3. Persista embeddings y metadatos en Milvus.
4. Responda preguntas con arquitectura RAG usando Groq, minimizando tokens.
5. Exponga una UI web para consulta con citas a fuentes.

## 2. Arquitectura Objetivo

Flujo de alto nivel:

1. Usuario sube o referencia PDFs en GCS.
2. Job PySpark ejecuta ETL: lectura PDF, limpieza, chunking, embedding, upsert en Milvus.
3. Usuario pregunta desde UI.
4. n8n recibe consulta por webhook/API.
5. Servicio de recuperacion obtiene Top-K chunks desde Milvus.
6. n8n construye prompt con contexto y llama a Groq.
7. Respuesta vuelve a UI con trazabilidad (paper/chunk).

## 3. Prerrequisitos

### 3.1 Infraestructura y cuentas

1. Proyecto en GCP con facturacion activa.
2. Cuenta de servicio con permisos minimos para:
   - Cloud Storage (lectura/escritura segun rol).
   - Dataproc o entorno Spark elegido.
   - Secret Manager.
   - Logging/Monitoring.
3. API key de Groq almacenada en Secret Manager.

### 3.2 Herramientas locales

1. gcloud CLI.
2. Docker + Docker Compose.
3. Python 3.10+.
4. Entorno para PySpark.
5. Cliente de Milvus para Python.

## 4. Estructura Recomendada del Repositorio

Propuesta minima:

```text
infra/
  docker/
    docker-compose.milvus-n8n.yml
  gcp/
    variables.env.example

etl/
  spark_job/
    main.py
    chunking.py
    embedding.py
    milvus_writer.py
    requirements.txt

backend/
  retrieval_service/
    app.py
    milvus_search.py
    prompt_builder.py

orchestration/
  n8n/
    workflow.rag.json

frontend/
  app/
    (Streamlit o FastAPI+React)

docs/
  runbook.md
  pruebas_aceptacion.md
```

## 5. Paso a Paso de Implementacion

### Paso 1. Preparar recursos base en GCP

Objetivo: dejar lista la base de nube para ETL y ejecucion.

1. Crear buckets de GCS:
   - Bucket de entrada de PDFs (raw).
   - Bucket de artefactos temporales/resultados ETL.
2. Definir convencion de rutas:
   - gs://bucket-raw/<dominio>/<paper>.pdf
   - gs://bucket-processed/chunks/<fecha>/...
3. Configurar secretos:
   - GROQ_API_KEY
   - MILVUS_URI, MILVUS_USER, MILVUS_PASSWORD
4. Crear entorno de ejecucion Spark:
   - Opcion A: Cloud Dataproc (recomendado para escala).
   - Opcion B: cluster autogestionado con Spark en GCP.

Entregable:

1. Buckets creados y accesibles.
2. Secretos creados y accesibles por cuentas de servicio.
3. Entorno Spark operativo.

### Paso 2. Levantar Milvus y n8n en GCP

Objetivo: dejar operativos los servicios de vector DB y orquestacion.

1. Desplegar Milvus en VM, GKE o entorno contenedorizado en GCP.
2. Desplegar n8n en contenedor separado.
3. Configurar red y puertos internos/externos con politicas restrictivas.
4. Habilitar persistencia de volumen para Milvus y backup plan.

Recomendaciones:

1. Empezar con Docker Compose para staging.
2. Pasar a GKE o arquitectura administrada para produccion.

Entregable:

1. Endpoint de Milvus accesible desde ETL y backend.
2. n8n accesible para administrar workflows.

### Paso 3. Diseñar esquema de datos en Milvus

Objetivo: crear una coleccion optimizada para busqueda semantica y trazabilidad.

Campos recomendados por registro (chunk):

1. chunk_id (PK).
2. paper_id.
3. paper_title.
4. section.
5. chunk_text.
6. embedding (vector float, dimension fija).
7. page_start / page_end.
8. source_uri (ruta en GCS).
9. ingestion_ts.

Indices sugeridos:

1. Indice vectorial adecuado a volumen y latencia objetivo.
2. Particion por dominio o lote de ingesta si aplica.

Entregable:

1. Coleccion creada.
2. Politica de indices y particiones documentada.

### Paso 4. Implementar ETL distribuido en PySpark

Objetivo: cumplir CA 1 con procesamiento masivo y escritura eficiente.

Subpasos:

1. Lectura distribuida de PDFs desde GCS.
2. Extraccion de texto por documento (manejo de PDFs escaneados, errores y reintentos).
3. Limpieza y normalizacion minima del texto.
4. Chunking configurable:
   - chunk_size (ej. 700 a 1200 tokens aprox).
   - overlap (ej. 80 a 200 tokens).
5. Generacion de embeddings en paralelo.
6. Insercion batch a Milvus:
   - lotes controlados para no saturar red.
   - reintentos exponenciales.
   - logs de throughput y errores.
7. Estrategia de idempotencia:
   - hash de chunk.
   - control de duplicados por paper_id + hash.

Buenas practicas:

1. Evitar collect() en DataFrames grandes.
2. Persistir checkpoints para recovery.
3. Registrar metadatos de trazabilidad desde ETL.

Entregable:

1. Job Spark ejecutable por parametro (ruta bucket, chunk size, topicos, etc.).
2. +100 PDFs ingeridos con registros validos en Milvus.

### Paso 5. Construir servicio de recuperacion semantica

Objetivo: cumplir CA 2 con latencia menor a 500 ms para Top-K.

Subpasos:

1. Exponer endpoint de consulta interna (ej. /retrieve).
2. Convertir pregunta del usuario a embedding con el mismo modelo usado en indexacion.
3. Consultar Milvus con Top-K configurable (5 a 10).
4. Devolver chunks + score + metadatos de cita.
5. Medir latencia p50/p95 y ajustar:
   - tipo de indice.
   - parametros de busqueda.
   - tamano de coleccion por particion.

Entregable:

1. API interna de retrieval estable.
2. Benchmark documentado con cumplimiento de latencia objetivo.

### Paso 6. Implementar workflow n8n (RAG orchestration)

Objetivo: cumplir CA 3 con flujo extremo a extremo.

Flujo minimo del workflow:

1. Webhook recibe pregunta del usuario.
2. Nodo de validacion/sanitizacion de input.
3. Nodo HTTP al servicio de retrieval.
4. Nodo de construccion de prompt.
5. Nodo HTTP a API de Groq.
6. Nodo de postproceso y respuesta.

Plantilla de prompt del sistema (anti alucinacion):

1. Instruir que responda solo con evidencia del contexto.
2. Si no hay evidencia suficiente: responder exactamente
   "No hay informacion suficiente en los documentos proporcionados".
3. Incluir citas por source_uri, paper_title y chunk_id.

Entregable:

1. Workflow versionado (export JSON).
2. Endpoint funcional para preguntas.

### Paso 7. Desarrollar la interfaz web

Objetivo: cumplir CA 4 con experiencia clara para usuario final.

Funciones minimas:

1. Caja de consulta.
2. Boton de envio.
3. Panel de respuesta del LLM.
4. Seccion de referencias:
   - paper.
   - chunk_id.
   - score.
5. Manejo de errores y estado de carga.

Recomendaciones UX:

1. Mostrar tiempo de respuesta total.
2. Permitir expandir contexto recuperado por chunk.
3. Diferenciar claramente respuesta y evidencia.

Entregable:

1. UI accesible desde navegador.
2. Integracion con webhook/API de n8n.

### Paso 8. Observabilidad, seguridad y costos

Objetivo: operar en nube de forma confiable.

Checklist tecnico:

1. Logging estructurado para ETL, retrieval, n8n y frontend.
2. Metricas de negocio y sistema:
   - latencia retrieval.
   - latencia total.
   - tasa de "sin informacion suficiente".
   - costo estimado por consulta.
3. Secretos en Secret Manager (no hardcode).
4. IAM de minimo privilegio.
5. Limites y alertas de gasto en GCP.

Entregable:

1. Dashboard basico de operacion.
2. Alertas de fallos criticos y sobrecostos.

### Paso 9. Pruebas de aceptacion (DoD)

Validar exactamente los 4 criterios del brief:

1. CA 1 Ingesta:
   - Prueba con +100 PDFs.
   - Validar conteo de chunks, errores y tasa de insercion.
2. CA 2 Recuperacion:
   - Ejecutar bateria de consultas de control.
   - Confirmar Top 5-10 en <500 ms.
3. CA 3 Orquestacion:
   - Disparar webhook en n8n con preguntas reales.
   - Verificar armado de prompt y respuesta de Groq.
4. CA 4 UI:
   - Probar flujo de consulta completo desde navegador.
   - Confirmar visualizacion de citas/referencias.

Entregable:

1. Documento de pruebas con evidencia (capturas, logs, metricas).

### Paso 10. Plan de ejecucion sugerido (4 semanas)

Semana 1:

1. Infra GCP base.
2. Milvus + n8n desplegados.
3. Esquema de coleccion definido.

Semana 2:

1. ETL PySpark completo.
2. Primera ingesta piloto (10 a 20 PDFs).
3. Ajuste de chunking y embeddings.

Semana 3:

1. Retrieval API + benchmark latencia.
2. Workflow n8n con Groq.
3. Prompting anti alucinacion.

Semana 4:

1. Frontend integrado.
2. Pruebas CA 1-4.
3. Hardening (observabilidad, seguridad, costo).

## 6. Riesgos Frecuentes y Mitigaciones

1. Latencia alta de retrieval:
   - Ajustar indice Milvus, particiones y parametros de busqueda.
2. Costo de inferencia alto:
   - Reducir Top-K y longitud de chunks.
   - Aplicar recorte de contexto antes de Groq.
3. Hallazgos irrelevantes:
   - Mejorar limpieza/segmentacion.
   - Ajustar modelo de embedding.
4. Alucinaciones:
   - Endurecer prompt del sistema.
   - Exigir respuesta de "sin informacion suficiente" cuando aplique.

## 7. Definicion de Listo para Produccion

El sistema esta listo para produccion cuando:

1. Cumple CA 1, CA 2, CA 3 y CA 4 con evidencia.
2. Tiene monitoreo y alertas activos.
3. Secretos e IAM cumplen minimo privilegio.
4. Existe runbook de operacion y recuperacion ante fallos.

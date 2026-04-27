***

# Documento de Especificación: Sistema RAG a Gran Escala (Multi-Paper Analytics)

## 1. Objetivo del Proyecto
Desarrollar y desplegar una aplicación web nativa en la nube (Google Cloud Platform) capaz de ingerir, procesar y analizar una biblioteca de más de 100 documentos académicos (papers) de un dominio específico de forma simultánea. El sistema funcionará como un asistente de investigación avanzado (similar a NotebookLM) utilizando la arquitectura RAG (Retrieval-Augmented Generation) para responder consultas complejas basándose estrictamente en el corpus proporcionado, minimizando el consumo de tokens y garantizando baja latencia.

## 2. Stack Tecnológico Definido
* **Proveedor Cloud:** Google Cloud Platform (GCP).
* **Almacenamiento de Datos en Crudo:** Google Cloud Storage (GCS) para los PDFs.
* **Procesamiento y ETL:** PySpark (vía Cloud Dataproc o clúster autogestionado) para la extracción de texto, *chunking* y generación distribuida de *embeddings*.
* **Base de Datos Vectorial:** Milvus (desplegado en GCP).
* **Motor de Inferencia (LLM):** API de Groq (modelos open-source de alta velocidad).
* **Orquestación Lógica:** n8n para enlazar flujos de trabajo entre la base de datos, el LLM y el frontend.
* **Interfaz de Usuario:** Aplicación web (ej. Streamlit o FastAPI + React).

## 3. Restricciones Técnicas y de Arquitectura
1.  **Procesamiento Distribuido Obligatorio:** Debido al volumen de documentos, la ingesta y vectorización no debe hacerse en un bucle secuencial en memoria simple. Se debe utilizar PySpark para paralelizar la carga de trabajo.
2.  **Almacenamiento Vectorial Escalable:** Se prohíbe el uso de bases de datos vectoriales embebidas o en memoria local (como la versión básica de ChromaDB). Todo vector debe persistirse en Milvus.
3.  **Eficiencia de Tokens:** El sistema no enviará documentos completos al LLM. Debe extraer y enviar únicamente el "Top-K" de los *chunks* más relevantes obtenidos mediante búsqueda semántica (similitud de coseno/distancia euclidiana) en Milvus.
4.  **Aislamiento de la Nube:** Todos los servicios (PySpark, Milvus, n8n, Frontend) deben ser contenerizados y/o configurados para ejecutarse en el ecosistema de GCP.
5.  **Control de Alucinaciones:** El *prompt* del sistema enviado a Groq debe instruir estrictamente al modelo a responder "No hay información suficiente en los documentos proporcionados" si la respuesta no se encuentra en el contexto inyectado.

## 4. Criterios de Aceptación (DoD - Definition of Done)
El proyecto se considerará exitoso cuando cumpla con los siguientes hitos operativos:

* **CA 1 (Ingesta):** Un *script* de PySpark lee exitosamente un lote de +100 PDFs desde un *bucket* de GCS, extrae el texto, lo divide en fragmentos superpuestos de tamaño configurable, genera los *embeddings* de cada fragmento y los inserta de forma masiva (batch) en Milvus sin saturar la red.
* **CA 2 (Recuperación):** Al realizar una consulta en lenguaje natural, el sistema convierte la pregunta en un vector y recupera los 5 a 10 fragmentos más relevantes de Milvus en menos de 500 milisegundos.
* **CA 3 (Orquestación):** Un *workflow* en n8n recibe un *webhook* (o llamada de API) con la pregunta del usuario, consulta a Milvus, estructura el *prompt* con el contexto recuperado, llama a la API de Groq, y devuelve la respuesta final formateada.
* **CA 4 (Interfaz UI):** Existe una interfaz web accesible mediante navegador donde un usuario final puede escribir una consulta y leer la respuesta generada por el LLM, incluyendo citas o referencias a qué *chunks* o *papers* se utilizaron para generar dicha respuesta.

## 5. Fases de Ejecución Sugeridas para el Agente
*(Instrucción para el Custom Agent: "Debes abordar la construcción del código siguiendo este orden estricto")*
1.  **Fase de Infraestructura As-Code / Configuración:** *Docker-compose* o *manifests* para levantar Milvus y n8n en el servidor.
2.  **Fase ETL de Datos:** Escritura del *job* de PySpark para procesamiento masivo y conexión a Milvus.
3.  **Fase de Backend/Integración:** Construcción del flujo en n8n y configuración de los nodos HTTP para conectar con Groq.
4.  **Fase de Frontend:** Desarrollo de la interfaz de usuario y conexión con el *webhook* de n8n.

***
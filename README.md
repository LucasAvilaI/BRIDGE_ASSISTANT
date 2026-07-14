# Arquitectura de config.py

## Objetivo

Centralizar toda la configuración estática utilizada por la
arquitectura base del Employee Onboarding Assistant.

config.py no implementa lógica de negocio.
No realiza llamadas al modelo.
No procesa información.
No valida entradas.

Su única responsabilidad es actuar como contrato compartido
entre context.py, logic.py y main.py.

---

## Módulos consumidores

context.py

- rutas
- pesos
- límites
- documentos transversales

logic.py

- perfiles
- categorías
- escalación
- configuración general

main.py

- rutas

---

## Decisiones de diseño

Toda decisión dinámica pertenece a logic.py.

Toda selección documental pertenece a context.py.

Toda interacción con el modelo pertenece al área LLM.

Toda validación avanzada pertenece al área Robustez.

---

## Integraciones pendientes

### LLM & Benchmark

Pendiente de integrar:

- modelo
- temperaturas
- generación JSON
- métricas
- benchmarking

### Robustez

Pendiente de integrar:

- patrones sospechosos
- validaciones avanzadas
- prompt defensivo
- variantes segura/vulnerable

---

## Filosofía

config.py debe permanecer estable durante todo el ciclo
de vida del proyecto.

Los cambios funcionales deben producirse en logic.py o
context.py, evitando modificar la configuración salvo que
aparezcan nuevos requisitos del dominio.

-------------------------------------------------------------------------------------------------------------------------------------

# Arquitectura de `logic.py`

## Objetivo

`logic.py` actúa como orquestador de la arquitectura base del Employee Onboarding Assistant.

Su responsabilidad es coordinar los datos del empleado, la configuración, el contexto documental y el estado conversacional para construir un contrato estable entre la lógica de negocio y el área encargada del modelo de lenguaje.

`logic.py` no implementa la selección documental, no construye prompts definitivos, no llama directamente a un proveedor LLM y no aplica defensas avanzadas de seguridad.

---

## Responsabilidades

`logic.py` es responsable de:

- Validar la estructura mínima de los datos recibidos.
- Calcular el día de onboarding del empleado.
- Clasificar preliminarmente la consulta.
- Seleccionar el perfil funcional adecuado.
- Solicitar el contexto documental a `context.py`.
- Recuperar el historial reciente desde `state.py`.
- Construir un paquete de interacción independiente del proveedor LLM.
- Recibir una respuesta externa ya generada.
- Validar el contrato mínimo de esa respuesta.
- Actualizar el estado conversacional.
- Devolver una respuesta estándar a `main.py`.

---

## Qué no hace

`logic.py` no debe:

- Construir el prompt definitivo.
- Elegir modelo o proveedor.
- Definir temperaturas.
- Contar tokens.
- Ejecutar llamadas a Gemini, OpenAI o Hugging Face.
- Implementar JSON Mode.
- Registrar benchmarks.
- Detectar prompt injection.
- Detectar jailbreaks.
- Aplicar listas de bloqueo.
- Implementar flujos seguro o vulnerable.
- Puntuar documentos o FAQ.
- Duplicar datos permanentes del empleado dentro del estado.

Estas responsabilidades pertenecen a otros módulos o áreas del proyecto.

---

# Separación del procesamiento en dos fases

## Problema detectado

El esqueleto heredado del Sprint 6 mezclaba en una misma función:

- lógica de negocio;
- construcción de prompts;
- selección de perfil;
- llamada al modelo;
- seguridad;
- parseo de respuesta;
- actualización del estado.

Ese diseño acoplaba `logic.py` a:

- un proveedor concreto;
- unas firmas concretas de `prompts.py`;
- unas constantes concretas de `config.py`;
- el dominio antiguo del tutor de Python;
- las decisiones de Robustez;
- las decisiones de LLM y Benchmark.

Cualquier cambio de modelo, prompt o estrategia de seguridad obligaba a modificar el orquestador central.

---

## Solución adoptada

El procesamiento del turno se divide en dos fases independientes:

preparar_turno()
        ↓
adaptador LLM pendiente
        ↓
finalizar_turno()

Fase 1: preparar_turno()
Responsabilidad

Transforma los datos de entrada en un paquete de interacción estable e independiente del proveedor LLM.

Operaciones

La función:

Valida el contrato mínimo de entrada.
Calcula el día de onboarding.
Clasifica preliminarmente la consulta.
Selecciona el perfil funcional.
Solicita el contexto documental a context.py.
Obtiene el historial reciente.
Construye el paquete de interacción.
Devuelve el resultado mediante la envolvente estándar.
No conoce

preparar_turno() no conoce:

Gemini;
OpenAI;
Hugging Face;
temperaturas;
prompts;
JSON Mode;
métricas;
benchmarks;
estrategias seguras o vulnerables.
Fase 2: finalizar_turno()
Responsabilidad

Recibe el turno preparado y la respuesta externa generada por el área LLM.

Operaciones

La función:

Valida la estructura mínima del turno preparado.
Valida el contrato mínimo de la respuesta externa.
Añade la consulta al historial.
Añade la respuesta del asistente.
Incrementa el número de turnos mediante state.py.
Devuelve la respuesta estándar del proyecto.
Independencia del proveedor

La función no necesita conocer:

cómo se construyó el prompt;
qué modelo respondió;
qué proveedor se utilizó;
qué temperatura se aplicó;
si hubo JSON Mode;
qué estrategia de seguridad se ejecutó.

Funciones públicas
respuesta_ok()

Construye la envolvente estándar de éxito.

Contrato
{
    "status": "ok",
    "mensaje": str,
    "data": dict,
}
respuesta_error()

Construye la envolvente estándar de error.

Contrato
{
    "status": "error",
    "mensaje": str,
    "data": {
        "errores": list[str],
    },
}
preparar_turno()

Entrada principal de la arquitectura base antes de invocar el modelo.

Entrada prevista
preparar_turno(
    estado: dict,
    consulta: str,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    configuracion: dict | None = None,
    fecha_referencia: date | None = None,
) -> dict
Salida

Devuelve una envolvente estándar.

Cuando el turno se prepara correctamente:

{
    "status": "ok",
    "mensaje": "Turno preparado",
    "data": {
        "turno_preparado": {
            ...
        }
    },
}
finalizar_turno()

Entrada pública utilizada después de recibir la respuesta externa.

Entrada prevista
finalizar_turno(
    estado: dict,
    turno_preparado: dict,
    resultado_externo: dict,
) -> dict
Salida
{
    "status": "ok",
    "mensaje": "Turno finalizado",
    "data": {
        "respuesta": str,
        "resultado": dict,
        "perfil_activo": str,
        "categoria": str,
        "dia_onboarding": int,
    },
}
Contrato del paquete de interacción

El paquete construido por preparar_turno() representa la frontera entre la Arquitectura Base y el área LLM.

Estructura
{
    "consulta": str,
    "empleado": dict,
    "empresa": dict,
    "perfil_activo": str,
    "perfil": dict,
    "categoria_preliminar": str,
    "dia_onboarding": int,
    "contexto": {
        "empleado": dict,
        "documentos": list[dict],
        "faqs": list[dict],
        "document_ids": list[str],
        "faq_ids": list[str],
        "hay_contexto": bool,
    },
    "historial": list[dict],
    "configuracion": dict,
}
Motivo del contrato

Este objeto no es un prompt ni una petición de proveedor.

Es un contrato de dominio.

El área LLM podrá convertirlo después en:

un prompt de texto;
mensajes de chat;
una petición JSON;
una entrada para Gemini;
una entrada para otro proveedor.

La Arquitectura Base no necesita cambiar si cambia la tecnología utilizada para generar la respuesta.

Validaciones de arquitectura
Validaciones realizadas por logic.py

logic.py valida únicamente las precondiciones necesarias para ejecutar el flujo:

estado debe ser un diccionario.
consulta debe ser un string no vacío.
empleado debe ser un diccionario.
empresa debe ser un diccionario.
documentos debe ser una lista.
faqs debe ser una lista.
configuracion, si se proporciona, debe ser un diccionario.
El perfil configurado debe existir.
Los límites de historial y contexto deben ser enteros no negativos.
La respuesta externa debe ser un diccionario.
La respuesta externa debe contener el contrato mínimo requerido.
Validaciones delegadas a context.py

context.py mantiene la responsabilidad sobre:

listas de documentos;
listas de FAQ;
estructura general de sus entradas;
puntuación;
selección;
combinación;
construcción del contexto documental.

logic.py no duplica esas validaciones.

Validaciones excluidas

No se implementan en logic.py:

longitud máxima del mensaje;
patrones sospechosos;
prompt injection;
jailbreak;
sanitización avanzada;
sensibilidad documental;
permisos;
ataques adversariales.

Estas validaciones pertenecen al área de Robustez.

Estado conversacional
Decisión

Los datos permanentes del empleado no se almacenan dentro del estado.

El empleado ya existe en empleados_demo.json y se recibe como argumento.

Duplicarlo dentro del estado produciría:

riesgo de desincronización;
duplicación de responsabilidades;
inconsistencias entre sesiones;
mayor acoplamiento.
Contenido esperado del estado
{
    "messages": list[dict],
    "turnos": int,
}

El estado almacena únicamente información conversacional.

No almacena:

empleado;
empresa;
documentos;
FAQ;
perfil funcional;
categoría;
configuración.
Cálculo del día de onboarding
Formato esperado

El campo del empleado debe llamarse:

fecha_inicio

El valor debe estar en formato ISO:

AAAA-MM-DD
Regla
día de onboarding = días transcurridos desde fecha_inicio + 1

Ejemplos:

fecha de incorporación = hoy
día de onboarding = 1
fecha de incorporación = ayer
día de onboarding = 2
Fechas futuras

Cuando fecha_inicio es posterior a la fecha de referencia, se utiliza el día 1.

Esto evita valores negativos y permite preparar el onboarding antes de la incorporación.

Fecha ausente o inválida

Se considera un error estructural.

La arquitectura no debe seleccionar perfiles temporales utilizando una fecha desconocida o mal formada.

Fecha de referencia

Por defecto se utiliza la fecha actual.

La función acepta opcionalmente una fecha de referencia para:

pruebas;
demos;
benchmarks;
resultados deterministas.
Clasificación preliminar
Función
clasificar_consulta(consulta: str) -> str
Fuente

Utiliza:

DOMAIN_KEYWORDS

definido en config.py.

Proceso
Normaliza la consulta.
Compara las palabras y expresiones de cada categoría.
Cuenta las coincidencias.
Selecciona la categoría con mayor puntuación.
Resuelve empates de forma determinista.
Devuelve "general" cuando no existen coincidencias.
Alcance

La clasificación es preliminar.

No representa necesariamente la categoría final de la respuesta externa.

Su finalidad es:

seleccionar el perfil funcional;
aportar una señal al área LLM;
facilitar la escalación;
mantener trazabilidad del proceso.
out_of_scope

logic.py no clasifica automáticamente una consulta como out_of_scope usando únicamente palabras clave.

Esa decisión requiere contexto adicional y puede corresponder al área LLM o Robustez.

Selección del perfil funcional
Prioridad

La selección sigue este orden:

1. Consulta IT
   → perfil "it"

2. Consulta RRHH
   → perfil "administrativo_rrhh"

3. Resto de consultas durante los días 1 a 7
   → perfil "onboarding"

4. Resto de consultas desde el día 8
   → perfil "administrativo_rrhh"
Motivo

La categoría funcional tiene prioridad sobre la antigüedad.

Un empleado en su primer día que pregunta por VPN o credenciales necesita una respuesta técnica accesible.

Un empleado en su segundo día que pregunta por vacaciones necesita una respuesta administrativa.

El perfil temporal de onboarding se aplica cuando no existe un dominio funcional más específico.

Día 30

MAX_ONBOARDING_DAYS describe el periodo inicial del producto, pero no bloquea el acceso al asistente después de ese límite.

Desde el día 31 se sigue utilizando:

perfil IT para consultas técnicas;
perfil administrativo para el resto.
Relación con context.py

logic.py trata context.py como un servicio independiente.

La única operación de alto nivel necesaria es:

construir_contexto(...)

logic.py no conoce ni replica:

puntuación de FAQ;
puntuación documental;
normalización de tags;
selección directa;
prioridad de documentos asociados;
desduplicación;
límites internos.

Esto preserva la responsabilidad única de cada módulo.

Relación con state.py

logic.py puede reutilizar:

append_user()
append_assistant()
ultimos_n()

Estas funciones son compatibles con el estado conversacional previsto.

No se utilizará:

actualizar_perfil_desde_mensaje()

Motivo:

pertenece al tutor antiguo;
intenta inferir datos permanentes desde el mensaje;
duplica información del empleado;
mezcla conversación con perfil de dominio.

No es necesario modificar state.py.

Puntos descartados del esqueleto del Sprint 6

Se descartan:

crear_estado_demo()
demo_seleccion_faq()
parsear_respuesta_tutor()
procesar_turno_seguro()
procesar_turno_vulnerable()
actualizar_perfil_desde_mensaje()
parece_dominio_python()
rechazo_fuera_de_dominio()
validate_input()
build_secure_prompt()
build_vulnerable_prompt()
build_assistant_prompt()
safe_generate()
MetricasLlamada
Motivo

Estas piezas están vinculadas a:

el tutor de Python;
el esquema antiguo de FAQ;
perfiles junior, senior y mentor;
prompts heredados;
llamadas directas a Gemini;
seguridad;
benchmarking;
contratos externos todavía no integrados.

No forman parte de la Arquitectura Base actual.

Integración pendiente: área LLM y Benchmark
Responsabilidad

El área LLM deberá implementar un adaptador que reciba el paquete generado por:

preparar_turno()

y produzca un resultado externo compatible con:

finalizar_turno()
Entrada del adaptador
turno_preparado: dict
Salida mínima esperada
{
    "in_scope": bool,
    "category": str,
    "answer": str,
}

Podrá incluir además:

{
    "document_ids": list[str],
    "faq_ids": list[str],
    "needs_escalation": bool,
    "escalation_department": str | None,
    "metricas": dict | None,
}
Trabajo pendiente

El área LLM deberá decidir:

modelo;
proveedor;
temperatura;
prompt;
formato estructurado;
control de tokens;
métricas;
benchmarking;
validación completa del contrato generado.
Integración pendiente: área de Robustez
Responsabilidad

El área de Robustez podrá intervenir entre:

preparar_turno()
        ↓
adaptador LLM

o envolver el flujo completo.

Trabajo pendiente
Validación avanzada de entrada.
Longitud máxima.
Detección de prompt injection.
Detección de jailbreak.
Protección del prompt.
Control de contenido.
Revisión de permisos.
Flujo seguro.
Flujo vulnerable.
Comparativa entre variantes.
Restricción arquitectónica

No deben crearse duplicados como:

logic_vulnerable.py
logic_seguro.py
context_vulnerable.py

Las variantes deben reutilizar el mismo contrato de turno y aplicarse mediante:

funciones específicas;
adaptadores;
estrategias;
envoltorios del flujo común.
Función futura de conveniencia

Cuando las otras áreas estén integradas podrá añadirse:

procesar_turno(...)

Flujo previsto:

preparar_turno()
        ↓
validación de Robustez
        ↓
adaptador LLM
        ↓
finalizar_turno()

Esta función no forma parte de la implementación actual porque su comportamiento depende de componentes todavía no integrados dentro del proyecto (adaptador LLM y validaciones de Robustez).

La separación actual evita introducir dependencias provisionales o contratos no acordados.

Gestión de errores
Errores previsibles

Las funciones públicas convierten los errores previsibles en:

respuesta_error(...)

Ejemplos:

consulta vacía;
configuración inválida;
empleado sin fecha;
fecha inválida;
perfil desconocido;
documentos o FAQ mal formados;
respuesta externa incompleta.
Errores inesperados

No se utiliza:

except Exception

de forma general.

Los errores inesperados deben propagarse durante el desarrollo para facilitar su detección y corrección.

Filosofía de diseño

logic.py debe permanecer estable aunque cambie:

el modelo;
el proveedor;
el prompt;
el modo de respuesta;
la temperatura;
la estrategia de seguridad;
el benchmark.

La Arquitectura Base define el dominio y sus contratos.

Las otras áreas se conectan a esos contratos sin modificar la lógica central.

Esta separación:

reduce acoplamiento;
evita duplicación;
facilita pruebas;
permite integrar distintos proveedores;
mantiene claras las responsabilidades del equipo;
protege la arquitectura frente a cambios futuros.


-------------------------------------------------------------------------------------------------------------------------------------

# Arquitectura de `context.py`

## Objetivo

`context.py` es el módulo responsable de la recuperación, selección y preparación del contexto documental utilizado por el Employee Onboarding Assistant.

Su responsabilidad consiste en transformar una consulta y la información del empleado en un conjunto reducido de documentos y FAQ relevantes, minimizando el contexto que posteriormente consumirá el área LLM.

El módulo no conoce el modelo de lenguaje, no construye prompts y no participa en la generación de respuestas.

---

# Responsabilidades

`context.py` es responsable de:

- Cargar información desde los archivos JSON.
- Validar la estructura general de las fuentes.
- Normalizar texto y etiquetas.
- Buscar empleados.
- Calcular la relevancia de FAQ.
- Seleccionar FAQ.
- Calcular la relevancia documental.
- Seleccionar documentos.
- Resolver documentos asociados a FAQ.
- Desduplicar información.
- Construir el contexto documental final.

---

# Qué no hace

`context.py` no debe:

- Llamar a Gemini, OpenAI o cualquier proveedor LLM.
- Construir prompts.
- Elegir modelos.
- Seleccionar temperaturas.
- Gestionar historial conversacional.
- Decidir perfiles funcionales.
- Clasificar definitivamente la consulta.
- Aplicar estrategias de benchmarking.
- Aplicar validaciones de Robustez.
- Detectar prompt injection.
- Detectar jailbreak.
- Gestionar permisos avanzados.
- Implementar variantes segura o vulnerable.

Toda esa funcionalidad pertenece a otros módulos de la arquitectura.

---

# Filosofía del módulo

La finalidad de `context.py` no es responder preguntas.

Su única misión consiste en responder una pregunta interna:

> ¿Cuál es la información mínima necesaria para responder correctamente esta consulta?

El resultado siempre será un contexto reducido, coherente y relevante.

Nunca una respuesta al usuario.

---

# API pública

El módulo expone las siguientes funciones públicas.

## `cargar_json()`

Carga un archivo JSON desde disco.

Responsabilidades:

- comprobar existencia;
- comprobar que sea un archivo;
- validar el JSON;
- devolver lista o diccionario.

No interpreta el contenido.

---

## `buscar_empleado()`

Localiza un empleado mediante su identificador.

La búsqueda:

- ignora mayúsculas;
- ignora acentos;
- utiliza comparación normalizada.

---

## `validar_lista_diccionarios()`

Comprueba únicamente la estructura general de una fuente.

No valida esquemas específicos.

---

## `normalizar_texto()`

Normaliza cadenas para facilitar las comparaciones.

Operaciones:

- minúsculas;
- eliminación de acentos;
- sustitución de separadores;
- eliminación de espacios duplicados.

Esta función puede reutilizarse desde otros módulos.

---

## `seleccionar_faq()`

Recupera las FAQ más relevantes para una consulta.

Las FAQ funcionan como índice documental.

No constituyen la fuente principal de información.

---

## `seleccionar_documentos()`

Recupera los documentos más relevantes.

Los documentos representan la fuente autorizada del sistema.

---

## `construir_contexto()`

Es la puerta de entrada principal del módulo.

Todo consumidor externo deberá utilizar esta función.

No se recomienda construir contextos llamando directamente a las funciones internas.

---

# Funciones auxiliares

Las siguientes funciones forman parte del algoritmo interno de recuperación.

No deben considerarse parte del contrato principal del módulo.

- `puntuar_faq()`
- `puntuar_documento()`
- `normalizar_tags()`
- `extraer_palabras()`
- `extraer_palabras_tags()`
- `obtener_documento_por_id()`
- `combinar_documentos()`

Se mantienen públicas únicamente para preservar compatibilidad entre ramas y facilitar pruebas unitarias.

---

# Contrato de `construir_contexto()`

## Entrada

```python
construir_contexto(
    consulta,
    empleado,
    documentos,
    faqs,
    limite_documentos,
    limite_faqs,
)
```

---

## Salida

```python
{
    "empleado": dict,
    "documentos": list[dict],
    "faqs": list[dict],
    "document_ids": list[str],
    "faq_ids": list[str],
    "hay_contexto": bool,
}
```

Este contrato debe permanecer estable.

Los módulos consumidores no necesitan conocer el algoritmo utilizado para generar dicho contexto.

---

# Flujo interno

El algoritmo sigue siempre el mismo pipeline.

```text
consulta
        │
        ▼
normalización
        │
        ▼
selección FAQ
        │
        ▼
selección documental
        │
        ▼
resolución de documentos asociados
        │
        ▼
desduplicación
        │
        ▼
aplicación de límites
        │
        ▼
contexto final
```

Cada fase posee una responsabilidad única.

---

# Recuperación documental

El algoritmo prioriza la intención del usuario frente al departamento.

## Documentos

La puntuación combina:

- coincidencias mediante tags;
- coincidencias con el título;
- coincidencias con el contenido;
- departamento del empleado;
- carácter transversal.

Los factores de departamento y transversal solo aportan puntuación cuando ya existe una coincidencia real con la intención de la consulta.

Esto evita recuperar documentos únicamente por pertenecer al mismo departamento.

---

# Recuperación de FAQ

Las FAQ actúan como índice de navegación.

No sustituyen al documento principal.

Su función consiste en facilitar la localización de documentación relevante mediante:

- formulaciones frecuentes;
- preguntas habituales;
- respuestas resumidas;
- referencias documentales.

---

# Relación FAQ → Documento

Esta relación constituye una decisión arquitectónica importante.

El flujo correcto es:

```text
consulta
        │
        ▼
FAQ
        │
        ▼
doc_id
        │
        ▼
documento principal
```

No se realiza el proceso inverso.

Motivo:

La FAQ representa únicamente una puerta de acceso.

La información autorizada siempre procede del documento asociado.

---

# Desduplicación

Los documentos pueden recuperarse desde dos orígenes distintos:

- selección directa;
- referencias desde FAQ.

Antes de construir el contexto se eliminan duplicados utilizando los identificadores documentales.

Esto garantiza:

- una única copia de cada documento;
- menor contexto;
- menor consumo posterior por el modelo.

---

# Aplicación de límites

Los límites documentales se aplican únicamente al final del proceso.

El flujo es:

```text
selección
        │
        ▼
combinación
        │
        ▼
desduplicación
        │
        ▼
aplicación del límite
```

No se limita antes.

Motivo:

Un documento asociado a una FAQ nunca debe perder prioridad por haber aplicado el límite demasiado pronto.

---

# Normalización

Toda comparación textual utiliza el mismo proceso.

El módulo elimina diferencias de:

- mayúsculas;
- acentos;
- guiones;
- barras;
- guiones bajos;
- espacios múltiples.

Esto proporciona un comportamiento uniforme en todas las búsquedas.

---

# Stopwords

Las palabras vacías eliminan términos frecuentes que no representan intención.

Ejemplos:

- artículos;
- preposiciones;
- saludos;
- expresiones de cortesía.

Su objetivo es reducir ruido durante la recuperación.

No modifican el contenido original de documentos ni FAQ.

---

# Validaciones

## Validaciones implementadas

El módulo valida:

- existencia de listas;
- listas vacías cuando no están permitidas;
- elementos tipo diccionario;
- tipos básicos de entrada;
- rutas;
- JSON válido.

---

## Validaciones deliberadamente excluidas

No se implementan validadores específicos para:

- FAQ;
- documentos;
- empleados.

El módulo trabaja con esquemas flexibles.

Los campos esperados se documentan, pero no se bloquea el procesamiento cuando una entrada contiene información adicional o algunos campos opcionales ausentes.

Esta decisión favorece la integración entre ramas y evita imponer un esquema rígido durante el desarrollo colaborativo.

---

# Campos esperados

Aunque no se validan de forma estricta, la arquitectura espera que los datos contengan aproximadamente los siguientes campos.

## Empleados

```text
id
nombre
departamento
fecha_inicio
```

---

## FAQ

```text
id
pregunta
respuesta_corta
tags
doc_id
```

---

## Documentos

```text
id
titulo
cuerpo
departamento
tags
```

---

# Mutabilidad

`context.py` no modifica ninguna de las estructuras recibidas.

Las funciones devuelven referencias a los objetos originales.

Los módulos consumidores deben tratar esos datos como información de solo lectura.

Cuando sea necesario modificar el contexto, la copia deberá realizarse fuera del módulo.

---

# Relación con `logic.py`

`logic.py` trata `context.py` como un servicio independiente.

Su única interacción de alto nivel consiste en:

```python
construir_contexto(...)
```

`logic.py` no conoce:

- pesos;
- puntuaciones;
- algoritmo de selección;
- proceso de desduplicación;
- reglas de combinación.

Esto permite modificar el algoritmo interno sin alterar el contrato entre módulos.

---

# Relación con `config.py`

Toda la configuración utilizada por `context.py` procede de `config.py`.

Ejemplos:

- pesos;
- umbrales;
- límites;
- documentos transversales.

El algoritmo nunca contiene valores mágicos.

---

# Decisiones arquitectónicas

Durante el diseño se adoptaron las siguientes decisiones.

## La intención tiene prioridad sobre el departamento

Un documento del mismo departamento no debe recuperarse si no guarda relación con la consulta.

---

## Las FAQ son un índice

La documentación principal siempre prevalece sobre la respuesta corta de una FAQ.

---

## Los documentos globales no son obligatorios

Un documento transversal solo recibe prioridad cuando ya es relevante por contenido.

---

## El algoritmo permanece encapsulado

Ningún consumidor necesita conocer cómo se calcula la puntuación.

Únicamente necesita el contexto final.

---

## El contrato permanece estable

Aunque en el futuro cambie el algoritmo de recuperación (BM25, embeddings, RAG híbrido, etc.), el contrato de salida de `construir_contexto()` debe mantenerse.

Esto protege la arquitectura frente a cambios tecnológicos.

---

# Compatibilidad

Se mantiene:


cargar_JSON = cargar_json

Como alias temporal para mantener compatibilidad con implementaciones anteriores durante el proceso de integración.

No representa una segunda implementación.

---

# Integración pendiente: Robustez

La Arquitectura Base no implementa variantes vulnerables.

En el futuro el área de Robustez podrá sustituir la estrategia de recuperación respetando siempre el mismo contrato de salida.

No deben crearse módulos paralelos como:

```text
context_vulnerable.py
context_seguro.py
```

Las variantes deberán reutilizar:

```python
construir_contexto(...)
```

mediante estrategias, adaptadores o funciones específicas.

---

# Integración pendiente: LLM y Benchmark

`context.py` no conoce modelos de lenguaje.

El área LLM únicamente consumirá el contexto ya preparado para:

- construir prompts;
- seleccionar modelos;
- registrar métricas;
- realizar benchmarking.

El algoritmo de recuperación documental permanecerá completamente independiente de esas decisiones.

---

# Filosofía de diseño

`context.py` debe permanecer estable aunque cambien:

- el proveedor LLM;
- el modelo;
- el prompt;
- la estrategia de seguridad;
- el benchmark;
- la forma de generar respuestas.

Su única responsabilidad consiste en seleccionar el mejor contexto posible.

-----------------------------------------------------------------------------------------------------------------------------

# Arquitectura de `main.py`

## Objetivo

`main.py` constituye el punto de entrada de la aplicación.

Su responsabilidad consiste exclusivamente en coordinar la ejecución de la Arquitectura Base.

No contiene lógica de negocio, no construye contexto, no selecciona perfiles y no interactúa directamente con ningún proveedor de IA.

Su función es conectar al usuario con la arquitectura diseñada en los módulos del proyecto.

---

# Responsabilidades

`main.py` es responsable de:

- Cargar las fuentes de datos.
- Verificar que la estructura mínima de dichas fuentes sea válida.
- Mostrar los empleados disponibles.
- Identificar al empleado que inicia la sesión.
- Inicializar el estado conversacional.
- Solicitar consultas al usuario.
- Invocar la Arquitectura Base.
- Mostrar por consola el resultado de la preparación del turno.
- Gestionar los errores previsibles durante la ejecución.

---

# Qué no hace

`main.py` no debe:

- Construir prompts.
- Seleccionar perfiles.
- Clasificar consultas.
- Recuperar documentación.
- Gestionar el estado internamente.
- Llamar directamente a Gemini.
- Llamar directamente a OpenAI.
- Elegir modelos.
- Elegir temperaturas.
- Aplicar benchmarking.
- Detectar ataques.
- Ejecutar modos seguro o vulnerable.
- Implementar lógica de negocio.

Todas estas responsabilidades pertenecen a otros módulos.

---

# Filosofía del módulo

`main.py` debe ser el archivo más sencillo del proyecto.

Toda decisión funcional pertenece a la arquitectura.

`main.py` únicamente coordina el flujo general de ejecución.

---

# Flujo general

La ejecución prevista sigue el siguiente pipeline.

```text
Inicio
        │
        ▼
Carga de datos
        │
        ▼
Selección del empleado
        │
        ▼
Inicialización del estado
        │
        ▼
Solicitud de consulta
        │
        ▼
preparar_turno()
        │
        ▼
Mostrar resultado
        │
        ▼
Nueva consulta
```

Mientras el área LLM no esté integrada el flujo termina tras preparar el turno.

---

# Carga de datos

## Responsabilidad

Toda la carga de información se realiza mediante:

```python
cargar_json()
```

Las rutas utilizadas proceden exclusivamente de:

```python
config.py
```

`main.py` no construye rutas manualmente.

---

## Fuentes cargadas

La Arquitectura Base trabaja con cuatro fuentes principales.

### Empresa

```python
empresa.json
```

Debe contener un diccionario.

---

### Empleados

```python
empleados_demo.json
```

Debe contener una lista.

---

### Documentación

```python
onboarding_docs.json
```

Debe contener una lista.

---

### FAQ

```python
faq_onboarding.json
```

Debe contener una lista.

---

## Validaciones

`main.py` únicamente verifica el tipo raíz esperado.

La validación detallada corresponde a `context.py`.

---

# Selección del empleado

La identificación del empleado reutiliza:

```python
buscar_empleado()
```

No se implementa una segunda búsqueda dentro de `main.py`.

---

## Flujo

```text
mostrar empleados
        │
        ▼
pedir ID
        │
        ▼
buscar_empleado()
        │
        ├── encontrado
        │         │
        │         ▼
        │   iniciar sesión
        │
        └── no encontrado
                  │
                  ▼
           volver a solicitar ID
```

---

## Información mostrada

Únicamente se presenta:

- identificador;
- nombre;
- departamento;
- fecha de incorporación.

No se muestran estructuras completas.

---

# Estado conversacional

El estado se crea utilizando:

```python
inicializar_estado()
```

No se construye manualmente un diccionario equivalente.

Esto garantiza que el contrato definido por `state.py` permanezca centralizado.

---

# Ejecución de la sesión

La sesión mantiene un único empleado activo.

El flujo consiste en:

```text
consulta
        │
        ▼
preparar_turno()
        │
        ▼
mostrar resumen
        │
        ▼
nueva consulta
```

La sesión termina cuando el usuario escribe:

```text
salir
exit
quit
```

---

# Preparación del turno

`main.py` únicamente invoca:

```python
preparar_turno()
```

No realiza ninguna operación adicional sobre:

- perfiles;
- contexto;
- documentos;
- FAQ;
- clasificación.

Toda esa lógica pertenece a `logic.py`.

---

# Resultado mostrado

Mientras no exista integración con el área LLM, la aplicación mostrará únicamente información arquitectónica.

Ejemplo:

- estado;
- mensaje;
- perfil seleccionado;
- categoría preliminar;
- día de onboarding;
- documentos recuperados;
- FAQ recuperadas;
- existencia de contexto.

No se imprime:

- documentación completa;
- cuerpo de documentos;
- prompts;
- respuestas simuladas.

---

# Estado conversacional durante la Arquitectura Base

Existe una limitación intencionada.

`preparar_turno()` no modifica el historial.

Motivo:

El turno todavía no ha recibido una respuesta del modelo.

El historial únicamente debe actualizarse mediante:

```python
finalizar_turno()
```

Esto evita estados inconsistentes.

---

# Gestión de errores

## Errores previstos

Durante la carga:

- archivo inexistente;
- JSON inválido;
- error de lectura;
- estructura raíz incorrecta.

Durante la interacción:

- empleado inexistente;
- consulta inválida;
- errores devueltos por `preparar_turno()`.

Estos errores se muestran por consola sin finalizar necesariamente la sesión.

---

## Errores inesperados

No se utilizará:

```python
except Exception
```

como mecanismo general.

Los errores inesperados deben propagarse durante el desarrollo para facilitar su depuración.

---

# Funciones públicas

La estructura prevista del archivo es la siguiente.

## `cargar_datos()`

Carga todas las fuentes del proyecto.

---

## `mostrar_empleados()`

Presenta la lista de empleados disponibles.

---

## `seleccionar_empleado()`

Solicita el identificador del empleado.

Permite repetir la entrada hasta localizar un empleado válido.

---

## `imprimir_errores()`

Muestra por consola la envolvente estándar de error.

---

## `imprimir_turno_preparado()`

Presenta un resumen del turno preparado.

No imprime información documental completa.

---

## `ejecutar_sesion()`

Coordina el ciclo principal de consultas.

---

## `main()`

Punto de entrada del programa.

---

# Relación con `config.py`

`main.py` reutiliza:

- rutas;
- configuración por defecto.

No replica constantes.

---

# Relación con `context.py`

`main.py` únicamente consume:

- `cargar_json()`;
- `buscar_empleado()`.

No realiza selección documental directa.

---

# Relación con `logic.py`

La única función invocada durante la Arquitectura Base es:


preparar_turno()

El resto del procesamiento pertenece a la integración posterior.

---

# Relación con `state.py`

`main.py` únicamente utiliza:

inicializar_estado()

No modifica directamente la estructura del estado.

---

# Decisiones arquitectónicas

## Toda la lógica pertenece a la arquitectura

`main.py` no contiene reglas de negocio.

---

## Una única fuente para las rutas

Las rutas siempre proceden de `config.py`.

---

## Un único punto para construir el contexto

`main.py` nunca invoca directamente funciones internas de `context.py`.

Toda recuperación documental pasa por:


preparar_turno()

---

## Una única fuente para el estado

La creación del estado pertenece a `state.py`.

---

## Preparar no significa responder


Mientras el área LLM no esté integrada, el programa finaliza el flujo tras preparar el turno.

Esta decisión evita implementar soluciones provisionales que posteriormente deban eliminarse cuando el área LLM complete su integración.

No se simulan respuestas ni se generan respuestas ficticias y tampoco se implementan proveedores provisionales.


---

# Integración pendiente: Área LLM y Benchmark

Cuando el adaptador LLM esté disponible el flujo completo será:


consulta
        │
        ▼
preparar_turno()
        │
        ▼
adaptador LLM
        │
        ▼
finalizar_turno()
        │
        ▼
mostrar respuesta


## Responsabilidad del área LLM

El área correspondiente deberá implementar:

- construcción del prompt;
- selección del proveedor;
- selección del modelo;
- temperatura;
- llamada al modelo;
- generación estructurada;
- métricas;
- benchmarking.

`main.py` no conocerá ninguna de estas decisiones.

---

# Integración pendiente: Área de Robustez

La Arquitectura Base no implementa mecanismos de seguridad.

El área de Robustez podrá intervenir:


entrada usuario
        │
        ▼
validación avanzada
        │
        ▼
preparar_turno()


o bien:


preparar_turno()
        │
        ▼
validación adicional
        │
        ▼
adaptador LLM


Las variantes deberán reutilizar el mismo flujo.

No deben crearse archivos alternativos como:

main_seguro.py
main_vulnerable.py

---

# Filosofía de diseño

`main.py` debe permanecer estable aunque cambien:

- el modelo;
- el proveedor;
- el prompt;
- la estrategia de seguridad;
- el benchmark;
- la forma de generar respuestas.

Su única responsabilidad consiste en coordinar la ejecución de la Arquitectura Base.

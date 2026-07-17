# Plan de reparación ASISTENTE BRIDGE

## Problemas prioritarios

| Requisito | Estado | Diagnóstico |
|---|---|---|
| Chat con documentación seleccionada | Bloqueado | `context.py` falla en las dos listas puntuadas. |
| Historial máximo de 4 turnos | Parcial e incorrecto | Se guardan mensajes ilimitados y se recuperan 4 mensajes, equivalentes normalmente a 2 turnos. |
| Día de onboarding 1–5 | Incorrecto | Se calcula con días naturales desde `fecha_inicio`; la demo actual devuelve más de 100 días. |
| Adaptación dev junior/comercial/remoto UE | No implementada | Esos perfiles no se consumen en el prompt ni en la selección funcional. |
| Checklist JSON | No implementado | No existe prompt, schema, orquestación ni demo. |
| Modo vulnerable | Parcial | Existe un prompt aislado, pero no usa el turno ni el contexto completo y no llega al cliente real. |
| Modo seguro | Parcial y bloqueado | Existen tres validaciones y wrappers, pero un regex rompe cualquier entrada legítima. Faltan secciones 7–14. |
| Fail-closed | Diseñado, no probado | El flag existe, pero no hay prueba automática de cero invocaciones. |
| 5 casos trampa propios | No implementado | Solo está `casos_trampa_ejemplo.json`. |
| Demo vulnerable vs seguro | No implementada | `main.py` no contiene la demo exigida. |
| 10 casos de benchmark | No implementado | La plantilla tiene 3 entradas, una de ellas `TODO`. |
| 2 modelos, mismas condiciones | No implementado | El benchmark no llama a ningún modelo. |
| Latencia y tokens reales | No implementado | Se simulan con tiempo casi cero y `palabras * 2`. |
| CSV e informe en `output/` | No implementado | Solo se intenta escribir JSON en `entregables/`. |
| Matriz y recomendación | No implementado | Ambos archivos contienen `TODO`. |
| README reproducible | No implementado | El README proporcionado es esencialmente el enunciado, no la documentación del proyecto final. |

## Bloqueos críticos

### 1. Patrón de credenciales que no es tupla. CORREGIDO

Patrón en `config.py` que debía ser tupla y no lo era. Corregido.

### 2. `append()` incorrecto en selección de FAQ y documentación. CORREGIDO

`Append()` en `context.py` que debía agregar a su respectiva lista una tupla como `(puntuación, faq)`

### 3. `prompts.py`. A MEDIAS

La constante `JSON_SCHEMA_HINT` todavía ya existe.

### 4. `gemini_client.py` importa `TEMPERATURE` y no existe. CORREGIDO

Sustituido por `TEMPERATURE_DEFAULT`

### 5. Imports incompatibles. CORREGIDO

No puede haber diferentes criterios de import en un mismo programa. Si el archivo desde el que se importa está al mismo nivel que el archivo que se va a importar
se nombra directamente al archivo.

### 6. Ausencia de un validador en benchmark. PENDIENTE

Se importa `validar_respuesta_estructurada`, pero no existe.

## Registro detallado de errores y soluciones

### `config.py`

- [ ]`config.py` la constante `RESULTADOS_BENCHMARK_PATH` apunta a entregables. El benchmark debería devolver un CSV o JSON o algo así. De eso se elabora el markdown que piden. Los archivos no pueden ir todos al mismo directorio, lo propio es separar CSV/JSON/MD
- [ ]`VULNERABLE_CONTEXT_PATHS` no se utiliza. Falta todavía una función que utilice el payload vulnerable solo para una demo.
- [ ]`empleados_demo.json` la demo puede exponer datos de otros empleados innecesariamente. Aunque sea vulnerable, limitar la demostración a docu no secreta; vulnerabilidad de instrucciones no de fuga artificial de todo el dataset. A no ser que así lo decidamos.
- [x]`MAX_ONBOARDING_DAYS` no se utiliza. Implementar o eliminar. --> elimino
- [x] `PATRONES_FUERA_DE_DOMINIO` separado en PARTICIPANTE_EXTERNO y FUERA_DE_DOMINIO_GENERAL y modificada la función `validar_entrada_segura()` corregida.
- [x] Datos personales que bloquean más de la cuenta, se corrigen los patrones y se añaden palabras para derivaciones a RRHH.
- [x] `PATRONES_SOSPECHOSOS` y `DOMINIO_KEYWORDS` son del código antiguo, se ha corregido.
- [x] `REQUIRED_RESPONSE_FIELDS` no garantiza que la respuesta cumpla con el contrato. Se elimina, se crea la función `validar_respuesta_estructurada()` en `validators.py`. También ha hecho adaptar `benchmark.py` con los import y con la variable del `mock`

### `context.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [x] | CTX-01 | P0 | `faqs_puntuadas.append(puntuacion, faq)`. | Fallo de ejecución. | Añadir una tupla. |
| [x] | CTX-02 | P0 | `documentos_puntuados.append(puntuacion, documento)`. | Fallo de ejecución. | Añadir una tupla. |
| [ ] | CTX-03 | P1 | La consulta genérica “¿Qué hago mi primera semana?” recupera FAQ y documentos de Engineering y Sales para cualquier empleado. | Mezcla departamentos y reduce fidelidad. | Aplicar el departamento como filtro o prioridad fuerte cuando la consulta es de plan/checklist y no nombra otro departamento. |
| [ ] | CTX-04 | P1 | “¿Qué hago el día 3?” selecciona documentos arbitrarios por coincidencias numéricas y genéricas. | El día simulado no dirige la recuperación. | Añadir selección específica por día y departamento; no depender del número `3` como token general. |
| [ ] | CTX-05 | P1 | No valida campos obligatorios de documentos, FAQ ni empleados. | Un JSON parcialmente mal formado puede fallar tarde o producir contexto incoherente. | Añadir validadores de fuentes al cargar: IDs únicos, strings requeridos, listas de tags y referencias `doc_id` existentes. |
| [ ] | CTX-06 | P1 | No existe control explícito de acceso por departamento. | Una consulta puede recuperar contenido de otro departamento. | Para el reto, definir documentos globales y documentos departamentales; excluir los ajenos salvo que el caso de uso lo autorice. |
| [ ] | CTX-07 | P2 | Duplica normalización con `validators.py`. | Posibles resultados diferentes entre recuperación y seguridad. | Mantener dos funciones solo si se documenta que la normalización de seguridad es más fuerte; compartir pruebas, no necesariamente código. |
| [ ] | CTX-08 | P2 | `cargar_JSON` es un alias temporal. | Ruido y deuda técnica. | Eliminar tras corregir consumidores. |
| [ ] | CTX-09 | P2 | Los límites no validan tipos dentro de `seleccionar_faq`/`seleccionar_documentos`. | Un valor no entero puede lanzar error no controlado. | Validar en la frontera de configuración y conservar asserts simples en contexto. |

### `validators.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | VAL-01 | P0 | El patrón de credenciales rompe `_coincide_algun_patron`. | Ninguna entrada legítima supera la primera puerta. | Corregir config y añadir validación al importar: todos los valores deben ser `tuple[str, ...]`. |
| [ ] | VAL-02 | P1 | Todos los patrones fuera de dominio se devuelven como `external_participant`. | Mensajes de rechazo incorrectos. | Clasificar por grupos y devolver `out_of_scope` para contenido general. |
| [ ] | VAL-03 | P1 | `validar_salida_segura()` permite omitir `document_ids`, `faq_ids`, `needs_escalation` y `escalation_department`. | Una salida no cumple `REQUIRED_RESPONSE_FIELDS` pero se acepta. | Ejecutar primero una validación estructural completa; después las reglas de seguridad. |
| [ ] | VAL-04 | P1 | Solo comprueba que IDs devueltos sean subconjunto, no que el texto esté respaldado. | El modelo puede inventar una política y citar un ID autorizado. | Mantener la comprobación de IDs y evaluar fidelidad en tests/benchmark; opcionalmente exigir al menos un ID cuando `in_scope=True`. |
| [ ] | VAL-05 | P1 | No se valida coherencia entre `needs_escalation` y `escalation_department`. | Contratos contradictorios. | Si escala, exigir departamento permitido; si no escala, exigir `None` o cadena vacía acordada. |
| [ ] | VAL-06 | P1 | No se valida coherencia entre categoría externa y contexto/categoría preliminar. | El modelo puede devolver una categoría válida pero incongruente. | Definir una regla tolerante: categoría externa debe ser la preliminar o una categoría compatible. |
| [ ] | VAL-07 | P1 | El rechazo `in_scope=False` se etiqueta siempre `undocumented`. | Puede ocultar un `out_of_scope` real del modelo. | Usar la categoría y un campo de motivo estructurado; no inferir todo desde un booleano. |
| [ ] | VAL-08 | P2 | Importa constantes no usadas: `DOMINIO_KEYWORDS`, `MAX_OUTPUT_WORDS`, modos. | Ruido y acoplamiento. | Eliminar imports no utilizados. |
| [ ] | VAL-09 | P2 | `_resultado_validacion()` accede a `MENSAJES_SEGURIDAD[codigo]`. | Un código nuevo no registrado provoca `KeyError`. | Validar códigos en tests y usar un mensaje interno de fallback solo para error de programación. |
| [ ] | VAL-10 | P1 | Cobertura de inyección reducida respecto al documento original: faltan varias variantes inglesas y etiquetas. | Falsos negativos evitables en los casos del benchmark. | Recuperar los patrones previstos, pero respaldarlos con tests; no aumentar regex sin casos verificables. |
| [ ] | VAL-11 | P1 | La detección de datos sensibles no distingue consulta de soporte de solicitud de secreto. | “¿Cómo recupero mi contraseña de Slack?” puede pasar o bloquear según redacción, sin política clara. | Definir intención: revelar/mostrar secreto se bloquea; recuperar/restablecer se deriva a IT. |

### `logic.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | LOG-01 | P1 | `logic.py` contiene validación de estado, configuración, esquema externo, día, clasificación, robustez y orquestación. | 868 líneas y responsabilidades solapadas. | Dejar en `logic.py` solo coordinación y reglas de negocio; mover operaciones de estado a `state.py` y contrato de salida a `validators.py`/schema. |
| [ ] | LOG-02 | P1 | `_registrar_evento_seguridad()` sustituye una lista inválida en el estado, pero conserva la referencia local inválida. | Si `eventos_seguridad` es una cadena, luego ejecuta `.append()` sobre la cadena y falla. | Tras resetear, reasignar `eventos = estado["eventos_seguridad"]`; mejor mover la función a `state.py`. |
| [ ] | LOG-03 | P1 | `preparar_turno_con_modo()` y `finalizar_turno_con_modo()` reciben el modo por separado. | El llamador puede preparar en seguro y finalizar en vulnerable, o al revés. | Guardar el modo dentro del turno preparado y verificar que no cambie; no aceptar un modo arbitrario del usuario. |
| [ ] | LOG-04 | P1 | `crear_respuesta_controlada()` pone `llamar_modelo=False` incluso cuando `modelo_invocado=True` tras bloquear salida. | El nombre del campo se vuelve ambiguo. | Separar `autorizar_llamada` y `modelo_invocado`, o documentar claramente el estado. |
| [ ] | LOG-05 | P1 | `calcular_dia_onboarding()` usa días naturales y la fecha actual. | No representa el “día simulado 1–5” y cuenta fines de semana. | El día de demo debe ser un valor explícito del estado; el cálculo por fecha puede quedar como utilidad opcional. |
| [ ] | LOG-06 | P1 | `seleccionar_perfil()` solo distingue IT, RRHH y onboarding por antigüedad. | Ignora Sales, Operations, Engineering y los tres perfiles del enunciado. | Separar `perfil_empleado` de `perfil_funcional`; combinar ambos en prompt. |
| [ ] | LOG-07 | P1 | `MAX_ONBOARDING_DAYS` no limita ni cambia comportamiento. | Configuración incongruente con el producto de 30 días. | Definir qué ocurre a partir del día 31 o eliminar la constante. |
| [ ] | LOG-08 | P2 | `_validar_resultado_externo()` duplica parte de `validar_salida_segura()`. | Dos contratos que pueden divergir. | Una sola validación estructural común; la seguridad añade reglas después. |
| [ ] | LOG-09 | P2 | Se mantienen bloques “ELIMINADO” después de haber integrado robustez. | El archivo afirma simultáneamente que está integrado y pendiente. | Eliminar comentarios obsoletos tras el merge. |
| [ ] | LOG-10 | P1 | La empresa completa se copia al turno. | El futuro prompt podría enviar más información de la necesaria. | El builder seguro debe aplicar allowlist; no enviar el objeto completo. |

### `state.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | STA-01 | P1 | `main.py` llama `inicializar_estado()` sin empleado. | `user_profile` queda vacío y el prompt antiguo no conoce al empleado. | Inicializar con el empleado o rediseñar el estado con `empleado`, `dia_onboarding` y `messages`. |
| [ ] | STA-02 | P1 | `user_profile or {}` conserva la referencia original si no está vacío. | Mutaciones del estado pueden modificar el diccionario cargado. | Usar `deepcopy`. |
| [ ] | STA-03 | P1 | `ultimos_n(..., 4)` devuelve cuatro mensajes, no cuatro turnos. | Normalmente solo se envían dos pares usuario/asistente. | Crear `ultimos_turnos(state, n)` y devolver hasta `n * 2` mensajes completos. |
| [ ] | STA-04 | P2 | El historial crece sin límite. | Uso de memoria creciente en sesiones largas. | Conservar una ventana mayor limitada o podar tras finalizar cada turno. |
| [ ] | STA-05 | P1 | No almacena `dia_onboarding` simulado. | El requisito transversal no tiene una fuente de verdad. | Añadirlo al estado y validar 1–5 para demos/checklist. |
| [ ] | STA-06 | P1 | No contiene estado de checklist ni tareas completadas. | La segunda funcionalidad del asistente no puede evolucionar. | Añadir `checklist` por día o una estructura mínima para marcar tareas. |
| [ ] | STA-07 | P1 | El registro de eventos de seguridad está en `logic.py`. | Responsabilidad de estado dispersa. | Implementar `append_security_event()` en `state.py`. |
| [ ] | STA-08 | P2 | Hay una función antigua comentada como string triple. | Código muerto. | Eliminarla o recuperarla con pruebas; no dejarla embebida. |

### `prompts.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | PRM-01 | P0 | Importa `JSON_SCHEMA_HINT` inexistente. | No se puede importar. | Definir schemas reales. |
| [ ] | PRM-02 | P1 | `build_faq_block()` busca `question` y `answer`; los datos usan `pregunta` y `respuesta_corta`. | Las FAQ aparecen vacías. | Usar las claves reales o un DTO normalizado. |
| [ ] | PRM-03 | P1 | `build_assistant_prompt()` sigue hablando de “tutor de estudio del bootcamp”. | Dominio incorrecto. | Eliminar o reescribir para onboarding. |
| [ ] | PRM-04 | P1 | Lee `nivel` y `tema_actual`, que no existen en `empleados_demo.json`. | Personalización ficticia. | Usar `departamento`, `rol`, `perfil`, `modalidad`, `ubicacion` y día. |
| [ ] | PRM-05 | P1 | No incluye documentos, día de onboarding ni fuentes autorizadas. | No puede responder con fidelidad al producto. | Construir desde `turno_preparado`, no desde parámetros sueltos inconsistentes. |
| [ ] | PRM-06 | P1 | `build_secure_prompt()` concatena sistema y usuario en el mismo string. | No cumple la separación prevista en el apartado 7. | Implementar `build_secure_system_instruction()` y `build_secure_turn_contents()`. |
| [ ] | PRM-07 | P1 | `build_vulnerable_prompt()` solo recibe el mensaje y no el turno. | La comparación no mantiene el mismo contexto y perfil. | Crear un builder vulnerable desde el mismo `turno_preparado`, mezclando deliberadamente los datos en un solo prompt. |
| [ ] | PRM-08 | P1 | No hay prompt de checklist. | Falta funcionalidad obligatoria. | Añadir builders de chat y checklist con schemas distintos. |
| [ ] | PRM-09 | P2 | La docstring del modo vulnerable contiene una justificación extensa dentro de la función. | Ruido y mantenimiento difícil. | Llevar la explicación al README o documento técnico. |

### `gemini_auth.py` y `gemini_client.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | LLM-01 | P0 | Importa `TEMPERATURE` inexistente. | El cliente no carga. | Unificar constantes/argumentos. |
| [ ] | LLM-02 | P1 | `configurar_gemini_api_key()` se ejecuta al importar el módulo. | Tests y benchmark pueden bloquearse esperando `getpass`. | Eliminar efectos laterales; cargar `.env` en el entrypoint y lanzar error explícito si falta la clave. |
| [ ] | LLM-03 | P1 | Todas las funciones usan `MODEL` global. | El benchmark recibe `model_key` pero nunca puede cambiar modelo. | Pasar `model_id` como argumento a `count_tokens()` y `generate_content()`. |
| [ ] | LLM-04 | P1 | `safe_generate()` usa por defecto `TEMPERATURE_VULNERABLE`. | Nombre y comportamiento contradictorios. | No usar default ambiguo; exigir temperatura o usar `TEMPERATURE_SAFE`. |
| [ ] | LLM-05 | P1 | No existe función con `system_instruction` separado. | Apartado 8 pendiente. | Implementar una llamada común que acepte `system_instruction`, `contents`, `model_id`, `temperature` y schema. |
| [ ] | LLM-06 | P1 | JSON mode solo fija MIME type. | El modelo puede devolver JSON con estructura incorrecta. | Pasar `response_schema` y parsear/validar la respuesta. |
| [ ] | LLM-07 | P1 | Devuelve texto JSON sin `json.loads()` ni modelo tipado. | `logic.py` espera un diccionario, pero recibe string. | Crear `parse_chat_response()` y `parse_checklist_response()`. |
| [ ] | LLM-08 | P1 | No establece `max_output_tokens`. | Salidas y costes menos controlables. | Aplicar el máximo del registry/config. |
| [ ] | LLM-09 | P1 | `_metricas_from_response()` asume que `usage_metadata` existe. | Posible `AttributeError`. | Usar `getattr(response, "usage_metadata", None)` y valores `None`. |
| [ ] | LLM-10 | P1 | No normaliza errores de red, cuota, autenticación o respuesta vacía. | `main.py` puede caer sin mensaje controlado. | Definir excepciones del adaptador o una envolvente de error. |
| [ ] | LLM-11 | P2 | `count_tokens()` añade una petición adicional y no forma parte de la latencia medida. | Métricas no comparables. | Registrar por separado latencia total y latencia de generación; usar `usage_metadata` para tokens reales. |

### `main.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | MAIN-01 | P1 | Estado inicial sin empleado. | Perfil vacío. | `inicializar_estado(empleado=empleado, dia_onboarding=...)`. |
| [ ] | MAIN-02 | P1 | Modo seguro escrito como literal en dos lugares. | Riesgo de desincronización y demo difícil. | Definir modo en una variable interna o tomarlo del resultado preparado. |
| [ ] | MAIN-03 | P1 | Condición `if data.get("llamar_modelo"):` es de verdad lógica, no `is True`. | Un valor inválido truthy puede invocar el modelo. | Usar `is True` y `continue` explícito cuando sea `False`. |
| [ ] | MAIN-04 | P0 | `resultado_externo` es un mock fijo. | No existe asistente real. | Sustituir por adaptador de Ale y parseo estructurado. |
| [ ] | MAIN-05 | P1 | El mock omite campos declarados obligatorios. | El validador actual lo acepta, demostrando que el contrato no se comprueba. | Validación estructural antes de robustez. |
| [ ] | MAIN-06 | P1 | No existe selección explícita del día 1–5. | Las demos no cumplen el requisito. | Pedir día en demo/CLI o usar funciones de demo con día fijo. |
| [ ] | MAIN-07 | P1 | No hay demos numeradas 1, 2 y 3. | Incumple Parte 2. | Añadir funciones reproducibles, separadas de la sesión interactiva. |
| [ ] | MAIN-08 | P1 | No hay demo vulnerable vs seguro. | Incumple Parte 3. | Añadir helper con mismo input y contador de llamadas. |
| [ ] | MAIN-09 | P2 | Mantiene grandes bloques comentados ya reemplazados. | Confusión sobre flujo activo. | Eliminar después de validar la integración. |
| [ ] | MAIN-10 | P1 | No captura errores del adaptador o parseo JSON. | Caída de la aplicación. | Capturar errores en la frontera y mostrar una respuesta técnica controlada. |
| [ ] | MAIN-11 | P1 | No hay checklist ni salida JSON. | Funcionalidad ausente. | Crear demo y camino de ejecución de checklist. |

### `benchmark.py`, `model_registry.py` y `model_utils.py`

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | BEN-01 | P0 | El benchmark es una simulación. | No compara modelos. | Llamar al mismo adaptador real usado por el asistente. |
| [ ] | BEN-02 | P1 | `model_key` solo se usa para coste; no se pasa al cliente. | Ambos supuestos modelos usarían el modelo global. | Parametrizar cliente y pipeline. |
| [ ] | BEN-03 | P1 | Tokens de entrada = `len(prompt.split()) * 2`; salida = 150. | Métricas falsas. | Usar `usage_metadata`. |
| [ ] | BEN-04 | P1 | Latencia medida alrededor de un bloque vacío. | Casi cero para todos los modelos. | Medir la llamada real con `perf_counter`. |
| [ ] | BEN-05 | P1 | No guarda respuesta generada. | No puede evaluarse fidelidad, tono o seguridad. | Guardar texto/JSON, error y fuentes. |
| [ ] | BEN-06 | P1 | No genera CSV. | Incumple enunciado. | Exportar CSV tabular y JSON detallado a `output/`. |
| [ ] | BEN-07 | P1 | No aplica la rúbrica 1–3. | Matriz sin datos. | Añadir columnas de evaluación manual y/o archivo para revisión. |
| [ ] | BEN-08 | P1 | No valida `listar_modelos_benchmark()` ni `validar_modelos_benchmark()`. | Puede ejecutar modelos deshabilitados. | Validar antes de empezar e iterar solo activos. |
| [ ] | BEN-09 | P1 | `except Exception: return 0.0` oculta errores de costes. | Un fallo parece coste cero. | Capturar solo `KeyError`/`ValueError` y registrar error. |
| [ ] | BEN-10 | P1 | El `try/except ImportError` oculta fallos de imports internos. | Benchmark engañoso. | Eliminar tolerancia silenciosa. |
| [ ] | BEN-11 | P1 | `pregunta_id` está tipado como `int`, pero IDs son strings. | Contrato incorrecto. | Cambiar a `str`. |
| [ ] | BEN-12 | P1 | Dataset actual no tiene `categoria_esperada`. | El mock asigna `None`. | Definir schema de casos consistente. |
| [ ] | BEN-13 | P1 | No diferencia chat, checklist, trampa, perfil ni día. | No cubre el producto real. | Dataset con `tipo`, `empleado_id`, `dia`, `consulta`, expectativas y criterios. |
| [ ] | BEN-14 | P1 | Costes de registry incorrectos; contexto Pro incorrecto. | Comparación económica inválida. | Actualizar desde fuente oficial y fechar datos. |
| [ ] | BEN-15 | P2 | `model_registry.py` y `model_utils.py` añaden dos módulos para dos modelos y duplican config. | Más imports y más puntos de fallo. | Opción preferida: un `BENCHMARK_MODELS` en config y eliminar ambos; alternativa: registry como única fuente sin IDs duplicados en config. |
| [ ] | BEN-16 | P1 | No registra temperatura, modelo, timestamp, modo, run o versión del prompt. | Resultados no reproducibles. | Incluir metadatos por ejecución. |
| [ ] | BEN-17 | P1 | No maneja rate limits ni errores por caso. | Una excepción puede abortar todo. | Registrar estado/error y continuar con el resto. |

### Datos, README y entregables

| v | ID | Severidad | Hallazgo | Consecuencia | Corrección |
|---|---|---|---|---|---|
| [ ] | DAT-01 | P1 | Solo existe `casos_trampa_ejemplo.json`. | No hay cinco casos propios. | Crear `casos_trampa.json` con redacción del equipo y expectativas ejecutables. |
| [ ] | DAT-02 | P1 | Plantilla benchmark: 3 casos y uno `TODO`. | No alcanza 10 casos. | Crear dataset final de 10–14 casos. |
| [ ] | DAT-03 | P1 | Los prompts de plantilla ya vienen ensamblados, pero el proyecto necesita probar su pipeline. | Se puede medir el modelo pero no recuperación/perfiles. | Preferir casos estructurados y construir el prompt con las funciones del proyecto. |
| [ ] | DAT-04 | P1 | Perfiles de empleados no están conectados a `PERFILES`. | Personalización no observable. | Crear mapa de adaptación específico para `dev_junior`, `comercial`, `remoto_eu`. |
| [ ] | DOC-01 | P1 | README es el enunciado del reto. | No explica instalación, ejecución real ni decisiones. | Reescribir tras estabilizar: arquitectura, setup, demos, robustez, benchmark y limitaciones. |
| [ ] | DOC-02 | P1 | `matriz_decision.md` contiene `TODO`. | Entregable incompleto. | Rellenar desde resultados. |
| [ ] | DOC-03 | P1 | `recomendacion.md` contiene `TODO`. | Entregable incompleto. | Rellenar después de benchmark. |
| [ ] | DOC-04 | P1 | No se ha proporcionado `requirements.txt`, `.env.example`, `.gitignore` ni tests. | Reproducibilidad no verificable. | Añadirlos o confirmar que existen en el repo. |
| [ ] | DOC-05 | P1 | No hay resultados en `output/`. | Parte 4 incompleta. | Generar CSV, JSON e informe. |

---
## 6. Problemas de diseño que requieren reestructuración

### 6.1 El concepto de “perfil” está mezclando dos dimensiones

Los datos definen perfiles de empleado:

- `dev_junior`;
- `comercial`;
- `remoto_eu`.

La configuración define perfiles funcionales:

- `onboarding`;
- `administrativo_rrhh`;
- `it`.

No representan lo mismo. El código reemplaza `perfil_activo` con la función elegida y pierde la adaptación exigida por el enunciado.

**Diseño recomendado:**

```python
turno_preparado = {
    "perfil_empleado": empleado["perfil"],
    "perfil_funcional": seleccionar_perfil_funcional(...),
    "departamento": empleado["departamento"],
    "dia_onboarding": estado["dia_onboarding"],
    ...
}
```

El prompt combina ambas dimensiones:

- `dev_junior`: explicación guiada y términos técnicos explicados;
- `comercial`: respuesta breve, orientada a CRM/proceso comercial;
- `remoto_eu`: destacar ubicación, país de contratación y restricciones cross-border;
- perfil funcional IT/RRHH/onboarding: determina rol y tipo de procedimiento.

### 6.2 El día de onboarding debe ser estado simulado, no fecha actual

La práctica exige demostrar días 1–5. El cálculo actual sirve como utilidad de calendario, pero no como fuente principal de la demo.

**Contrato recomendado:**

```python
def inicializar_estado(empleado: dict, dia_onboarding: int = 1) -> dict:
    validar_dia_onboarding(dia_onboarding)  # 1..5 en demo
    return {
        "empleado": deepcopy(empleado),
        "dia_onboarding": dia_onboarding,
        "messages": [],
        "turnos": 0,
        "eventos_seguridad": [],
        "checklist": {},
    }
```

`logic.py` consume el día del estado. `fecha_referencia` puede quedar solo para tests opcionales.

### 6.3 La recuperación necesita una regla explícita de departamento y día

La puntuación actual permite mezclar Engineering y Sales. Para preguntas de plan o checklist:

1. filtrar documento del departamento del empleado;
2. incluir documentos transversales relevantes;
3. extraer solo las tareas del día pedido;
4. no incluir documentos de otro departamento salvo que la pregunta lo solicite explícitamente y sea información autorizada.

### 6.4 Un único contrato estructurado no sirve para chat y checklist

Se necesitan dos schemas:

**Chat**

```python
{
    "in_scope": bool,
    "category": str,
    "answer": str,
    "document_ids": list[str],
    "faq_ids": list[str],
    "needs_escalation": bool,
    "escalation_department": str | None
}
```

**Checklist**

```python
{
    "empleado_id": str,
    "dia": int,
    "tareas": [
        {
            "id": str,
            "titulo": str,
            "completada": false,
            "fuente_doc": str
        }
    ],
    "mensaje_resumen": str
}
```

No se debe reutilizar `answer` para el checklist.

### 6.5 El benchmark debe usar el mismo pipeline que producción

La única diferencia entre modelos debe ser `model_id`. El benchmark no debe construir respuestas mock ni otro prompt paralelo.

Flujo:

```text
caso estructurado
  -> cargar empleado y día
  -> preparar_turno_con_modo
  -> construir prompt con prompts.py
  -> llamar cliente con model_id del caso experimental
  -> parsear schema
  -> validar salida
  -> guardar respuesta y métricas
```

---

## 7. Arquitectura objetivo mínima

No se recomienda añadir frameworks, clases de servicio o más capas genéricas. La estructura ya propuesta por el reto es suficiente:

```text
programa/
├── __init__.py
├── config.py          # constantes, rutas y schemas/config
├── context.py         # carga, validación y selección de fuentes
├── state.py           # sesión, historial, día, checklist, eventos
├── validators.py      # entrada, contexto, contrato y salida segura
├── prompts.py         # builders de chat/checklist, seguro/vulnerable
├── gemini_auth.py     # carga explícita de credencial
├── gemini_client.py   # llamada parametrizada, parseo y métricas
├── logic.py           # orquestación de casos de uso
├── main.py            # demos y CLI
└── benchmark.py       # ejecución comparativa y exportación
```

### Sobre `model_registry.py` y `model_utils.py`

Para dos modelos, la opción más simple es reemplazarlos por un diccionario `BENCHMARK_MODELS` en `config.py`. Si Ale desea conservar el registry, debe ser la única fuente de IDs y metadatos; `config.py` no debe duplicar `MODEL_1`, `MODEL_2` y precios.

### Regla de diseño

Cada módulo debe responder a una pregunta:

- `config`: ¿qué valores y contratos son configurables?
- `context`: ¿qué fuentes autorizadas son relevantes?
- `state`: ¿qué sabe la sesión y qué se ha guardado?
- `validators`: ¿puede avanzar el dato y cumple el contrato?
- `prompts`: ¿qué instrucciones y datos se envían?
- `gemini_client`: ¿cómo se llama al proveedor y se mide?
- `logic`: ¿en qué orden se ejecuta el caso de uso?
- `main`: ¿cómo se demuestra y opera el producto?
- `benchmark`: ¿cómo se repite la misma prueba con modelos distintos?

---

## 10. Reparto de tareas por miembro

El reparto se basa en las responsabilidades actuales, pero evita que la arquitectura base absorba trabajo de seguridad, estado o benchmark.

### Enric — arquitectura base y contexto

**Objetivo:** dejar un núcleo simple y ejecutable, no añadir abstracciones.

Tareas:

1. Estandarizar imports relativos y añadir `__init__.py`.
2. Corregir los dos `append()` de `context.py`.
3. Añadir validación de estructura de fuentes.
4. Corregir la recuperación para no mezclar departamentos.
5. Integrar selección explícita por día para chat/checklist.
6. Separar `perfil_empleado` y `perfil_funcional` en `turno_preparado` junto con Lucas.
7. Reducir `logic.py`: mover operaciones de estado y validación de contrato fuera.
8. Limpiar aliases, bloques “ELIMINADO”, código comentado y duplicidades.
9. Ser propietario del flujo de `main.py`, pero no del contenido de seguridad ni del cliente.

**No debe añadir:** factories, clases manager, estrategias genéricas, múltiples mains o contextos paralelos.

**Criterio de aceptación:** consultas de Slack, vacaciones, baja médica y primera semana preparan contexto correcto sin LLM y sin excepciones.

### Ale — LLM, modo vulnerable y benchmark

**Objetivo:** conectar el proveedor real y generar mediciones reproducibles.

Tareas:

1. Definir schemas de chat y checklist con revisión de Alex.
2. Corregir `gemini_client.py`: sin efectos al importar, modelo parametrizado, system instruction, schema, parseo, métricas y errores.
3. Construir el prompt vulnerable desde el mismo turno preparado.
4. Elegir una única fuente de modelos; simplificar/eliminar registry y utils si no aportan valor.
5. Actualizar precios y límites con fecha/fuente.
6. Crear `preguntas_benchmark.json` con 10–14 casos.
7. Ejecutar ambos modelos con misma temperatura y pipeline.
8. Exportar CSV y JSON a `output/`.
9. Guardar respuestas, latencia, tokens, coste, estado, error y metadatos.
10. Preparar datos para matriz y recomendación.

**Criterio de aceptación:** cambiar `model_id` cambia realmente el modelo invocado y produce dos filas por caso con métricas reales.

### Alex — robustez y seguridad

**Objetivo:** completar las tres puertas y demostrar fail-closed.

Tareas:

1. Corregir la tupla de credenciales.
2. Separar participantes externos de fuera de dominio general.
3. Refinar credenciales y datos personales para reducir falsos positivos/negativos.
4. Recuperar cobertura de inyección prevista y escribir tests para cada patrón.
5. Añadir `build_secure_system_instruction()` y `build_secure_turn_contents()` en colaboración con Ale.
6. Completar validación de salida sobre un schema ya validado.
7. Validar fuentes de chat y checklist.
8. Crear cinco casos trampa propios.
9. Crear demo seguro vs vulnerable y contador de invocaciones.
10. Añadir pruebas de que una entrada/salida bloqueada no entra en historial.
11. Documentar límites reales y falsos positivos conocidos.

**Criterio de aceptación:** todos los casos trampa bloquean antes de `count_tokens()` en seguro y autorizan una llamada en vulnerable.

### Lucas — estado, día y checklist

**Objetivo:** convertir `state.py` en la fuente de verdad de la sesión.

Tareas:

1. Rediseñar `inicializar_estado()` con copia del empleado y día simulado.
2. Validar día 1–5 para demos.
3. Implementar `ultimos_turnos()` correctamente.
4. Acotar historial almacenado.
5. Mover el registro de eventos de seguridad desde `logic.py`.
6. Añadir estado mínimo de checklist y funciones para marcar tareas.
7. Probar que turnos bloqueados no incrementan el contador.
8. Colaborar con Enric en el contrato de `turno_preparado`.
9. Preparar tests de estado y fixtures reutilizables por el equipo.

**Criterio de aceptación:** el estado conoce empleado, perfil, día, historial, checklist y eventos sin depender de variables duplicadas en `main.py`.

## 12. Orden exacto de reparación

1. Congelar nuevas funcionalidades hasta cerrar P0.
2. Estandarizar imports y forma de ejecución.
3. Corregir regex de credenciales.
4. Corregir selección de FAQ/documentos.
5. Añadir tests mínimos para que esos fallos no regresen.
6. Fijar contratos de estado, turno, chat y checklist.
7. Corregir perfil y día simulado.
8. Corregir recuperación por departamento/día.
9. Implementar apartado 7 de prompts.
10. Implementar apartado 8 del cliente.
11. Sustituir mock de `main.py`.
12. Implementar checklist y demos.
13. Completar casos trampa y fail-closed.
14. Construir benchmark real.
15. Ejecutar benchmark y completar entregables.
16. Limpiar código muerto y reescribir README.

No conviene empezar por el benchmark: actualmente mediría mocks y no el producto.

## 14. Dataset de benchmark recomendado

Mínimo 12 casos para cubrir bien el reto:

1. Slack — Engineering, día 1.
2. Portátil no recibido — remoto UE.
3. Primera semana — Engineering, día 3.
4. Primera semana — Sales, día 3.
5. Operations y cohortes.
6. Vacaciones en España.
7. Trabajo desde otro país — remoto UE.
8. Buddy.
9. Baja médica explícita.
10. Baja ambigua.
11. Salario/bonus.
12. Inyección.
13. Participante externo.
14. Política inexistente.

Los casos bloqueados en modo seguro deben registrar `llamada_modelo=False` y tokens/latencia de modelo vacíos o cero con una columna que lo explique. No se deben inventar métricas de una llamada que no ocurrió.

Ejemplo de caso estructurado:

```json
{
  "id": "bench_01_slack_dev",
  "tipo": "chat",
  "empleado_id": "emp_01",
  "dia_onboarding": 1,
  "consulta": "¿A qué canales de Slack debo unirme hoy?",
  "modo": "seguro",
  "categoria_esperada": "it",
  "docs_esperados": ["doc_it_02"],
  "debe_llamar_modelo": true
}
```

---

## 15. Formato de resultados del benchmark

Cada fila debe incluir:

- `run_id`;
- `timestamp`;
- `case_id`;
- `model_id`;
- `temperature`;
- `modo`;
- `empleado_id`;
- `dia_onboarding`;
- `llamada_modelo`;
- `status`;
- `error`;
- `latencia_total_ms`;
- `latencia_modelo_ms`;
- `tokens_input`;
- `tokens_output`;
- `tokens_total`;
- `coste_estimado_usd`;
- `respuesta`;
- `document_ids`;
- `faq_ids`;
- `cumple_schema`;
- `fidelidad_1_3`;
- `relevancia_1_3`;
- `tono_1_3`;
- `seguridad_1_3`.

La matriz de decisión se completa después de la revisión manual, no desde respuestas mock.

---

## 16. Criterios de aceptación antes de seguir desarrollando

### Reparación base

- [ ] No hay constantes importadas que no existan.
- [ ] Una consulta legítima prepara turno sin excepciones.
- [ ] Contexto no mezcla departamentos en casos de plan/checklist.
- [ ] Día 1–5 es explícito y reproducible.
- [ ] Los tres perfiles del enunciado se observan en la salida.

### Robustez

- [x] Modo por defecto seguro.
- [x] Usuario final no puede activar vulnerable.
- [?] Inyección/salario/externo/política/baja ambigua bloquean con el código esperado.
- [?] Cero llamadas a `count_tokens()` y `generate_content()` si se bloquea antes.
- [x] Entrada bloqueada no entra en historial.
- [x] Sistema y usuario se envían por canales separados.
- [x] Salida cumple schema y solo cita fuentes autorizadas.

### Producto

- [ ] Chat real funcional.
- [ ] Checklist JSON funcional.
- [ ] Demos 1–3 ejecutables.
- [x] Demo vulnerable vs seguro ejecutable.

### Benchmark y entrega

- [x] 10 o más casos finales.
- [ ] Dos modelos realmente invocados.
- [x] Misma temperatura y pipeline.
- [ ] Tokens/latencia reales.
- [ ] CSV y JSON en `output/`.
- [ ] Matriz y recomendación completas.
- [ ] README reproducible.
- [x] Una PR revisada y mergeada por miembro.

---

## 17. Riesgos que deben documentarse

1. Los regex no garantizan bloquear toda prompt injection.
2. La seguridad empresarial requiere control de acceso, no solo filtros de texto.
3. La recuperación léxica puede producir falsos positivos y falsos negativos.
4. Una respuesta con un ID autorizado aún puede inventar contenido.
5. Los precios y modelos cambian; deben fecharse.
6. El modo vulnerable debe quedar limitado a demos/tests.
7. No se deben almacenar ataques completos ni datos sensibles en logs.
8. La comparación de modelos de razonamiento no es idéntica aunque la temperatura sea igual; se debe documentar la configuración de thinking y mantener el resto constante.
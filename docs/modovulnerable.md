# Modo Vulnerable

## Objetivo

Esta rama desarrolla el modo vulnerable requerido en la Parte 3 — Robustez del Team Challenge Employee Onboarding Assistant.

El objetivo es disponer de un flujo base del asistente que permita comparar el comportamiento del sistema antes y después de aplicar las medidas de seguridad desarrolladas en el modo seguro.

## Alcance

El modo vulnerable deberá:

- reutilizar la arquitectura común del asistente;
- recibir las mismas entradas que el modo seguro;
- utilizar el mismo contexto de onboarding;
- utilizar el mismo modelo y configuración;
- permitir la ejecución de los casos trampa;
- servir como referencia para la demo comparativa vulnerable vs seguro.

## Comparación experimental

La comparación entre ambos modos deberá mantener, siempre que sea posible, las mismas condiciones:

- mismo input;
- mismo empleado;
- mismo día de onboarding;
- mismo contexto seleccionado;
- mismo modelo;
- misma temperatura.

La diferencia principal será la aplicación de las medidas de validación y protección correspondientes al modo seguro.

## Flujo previsto

### Modo vulnerable

Input del usuario

→ Contexto de onboarding

→ Construcción del prompt

→ Llamada al modelo

→ Respuesta


### Modo seguro

Input del usuario

→ Validación de seguridad

→ Rechazo o continuación del flujo

→ Contexto de onboarding

→ Construcción del prompt

→ Llamada al modelo

→ Respuesta


## Casos trampa

La comparación deberá incluir los cinco tipos de casos requeridos por el Team Challenge:

1. Prompt injection.
2. Pregunta sobre salario o bonus.
3. Consulta fuera del dominio del asistente.
4. Pregunta sobre una política no documentada.
5. Ambigüedad entre baja médica y baja laboral.

Los casos serán redactados por el equipo y no copiarán literalmente los ejemplos proporcionados en los datos del reto.

## Criterios de integración

El desarrollo del modo vulnerable deberá evitar duplicar funcionalidades pertenecientes a otras partes del proyecto.

Siempre que sea posible se reutilizarán:

- selección de contexto;
- gestión del empleado;
- día de onboarding;
- construcción de prompts;
- cliente del modelo.

La integración final se realizará mediante Pull Request desde:

`feature/modovulnerable`

hacia:

`develop`

## Estado actual

🚧 En desarrollo.

La implementación se realizará sobre la arquitectura común del proyecto una vez identificadas las funciones y contratos que deben reutilizarse.


## Documentación y justificación de decisiones en modo vulnerable

1. *def build_vulnerable_prompt* en prompts.py

Se ha optado por una vulnerabilidad realista y plausible, evitando introducir comportamientos deliberadamente inseguros o excesivamente obvios. El fallo principal consiste en incorporar directamente el mensaje del usuario al prompt, sin establecer una separación efectiva entre instrucciones confiables y contenido no confiable.

Además, el asistente recibe una autorización implícita y poco delimitada para utilizar la documentación disponible, reproduciendo un error habitual en sistemas RAG: confundir la capacidad de recuperar información con la autorización para utilizarla o revelarla.

Esta implementación permite demostrar los riesgos de prompt injection y control de acceso deficiente a partir de errores de diseño comunes en prototipos y MVP reales, manteniendo una progresión pedagógica clara hacia las posteriores fases de detección y defensa.

2. 
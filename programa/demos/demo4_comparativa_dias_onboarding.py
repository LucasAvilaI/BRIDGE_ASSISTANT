"""
Demo 4, adicional: adaptación al día de onboarding.

Objetivo
--------
- Ejecutar una consulta equivalente para el mismo empleado en dos días.
- Comparar día 1 y día 3.
- Verificar que el día 3 no repite de forma indiscriminada tareas del día 1.
- Demostrar que el día simulado afecta a la recuperación y al prompt.

Caso recomendado
--------
- Empleado: Dev Junior.
- Consulta: "¿Qué debo hacer hoy?"
- Comparación: día 1 frente a día 3.

Qué demuestra
-------------
TODO
...
"""

# ============================================================
# CONFIGURACIÓN
# ============================================================

...

# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_empleado_demo() -> dict:
    ...

def obtener_dias_demo() -> tuple[int, int]:
    ...

# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_comparativa_dias_onboarding() -> None:
    """
    Compara la respuesta para distintos días de onboarding.
    """
    

"""
AVISO DE INTEGRACIÓN

Este archivo implementa únicamente la lógica de demostración.

No debe modificar ni sustituir el comportamiento de:

- logic.py
- context.py
- validators.py
- robustez
- preparación de contexto
- pipeline del asistente

Las llamadas a dichos módulos deben realizarse utilizando sus interfaces
públicas.

TODO-INTEGRACIÓN:
Cuando el equipo publique la versión definitiva del flujo, sustituir
únicamente las llamadas marcadas como provisionales, sin modificar la
estructura de esta demo.
"""

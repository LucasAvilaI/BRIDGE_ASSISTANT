"""
Demo 3 · Comparativa de perfiles.

Objetivo
--------
- Ejecutar exactamente la misma consulta con dos perfiles diferentes.
- Comparar una persona Comercial con una persona Remoto UE.
- Demostrar cambios de tono, contexto, ejemplos y prioridades.
- Mantener el mismo modelo y la misma configuración.

Caso recomendado
--------
- Consulta común: "¿Qué debo tener preparado durante mi primera semana?"
- Perfil 1: Comercial.
- Perfil 2: Remoto UE.
"""

"""
AVISO DE INTEGRACIÓN
--------------------
Este archivo está pendiente de consolidación con la implementación real
existente en el proyecto.

No crear, renombrar ni duplicar funciones únicamente para adaptarlas al menú.
La función pública de entrada debe determinarse a partir del código real de
esta demo y de los contratos ya utilizados por main.py, logic.py y los tests.

Hasta confirmar ese contrato:

- conservar las funciones existentes;
- conservar sus parámetros y valores de retorno;
- no modificar llamadas a Robustez ni a Validadores;
- no trasladar lógica de negocio al menú;
- marcar integraciones pendientes con TODO-INTEGRACIÓN;
- actualizar menu.py solo cuando se conozca el nombre real de la función
  pública de entrada.

TODO-INTEGRACIÓN:
Confirmar la función real que ejecutará esta demo y registrar ese nombre
en menu.py sin alterar su implementación interna.
"""

# ============================================================
# CONFIGURACIÓN
# ============================================================

...

# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_perfiles_demo() -> tuple[dict, dict]:
    ...

def obtener_consulta_demo() -> str:
    ...

# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_comparativa_perfiles() -> None:
    """
    Compara la respuesta para distintos perfiles.
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
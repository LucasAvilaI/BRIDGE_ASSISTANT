"""Demo de los cinco casos trampa propios del equipo.

Objetivo
--------
- Ejecutar los cinco casos definidos por el equipo.
- Validar el código de rechazo esperado.
- Confirmar que los casos bloqueados no llaman al modelo.
- Mostrar un resumen reproducible de aprobados y fallidos.

Cobertura mínima:
1. Inyección de instrucciones.
2. Salario o bonus.
3. Participante externo o fuera de dominio.
4. Política no documentada.
5. Ambigüedad entre baja médica y baja laboral.
"""

# ============================================================
# CONFIGURACIÓN
# ============================================================

...

# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_casos_demo() -> list[str]:
    ...

# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_casos_trampa() -> None:
    """
    Ejecuta la batería de consultas problemáticas.
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
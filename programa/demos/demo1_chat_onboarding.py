"""
Demo 1, obligatoria · Chat de onboarding.

Objetivo
--------
- Ejecutar una consulta legítima de un empleado Dev Junior.
- Recuperar documentación y FAQ relevantes.
- Construir el turno con perfil, día e historial.
- Invocar el modelo en modo seguro.
- Mostrar una respuesta breve respaldada por fuentes autorizadas.

Esta demo únicamente orquesta llamadas a las interfaces públicas de
logic.py, prompts.py y gemini_client.py. No reimplementa selección de
contexto, validaciones ni construcción de prompts.
"""

from __future__ import annotations

from config import (
    ASSISTANT_CONFIG_DEFAULT,
    DOCS_PATH,
    EMPLEADOS_PATH,
    EMPRESA_PATH,
    FAQ_PATH,
)
from context import buscar_empleado, cargar_json
from gemini_client import (
    GeminiClientError,
    parsear_json,
    safe_generate_with_system_instruction,
)
from logic import finalizar_turno_seguro, preparar_turno_seguro
from metrics import formatear_metricas_turno
from prompts import build_secure_system_instruction, build_secure_turn_contents
from state import inicializar_estado

# ============================================================
# CONFIGURACIÓN
# ============================================================

EMPLEADO_ID_DEMO = "emp_01"
CONSULTA_DEMO = "¿A qué canales de Slack tengo que unirme en mi primera semana?"


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_empleado_demo() -> dict:
    """Carga el empleado de demostración (dev junior, emp_01)."""
    empleados = cargar_json(EMPLEADOS_PATH)
    empleado = buscar_empleado(empleados, EMPLEADO_ID_DEMO)

    if empleado is None:
        raise ValueError(
            f"No se encontró el empleado de demo '{EMPLEADO_ID_DEMO}' "
            "en empleados_demo.json."
        )

    return empleado


def obtener_consulta_demo() -> str:
    """Consulta legítima de ejemplo dentro del dominio de onboarding."""
    return CONSULTA_DEMO


# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_chat_onboarding() -> None:
    """Ejecuta la demostración del flujo completo del asistente."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)

    empleado = obtener_empleado_demo()
    consulta = obtener_consulta_demo()

    estado = inicializar_estado()

    print(f"Empleado: {empleado.get('nombre', '(sin nombre)')} ({empleado.get('id')})")
    print(f"Consulta: {consulta}\n")

    preparacion = preparar_turno_seguro(
        estado=estado,
        consulta=consulta,
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        configuracion=ASSISTANT_CONFIG_DEFAULT,
    )

    if preparacion.get("status") != "ok":
        print("[ERROR]", preparacion.get("mensaje"))
        for error in preparacion.get("data", {}).get("errores", []):
            print("-", error)
        return

    datos = preparacion["data"]

    if not datos.get("llamar_modelo", False):
        print("Asistente (respuesta controlada, sin llamar al modelo):")
        print(datos.get("respuesta", ""))
        return

    turno_preparado = datos["turno_preparado"]

    try:
        texto_modelo, metricas = safe_generate_with_system_instruction(
            build_secure_turn_contents(turno_preparado),
            system_instruction=build_secure_system_instruction(),
            json_mode=True,
        )
        resultado_externo = parsear_json(texto_modelo)
    except (GeminiClientError, ValueError, TypeError) as error:
        print("[ERROR] No se pudo completar la llamada al modelo:", error)
        return

    resultado_final = finalizar_turno_seguro(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )

    if resultado_final.get("status") != "ok":
        print("[ERROR]", resultado_final.get("mensaje"))
        for error in resultado_final.get("data", {}).get("errores", []):
            print("-", error)
        return

    print("Asistente:")
    print(resultado_final["data"]["respuesta"])
    print()
    print(formatear_metricas_turno(metricas))


if __name__ == "__main__":
    ejecutar_demo_chat_onboarding()

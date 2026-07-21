"""
Demo 2, obligatoria · Checklist del día 1.

Objetivo
--------
- Indicar al asistente quién es el empleado y qué día de onboarding
  le toca (día 1).
- Generar el plan del día en JSON, con tareas respaldadas por
  documentación autorizada (ver contrato en
  config.CHECKLIST_JSON_SCHEMA_HINT).

Usa preparar_checklist_seguro() / finalizar_checklist_seguro() de
logic.py, añadidas para dar soporte a esta capacidad (antes no existía
ningún punto de entrada de checklist conectado de extremo a extremo).
"""
from __future__ import annotations

import os
import sys

# Ver el mismo comentario en demo1_chat_onboarding.py: este proyecto
# usa imports bare en todos los módulos internos, no "programa.x".
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from state import inicializar_estado
from prompts import (
    build_checklist_system_instruction,
    build_checklist_turno_contents,
)
from metrics import formatear_metricas_turno
from logic import finalizar_checklist_seguro, preparar_checklist_seguro
from gemini_client import (
    GeminiClientError,
    parsear_json,
    safe_generate_with_system_instruction,
)
from context import buscar_empleado, cargar_json
from config import DOCS_PATH, EMPLEADOS_PATH, EMPRESA_PATH, FAQ_PATH, FALLBACK_MODEL

# ============================================================
# CONFIGURACIÓN
# ============================================================

EMPLEADO_ID_DEMO = "emp_01"
DIA_DEMO = 1


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_empleado_demo() -> dict:
    """Carga el empleado de demostración (Laura, dev junior, emp_01)."""
    empleados = cargar_json(EMPLEADOS_PATH)
    empleado = buscar_empleado(empleados, EMPLEADO_ID_DEMO)

    if empleado is None:
        raise ValueError(
            f"No se encontró el empleado de demo '{EMPLEADO_ID_DEMO}' "
            "en empleados_demo.json."
        )

    return empleado


def obtener_dia_demo() -> int:
    return DIA_DEMO


# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_checklist_dia_1() -> None:
    """Genera el checklist estructurado del día 1."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)

    empleado = obtener_empleado_demo()
    dia = obtener_dia_demo()

    estado = inicializar_estado()

    print(
        f"Empleado: {empleado.get('nombre', '(sin nombre)')} ({empleado.get('id')})")
    print(f"Día de onboarding solicitado: {dia}\n")

    preparacion = preparar_checklist_seguro(
        estado=estado,
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        dia_onboarding=dia,
    )

    if preparacion.get("status") != "ok":
        print("[ERROR]", preparacion.get("mensaje"))
        for error in preparacion.get("data", {}).get("errores", []):
            print("-", error)
        return

    datos = preparacion["data"]

    if not datos.get("llamar_modelo", False):
        print("No se ha podido generar el checklist (respuesta controlada):")
        print(datos.get("respuesta", ""))
        return

    turno_preparado = datos["turno_preparado"]

    try:
        texto_modelo, metricas = safe_generate_with_system_instruction(
            build_checklist_turno_contents(turno_preparado),
            system_instruction=build_checklist_system_instruction(),
            json_mode=True,
            fallback_model_id=FALLBACK_MODEL,
        )
        resultado_externo = parsear_json(texto_modelo)
    except (GeminiClientError, ValueError, TypeError) as error:
        print("[ERROR] No se pudo completar la llamada al modelo:", error)
        return

    resultado_final = finalizar_checklist_seguro(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )

    if resultado_final.get("status") != "ok":
        print("[ERROR]", resultado_final.get("mensaje"))
        for error in resultado_final.get("data", {}).get("errores", []):
            print("-", error)
        return

    checklist = resultado_final["data"]["checklist"]

    print(
        f"Checklist día {checklist.get('dia')} — {checklist.get('empleado_id')}")
    print(f"Resumen: {checklist.get('mensaje_resumen')}\n")

    for tarea in checklist.get("tareas", []):
        print(
            f"[ ] {tarea.get('id')}: {tarea.get('titulo')} (fuente: {tarea.get('fuente_doc')})")

    print()
    print(formatear_metricas_turno(metricas))


if __name__ == "__main__":
    ejecutar_demo_checklist_dia_1()

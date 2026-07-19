"""
Demo 4 · Comparativa dinámica de días de onboarding.

Objetivo
--------
- Generar el checklist del mismo empleado para varios días de
  onboarding (por defecto, día 1 y día 3).
- Mostrar cómo cambian las tareas priorizadas entre días, sin repetir
  lo ya cubierto en el día 1 (ver InstruccionesTeamChallenge.md,
  requisito transversal "Día de onboarding simulado").

Esta demo estaba referenciada en menu.py (`demos.demo4_comparativa_dias_onboarding`)
pero el archivo no existía en el proyecto: sin él, cualquier intento
de abrir el menú de demostraciones fallaba con ImportError.
"""

from __future__ import annotations
from state import inicializar_estado
from prompts import (
    build_checklist_system_instruction,
    build_checklist_turno_contents,
)
from logic import finalizar_checklist_seguro, preparar_checklist_seguro
from gemini_client import (
    GeminiClientError,
    parsear_json,
    safe_generate_with_system_instruction,
)
from context import buscar_empleado, cargar_json
from config import DOCS_PATH, EMPLEADOS_PATH, EMPRESA_PATH, FAQ_PATH
from typing import Any

import sys
import os

# Esto añade la carpeta 'programa' al PATH de forma automática al ejecutar el script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ============================================================
# CONFIGURACIÓN
# ============================================================

EMPLEADO_ID_DEMO = "emp_01"
DIAS_DEMO = (1, 3)


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_empleado_demo() -> dict:
    empleados = cargar_json(EMPLEADOS_PATH)
    empleado = buscar_empleado(empleados, EMPLEADO_ID_DEMO)

    if empleado is None:
        raise ValueError(
            f"No se encontró el empleado de demo '{EMPLEADO_ID_DEMO}' "
            "en empleados_demo.json."
        )

    return empleado


def obtener_dias_demo() -> tuple[int, ...]:
    return DIAS_DEMO


# ============================================================
# EJECUCIÓN
# ============================================================

def _generar_checklist_para_dia(
    *,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    dia: int,
) -> dict[str, Any]:
    """Ejecuta el pipeline seguro de checklist para un único día."""
    estado = inicializar_estado()

    preparacion = preparar_checklist_seguro(
        estado=estado,
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        dia_onboarding=dia,
    )

    if preparacion.get("status") != "ok":
        return preparacion

    datos = preparacion["data"]

    if not datos.get("llamar_modelo", False):
        return preparacion

    turno_preparado = datos["turno_preparado"]

    try:
        texto_modelo, _ = safe_generate_with_system_instruction(
            build_checklist_turno_contents(turno_preparado),
            system_instruction=build_checklist_system_instruction(),
            json_mode=True,
        )
        resultado_externo = parsear_json(texto_modelo)
    except (GeminiClientError, ValueError, TypeError) as error:
        return {
            "status": "error",
            "mensaje": "No se pudo completar la llamada al modelo.",
            "data": {"errores": [str(error)]},
        }

    return finalizar_checklist_seguro(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )


def ejecutar_demo_comparativa_dias_onboarding() -> None:
    """Compara los checklists generados para distintos días de onboarding."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)
    empleado = obtener_empleado_demo()

    print(
        f"Empleado: {empleado.get('nombre', '(sin nombre)')} ({empleado.get('id')})\n")

    for dia in obtener_dias_demo():
        print(f"=== DÍA {dia} ===")

        resultado = _generar_checklist_para_dia(
            empleado=empleado,
            empresa=empresa,
            documentos=documentos,
            faqs=faqs,
            dia=dia,
        )

        if resultado.get("status") != "ok":
            print("[ERROR]", resultado.get("mensaje"))
            for error in resultado.get("data", {}).get("errores", []):
                print("-", error)
            print()
            continue

        datos = resultado["data"]

        if "checklist" not in datos:
            print("No se ha podido generar el checklist (respuesta controlada):")
            print(datos.get("respuesta", ""))
            print()
            continue

        checklist = datos["checklist"]
        print(f"Resumen: {checklist.get('mensaje_resumen')}")

        for tarea in checklist.get("tareas", []):
            print(
                f"  [ ] {tarea.get('titulo')} (fuente: {tarea.get('fuente_doc')})")

        print()


if __name__ == "__main__":
    ejecutar_demo_comparativa_dias_onboarding()

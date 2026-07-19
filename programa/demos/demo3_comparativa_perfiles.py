"""
Demo 3 · Comparativa de perfiles.

Objetivo
--------
- Ejecutar exactamente la misma consulta con dos perfiles diferentes.
- Comparar una persona Comercial con una persona Remoto UE.
- Demostrar cambios de tono, contexto, ejemplos y prioridades.
- Mantener el mismo modelo y la misma configuración.

Caso recomendado
-----------------
- Consulta común: "¿Qué debo tener preparado durante mi primera semana?"
- Perfil 1: Comercial.
- Perfil 2: Remoto UE.

Los empleados se localizan por el campo 'perfil' de
empleados_demo.json (búsqueda por palabra clave, sin acentos ni
mayúsculas) en lugar de un ID fijo, para no depender de que el
dataset de demo mantenga siempre el mismo orden o los mismos IDs.
"""

from __future__ import annotations
from state import inicializar_estado
from prompts import build_secure_system_instruction, build_secure_turn_contents
from logic import finalizar_turno_seguro, preparar_turno_seguro
from gemini_client import (
    GeminiClientError,
    parsear_json,
    safe_generate_with_system_instruction,
)
from context import cargar_json, normalizar_texto
from config import ASSISTANT_CONFIG_DEFAULT, DOCS_PATH, EMPLEADOS_PATH, EMPRESA_PATH, FAQ_PATH

import sys
import os

# Esto añade la carpeta 'programa' al PATH de forma automática al ejecutar el script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ============================================================
# CONFIGURACIÓN
# ============================================================

CONSULTA_DEMO = "¿Qué debo tener preparado durante mi primera semana?"
PALABRA_CLAVE_PERFIL_1 = "comercial"
PALABRA_CLAVE_PERFIL_2 = "remoto"


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def _buscar_empleado_por_perfil(empleados: list[dict], palabra_clave: str) -> dict | None:
    """Busca el primer empleado cuyo campo 'perfil' contenga la palabra clave."""
    palabra_normalizada = normalizar_texto(palabra_clave)

    for empleado in empleados:
        perfil = normalizar_texto(empleado.get("perfil", ""))

        if palabra_normalizada in perfil:
            return empleado

    return None


def obtener_perfiles_demo() -> tuple[dict, dict]:
    """Devuelve un empleado Comercial y un empleado Remoto UE de la demo."""
    empleados = cargar_json(EMPLEADOS_PATH)

    empleado_comercial = _buscar_empleado_por_perfil(
        empleados, PALABRA_CLAVE_PERFIL_1)
    empleado_remoto_ue = _buscar_empleado_por_perfil(
        empleados, PALABRA_CLAVE_PERFIL_2)

    if empleado_comercial is None or empleado_remoto_ue is None:
        raise ValueError(
            "No se han encontrado en empleados_demo.json un empleado con "
            "perfil 'Comercial' y otro con perfil 'Remoto UE' para la "
            "comparativa."
        )

    return empleado_comercial, empleado_remoto_ue


def obtener_consulta_demo() -> str:
    return CONSULTA_DEMO


# ============================================================
# EJECUCIÓN
# ============================================================

def _ejecutar_consulta(*, empleado: dict, empresa: dict, documentos: list[dict], faqs: list[dict], consulta: str) -> dict:
    """Ejecuta el pipeline seguro completo para un empleado y devuelve el resultado final."""
    estado = inicializar_estado()

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
        return preparacion

    datos = preparacion["data"]

    if not datos.get("llamar_modelo", False):
        return preparacion

    turno_preparado = datos["turno_preparado"]

    try:
        texto_modelo, _ = safe_generate_with_system_instruction(
            build_secure_turn_contents(turno_preparado),
            system_instruction=build_secure_system_instruction(),
            json_mode=True,
        )
        resultado_externo = parsear_json(texto_modelo)
    except (GeminiClientError, ValueError, TypeError) as error:
        return {
            "status": "error",
            "mensaje": "No se pudo completar la llamada al modelo.",
            "data": {"errores": [str(error)]},
        }

    return finalizar_turno_seguro(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )


def _mostrar_resultado(titulo: str, empleado: dict, resultado: dict) -> None:
    print(f"=== {titulo}: {empleado.get('nombre', '(sin nombre)')} "
          f"({empleado.get('perfil', '(sin perfil)')}) ===")

    if resultado.get("status") != "ok":
        print("[ERROR]", resultado.get("mensaje"))
        for error in resultado.get("data", {}).get("errores", []):
            print("-", error)
        print()
        return

    datos = resultado["data"]

    if "motivo_bloqueo" in datos:
        print("(respuesta controlada, sin llamar al modelo)")

    print(datos.get("respuesta", ""))
    print()


def ejecutar_demo_comparativa_perfiles() -> None:
    """Compara la respuesta del asistente para distintos perfiles."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)

    empleado_comercial, empleado_remoto_ue = obtener_perfiles_demo()
    consulta = obtener_consulta_demo()

    print(f"Consulta común: {consulta}\n")

    resultado_comercial = _ejecutar_consulta(
        empleado=empleado_comercial,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        consulta=consulta,
    )
    _mostrar_resultado("PERFIL COMERCIAL",
                       empleado_comercial, resultado_comercial)

    resultado_remoto_ue = _ejecutar_consulta(
        empleado=empleado_remoto_ue,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        consulta=consulta,
    )
    _mostrar_resultado("PERFIL REMOTO UE",
                       empleado_remoto_ue, resultado_remoto_ue)


if __name__ == "__main__":
    ejecutar_demo_comparativa_perfiles()

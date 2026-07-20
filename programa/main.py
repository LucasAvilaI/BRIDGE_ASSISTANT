"""
Punto de entrada del asistente de onboarding.

La aplicación utiliza siempre el pipeline seguro. La comparación con una
integración vulnerable está aislada exclusivamente en la Demo 5.
"""

from __future__ import annotations

import sys
import os

# Añade la carpeta padre (la raíz 'BRIDGE_ASSISTANT') al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Any

from config import (
    ASSISTANT_CONFIG_DEFAULT,
    DOCS_PATH,
    EMPLEADOS_PATH,
    EMPRESA_PATH,
    FAQ_PATH,
)
from context import buscar_empleado, cargar_json
from gemini_auth import GeminiAuthError, configurar_gemini_api_key
from gemini_client import GeminiClientError, parsear_json, safe_generate_with_system_instruction
from logic import finalizar_turno_seguro, preparar_turno_seguro
from menu import ejecutar_menu
from metrics import formatear_metricas_turno
from prompts import build_secure_system_instruction, build_secure_turn_contents
from state import inicializar_estado


# ============================================================
# CONFIGURACIÓN DE LA INTERFAZ
# ============================================================

COMANDOS_SALIDA = frozenset({"salir", "exit", "quit"})


# ============================================================
# AUTENTICACIÓN
# ============================================================

def configurar_autenticacion() -> bool:
    """
    Configura las credenciales de Gemini antes de ejecutar cualquier
    funcionalidad que pueda invocar al modelo.

    Aplica una política fail-closed: si la autenticación falla, no se
    permite continuar con la aplicación ni con las demostraciones.
    """
    try:
        configurar_gemini_api_key(
            interactivo=True,
            sobrescribir=False,
        )
    except GeminiAuthError as error:
        print("\n[CRÍTICO] Fallo de inicialización de seguridad:")
        print(f"- {error}")
        print(
            "El asistente no puede operar sin credenciales válidas. "
            "Cierre seguro."
        )
        return False

    return True


# ============================================================
# CARGA DE DATOS
# ============================================================

def cargar_datos() -> dict:
    """
    Carga las fuentes de datos utilizadas por la aplicación.

    La validación detallada del contenido de empleados, documentos
    y preguntas frecuentes corresponde a context.py.
    """
    empresa = cargar_json(EMPRESA_PATH)
    empleados = cargar_json(EMPLEADOS_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)

    if not isinstance(empresa, dict):
        raise ValueError(
            "'empresa.json' debe contener un diccionario."
        )

    if not isinstance(empleados, list):
        raise ValueError(
            "'empleados_demo.json' debe contener una lista."
        )

    if not isinstance(documentos, list):
        raise ValueError(
            "'onboarding_docs.json' debe contener una lista."
        )

    if not isinstance(faqs, list):
        raise ValueError(
            "'faq_onboarding.json' debe contener una lista."
        )

    return {
        "empresa": empresa,
        "empleados": empleados,
        "documentos": documentos,
        "faqs": faqs,
    }


# ============================================================
# SELECCIÓN DEL EMPLEADO
# ============================================================

def mostrar_empleados(empleados: list[dict]) -> None:
    """Muestra la información mínima de los empleados disponibles."""
    print("\nEmpleados disponibles:")

    for empleado in empleados:
        empleado_id = empleado.get("id", "(sin ID)")
        nombre = empleado.get("nombre", "(sin nombre)")
        departamento = empleado.get(
            "departamento",
            "(sin departamento)",
        )

        print(
            f"- {empleado_id} | {nombre} | {departamento}"
        )


def seleccionar_empleado(
    empleados: list[dict],
) -> dict | None:
    """
    Solicita el identificador de un empleado hasta encontrar una
    entrada válida o recibir un comando de salida.
    """
    if not empleados:
        print("\nNo hay empleados disponibles.")
        return None

    mostrar_empleados(empleados)

    while True:
        empleado_id = input(
            "\nIntroduce el ID del empleado o escribe 'salir': "
        ).strip()

        if empleado_id.lower() in COMANDOS_SALIDA:
            return None

        empleado = buscar_empleado(
            empleados,
            empleado_id,
        )

        if empleado is not None:
            return empleado

        print(
            "No se ha encontrado ningún empleado con ese "
            "identificador."
        )


# ============================================================
# PRESENTACIÓN DE RESULTADOS
# ============================================================

def imprimir_errores(resultado: dict) -> None:
    """Muestra los errores contenidos en la envolvente estándar."""
    mensaje = resultado.get(
        "mensaje",
        "Se ha producido un error.",
    )

    print(f"\n[ERROR] {mensaje}")

    datos = resultado.get("data", {})
    errores = (
        datos.get("errores", [])
        if isinstance(datos, dict)
        else []
    )

    for error in errores:
        print(f"- {error}")


def imprimir_respuesta_final(resultado: dict) -> None:
    """Muestra la respuesta final destinada al empleado."""
    if resultado.get("status") != "ok":
        imprimir_errores(resultado)
        return

    datos = resultado.get("data", {})

    if not isinstance(datos, dict):
        imprimir_errores(
            {
                "status": "error",
                "mensaje": (
                    "La respuesta contiene una estructura no válida."
                ),
                "data": {
                    "errores": [
                        "El campo 'data' debe ser un diccionario."
                    ]
                },
            }
        )
        return

    respuesta = datos.get("respuesta", "")

    if not isinstance(respuesta, str) or not respuesta.strip():
        imprimir_errores(
            {
                "status": "error",
                "mensaje": (
                    "No se ha recibido una respuesta válida."
                ),
                "data": {
                    "errores": [
                        "Falta el campo 'data.respuesta' "
                        "o está vacío."
                    ]
                },
            }
        )
        return

    print(f"\nAsistente:\n{respuesta.strip()}")


# ============================================================
# ADAPTADOR LLM
# ============================================================

def generar_respuesta_llm(
    turno_preparado: dict,
) -> tuple[dict, Any]:
    """
    Invoca a Gemini mediante el canal seguro (system_instruction
    separado de contents) y devuelve el diccionario ya parseado
    desde JSON junto con las métricas técnicas de la llamada.

    No valida el contrato funcional de la respuesta: eso lo hace
    finalizar_turno_seguro() a través de validators.py. Esta función
    solo se encarga de la llamada externa y de traducir cualquier
    fallo técnico en un error controlado (fail-closed).
    """
    texto_modelo, metricas = safe_generate_with_system_instruction(
        build_secure_turn_contents(turno_preparado),
        system_instruction=build_secure_system_instruction(),
        json_mode=True,
    )

    return parsear_json(texto_modelo), metricas


# ============================================================
# SESIÓN INTERACTIVA
# ============================================================

def ejecutar_sesion(
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
) -> None:
    """
    Ejecuta el chat interactivo mediante el pipeline seguro.

    Cada consulta pasa por las validaciones de entrada y contexto antes
    de autorizar la llamada al modelo. La respuesta externa también se
    valida antes de incorporarse al estado conversacional.
    """
    estado = inicializar_estado()
    nombre = empleado.get(
        "nombre",
        "(sin nombre)",
    )

    print("\n" + "=" * 60)
    print("EMPLOYEE ONBOARDING ASSISTANT")
    print("=" * 60)
    print(f"Empleado activo: {nombre}")
    print(
        "\nEscribe una consulta relacionada con el onboarding."
    )
    print(
        "Para terminar utiliza: salir, exit o quit."
    )

    while True:
        consulta = input("\nConsulta: ").strip()

        if consulta.lower() in COMANDOS_SALIDA:
            print("\nSesión finalizada.")
            return

        # 1. Validación de entrada, preparación y validación
        #    del contexto.
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
            imprimir_errores(preparacion)
            continue

        datos_preparacion = preparacion.get(
            "data",
            {},
        )

        if not isinstance(datos_preparacion, dict):
            imprimir_errores(
                {
                    "status": "error",
                    "mensaje": (
                        "La preparación del turno devolvió "
                        "una estructura no válida."
                    ),
                    "data": {
                        "errores": [
                            "El campo 'data' debe ser "
                            "un diccionario."
                        ]
                    },
                }
            )
            continue

        # La consulta puede haber sido atendida mediante una
        # respuesta controlada sin invocar al modelo.
        if not datos_preparacion.get(
            "llamar_modelo",
            False,
        ):
            imprimir_respuesta_final(preparacion)
            continue

        turno_preparado = datos_preparacion.get(
            "turno_preparado"
        )

        if not isinstance(turno_preparado, dict):
            imprimir_errores(
                {
                    "status": "error",
                    "mensaje": (
                        "No se ha podido continuar con el turno."
                    ),
                    "data": {
                        "errores": [
                            "No se recibió un turno preparado válido."
                        ]
                    },
                }
            )
            continue

        # 2. Invocación del adaptador LLM (canal seguro).
        try:
            resultado_externo, metricas = generar_respuesta_llm(
                turno_preparado
            )
        except (GeminiClientError, ValueError, TypeError) as error:
            imprimir_errores(
                {
                    "status": "error",
                    "mensaje": (
                        "No se pudo completar la llamada "
                        "al modelo."
                    ),
                    "data": {
                        "errores": [str(error)]
                    },
                }
            )
            continue

        # 3. Validación segura de la salida y actualización
        #    del estado conversacional.
        resultado_final = finalizar_turno_seguro(
            estado=estado,
            turno_preparado=turno_preparado,
            resultado_externo=resultado_externo,
        )

        imprimir_respuesta_final(resultado_final)
        print(formatear_metricas_turno(metricas))


# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

def ejecutar_aplicacion_principal() -> None:
    """Carga los datos e inicia el chat interactivo seguro."""
    try:
        datos = cargar_datos()
    except (FileNotFoundError, ValueError, OSError) as error:
        print(
            "\nNo se ha podido iniciar la aplicación debido "
            "a un fallo en las fuentes:"
        )
        print(f"- {error}")
        return

    empleado = seleccionar_empleado(
        datos["empleados"]
    )

    if empleado is None:
        print("\nAplicación finalizada.")
        return

    ejecutar_sesion(
        empleado=empleado,
        empresa=datos["empresa"],
        documentos=datos["documentos"],
        faqs=datos["faqs"],
    )


# ============================================================
# SELECCIÓN DE INTERFAZ
# ============================================================

def seleccionar_interfaz() -> str | None:
    """
    Permite elegir entre el chat principal y el menú de demos.

    Devuelve None cuando el usuario solicita salir.
    """
    while True:
        print("\n" + "=" * 60)
        print("EMPLOYEE ONBOARDING ASSISTANT")
        print("=" * 60)
        print("1. Aplicación principal (chat interactivo seguro)")
        print("2. Menú de demostraciones del sprint")
        print("0. Salir")

        opcion = input(
            "\nSelecciona una opción: "
        ).strip()

        if opcion in {"1", "2"}:
            return opcion

        if opcion == "0" or opcion.lower() in COMANDOS_SALIDA:
            return None

        print(
            "\n[ERROR] Opción no válida. "
            "Selecciona 0, 1 o 2."
        )


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

def main() -> int:
    """
    Inicializa la aplicación y dirige al usuario a la interfaz elegida.

    La autenticación se valida antes de entrar tanto en el chat como en
    el menú de demostraciones.
    """
    opcion = seleccionar_interfaz()

    if opcion is None:
        print("\nAplicación finalizada.")
        return 0

    if not configurar_autenticacion():
        return 1

    if opcion == "2":
        ejecutar_menu()
        return 0

    ejecutar_aplicacion_principal()
    return 0


if __name__ == "__main__":
    sys.exit(main())

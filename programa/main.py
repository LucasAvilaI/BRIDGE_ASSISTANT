from config import (
    ASSISTANT_CONFIG_DEFAULT,
    DOCS_PATH,
    EMPLEADOS_PATH,
    EMPRESA_PATH,
    FAQ_PATH,
)
from context import buscar_empleado, cargar_json
from logic import preparar_turno
from state import inicializar_estado


# ============================================================
# CONFIGURACIÓN DE LA INTERFAZ
# ============================================================

COMANDOS_SALIDA = frozenset(
    {
        "salir",
        "exit",
        "quit",
    }
)


# ============================================================
# CARGA DE DATOS
# ============================================================

def cargar_datos() -> dict:
    """
    Carga las fuentes de datos utilizadas por la aplicación.

    La validación detallada de empleados, documentos y FAQ
    corresponde a context.py.
    """
    empresa = cargar_json(
        EMPRESA_PATH
    )

    empleados = cargar_json(
        EMPLEADOS_PATH
    )

    documentos = cargar_json(
        DOCS_PATH
    )

    faqs = cargar_json(
        FAQ_PATH
    )

    if not isinstance(empresa, dict):
        raise ValueError(
            "empresa.json debe contener un diccionario."
        )

    if not isinstance(empleados, list):
        raise ValueError(
            "empleados_demo.json debe contener una lista."
        )

    if not isinstance(documentos, list):
        raise ValueError(
            "onboarding_docs.json debe contener una lista."
        )

    if not isinstance(faqs, list):
        raise ValueError(
            "faq_onboarding.json debe contener una lista."
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

def mostrar_empleados(
    empleados: list[dict],
) -> None:
    """
    Muestra la información mínima de los empleados disponibles.
    """
    print("\nEmpleados disponibles:")

    for empleado in empleados:
        empleado_id = empleado.get(
            "id",
            "(sin ID)",
        )

        nombre = empleado.get(
            "nombre",
            "(sin nombre)",
        )

        departamento = empleado.get(
            "departamento",
            "(sin departamento)",
        )

        print(
            f"- {empleado_id} | "
            f"{nombre} | "
            f"{departamento}"
        )


def seleccionar_empleado(
    empleados: list[dict],
) -> dict | None:
    """
    Solicita el identificador del empleado hasta localizar
    una entrada válida o recibir un comando de salida.
    """
    mostrar_empleados(
        empleados
    )

    while True:
        empleado_id = input(
            "\nIntroduce el ID del empleado "
            "o escribe 'salir': "
        ).strip()

        if empleado_id.lower() in COMANDOS_SALIDA:
            return None

        empleado = buscar_empleado(
            empleados=empleados,
            empleado_id=empleado_id,
        )

        if empleado is not None:
            return empleado

        print(
            "No se ha encontrado ningún empleado "
            "con ese identificador."
        )


# ============================================================
# PRESENTACIÓN DE RESULTADOS
# ============================================================

def imprimir_errores(
    resultado: dict,
) -> None:
    """
    Muestra los errores contenidos en la envolvente estándar.
    """
    mensaje = resultado.get(
        "mensaje",
        "Se ha producido un error.",
    )

    print(
        f"\n[ERROR] {mensaje}"
    )

    errores = resultado.get(
        "data",
        {},
    ).get(
        "errores",
        [],
    )

    if not errores:
        return

    for error in errores:
        print(
            f"- {error}"
        )


def imprimir_turno_preparado(
    resultado: dict,
) -> None:
    """
    Muestra únicamente el estado general del turno preparado.

    Esta salida es temporal mientras no exista integración
    con el área LLM y Benchmark.
    """
    if resultado.get("status") != "ok":
        imprimir_errores(
            resultado
        )
        return

    turno_preparado = resultado.get(
        "data",
        {},
    ).get(
        "turno_preparado"
    )

    if not isinstance(
        turno_preparado,
        dict,
    ):
        imprimir_errores(
            {
                "mensaje": (
                    "El resultado no contiene "
                    "un turno preparado válido."
                ),
                "data": {
                    "errores": [
                        "Falta el campo "
                        "'data.turno_preparado'."
                    ],
                },
            }
        )
        return

    print(
        "\n[OK] Turno preparado."
    )

    print(
        "Pendiente de integración con "
        "el área LLM y Benchmark."
    )


def imprimir_respuesta_final(
    resultado: dict,
) -> None:
    """
    Muestra únicamente la respuesta final destinada al empleado.

    Esta función se utilizará cuando el área LLM esté integrada.
    """
    if resultado.get("status") != "ok":
        imprimir_errores(
            resultado
        )
        return

    respuesta = resultado.get(
        "data",
        {},
    ).get(
        "respuesta",
        "",
    )

    if not isinstance(respuesta, str) or not respuesta.strip():
        imprimir_errores(
            {
                "mensaje": (
                    "No se ha recibido una respuesta válida."
                ),
                "data": {
                    "errores": [
                        "Falta el campo 'data.respuesta' "
                        "o está vacío."
                    ],
                },
            }
        )
        return

    print(
        f"\nAsistente:\n{respuesta.strip()}"
    )


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
    Ejecuta el ciclo interactivo de la Arquitectura Base.

    El flujo activo prepara los turnos, pero no genera respuestas
    porque el adaptador LLM pertenece a otra área del proyecto.
    """
    estado = inicializar_estado()

    nombre = empleado.get(
        "nombre",
        "(sin nombre)",
    )

    print(
        "\n" + "=" * 60
    )

    print(
        "EMPLOYEE ONBOARDING ASSISTANT"
    )

    print(
        "=" * 60
    )

    print(
        f"Empleado activo: {nombre}"
    )

    print(
        "\nEscribe una consulta relacionada "
        "con el onboarding."
    )

    print(
        "Para terminar utiliza: salir, exit o quit."
    )

    while True:
        consulta = input(
            "\nConsulta: "
        ).strip()

        if consulta.lower() in COMANDOS_SALIDA:
            print(
                "\nSesión finalizada."
            )
            break

        resultado = preparar_turno(
            estado=estado,
            consulta=consulta,
            empleado=empleado,
            empresa=empresa,
            documentos=documentos,
            faqs=faqs,
            configuracion=ASSISTANT_CONFIG_DEFAULT,
        )

        imprimir_turno_preparado(
            resultado
        )

        # ====================================================
        # INTEGRACIÓN PENDIENTE: ROBUSTEZ
        # ====================================================
        #
        # El área de Robustez podrá intervenir antes de llamar
        # a preparar_turno(), validando la entrada del usuario,
        # o después de preparar el turno y antes de enviarlo al
        # adaptador LLM.
        #
        # No deben crearse flujos paralelos ni archivos como:
        #
        # - main_seguro.py
        # - main_vulnerable.py
        #
        # Las variantes deberán reutilizar esta sesión y los
        # contratos definidos por logic.py.

        # ====================================================
        # INTEGRACIÓN PENDIENTE: LLM Y BENCHMARK
        # ====================================================
        #
        # Flujo futuro previsto:
        #
        # if resultado["status"] == "ok":
        #     turno_preparado = resultado[
        #         "data"
        #     ]["turno_preparado"]
        #
        #     resultado_externo = adaptador_llm(
        #         turno_preparado
        #     )
        #
        #     resultado_final = finalizar_turno(
        #         estado=estado,
        #         turno_preparado=turno_preparado,
        #         resultado_externo=resultado_externo,
        #     )
        #
        #     imprimir_respuesta_final(
        #         resultado_final
        #     )
        #
        # El área LLM y Benchmark deberá implementar:
        #
        # - Construcción del prompt.
        # - Selección del proveedor y modelo.
        # - Temperatura.
        # - Generación estructurada.
        # - Control de tokens.
        # - Métricas.
        # - Benchmarking.
        #
        # La salida final de consola deberá limitarse a:
        #
        # Asistente:
        # <respuesta>
        #
        # Los perfiles, categorías, documentos, FAQ, historial
        # y métricas no deben mostrarse al usuario final.
        #
        # Mientras esa integración no exista, el estado no se
        # actualiza porque preparar_turno() no representa todavía
        # una interacción finalizada.


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

def main() -> None:
    """
    Punto de entrada de la aplicación.
    """
    try:
        datos = cargar_datos()

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        print(
            "\nNo se ha podido iniciar la aplicación."
        )

        print(
            f"- {error}"
        )

        return

    empleado = seleccionar_empleado(
        datos["empleados"]
    )

    if empleado is None:
        print(
            "\nAplicación finalizada."
        )
        return

    ejecutar_sesion(
        empleado=empleado,
        empresa=datos["empresa"],
        documentos=datos["documentos"],
        faqs=datos["faqs"],
    )


if __name__ == "__main__":
    main()
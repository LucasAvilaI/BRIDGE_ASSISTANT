"""
Menú principal de demostraciones del asistente de onboarding.
"""

from __future__ import annotations

from typing import Any, Callable

from demos.demo1_chat_onboarding import ejecutar_demo_chat_onboarding
from demos.demo2_checklist_dia_1 import ejecutar_demo_checklist_dia_1
from demos.demo3_comparativa_perfiles import ejecutar_demo_comparativa_perfiles
from demos.demo4_comparativa_dias_onboarding import (
    ejecutar_demo_comparativa_dias_onboarding,
)
from demos.demo5_vulnerable_vs_seguro import (
    ejecutar_demo_vulnerable_vs_seguro,
)
from demos.demo6_casos_trampa import ejecutar_demo_casos_trampa

# Adaptar estos imports a cargador de datos real.
from data_loader import (
    cargar_documentos,
    cargar_empleado_demo,
    cargar_empresa,
    cargar_faqs,
)


AccionMenu = Callable[[], Any]


def limpiar_pantalla() -> None:
    """
    Añade separación visual sin depender del sistema operativo.
    """

    print("\n" * 2)


def pausar() -> None:
    """
    Espera antes de volver al menú.
    """

    input("\nPulsa Enter para volver al menú principal...")


def mostrar_menu() -> None:
    """
    Imprime las opciones disponibles.
    """

    print("\n" + "=" * 56)
    print("ASISTENTE DE ONBOARDING · DEMOSTRACIONES")
    print("=" * 56)
    print("1. Chat de onboarding")
    print("2. Checklist del día 1")
    print("3. Comparativa de perfiles")
    print("4. Comparativa de días de onboarding")
    print("5. Comparación de robustez")
    print("6. Casos trampa")
    print("7. Benchmark de modelos")
    print("0. Salir")
    print("=" * 56)


def ejecutar_demo_5() -> None:
    """
    Carga el escenario y ejecuta las rutas segura y vulnerable aislada.
    """

    empleado = cargar_empleado_demo()
    empresa = cargar_empresa()
    documentos = cargar_documentos()
    faqs = cargar_faqs()

    ejecutar_demo_vulnerable_vs_seguro(
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
    )


def ejecutar_benchmark() -> None:
    """
    Import local para que el benchmark no se cargue al arrancar el menú.
    """

    from benchmark import ejecutar_benchmark_modelos

    ejecutar_benchmark_modelos()


def obtener_acciones_menu() -> dict[str, AccionMenu]:
    """
    Relaciona cada opción con una acción concreta.

    No existe ninguna acción para activar o desactivar seguridad.
    """

    return {
        "1": ejecutar_demo_chat_onboarding,
        "2": ejecutar_demo_checklist_dia_1,
        "3": ejecutar_demo_comparativa_perfiles,
        "4": ejecutar_demo_comparativa_dias_onboarding,
        "5": ejecutar_demo_5,
        "6": ejecutar_demo_casos_trampa,
        "7": ejecutar_benchmark,
    }


def ejecutar_menu() -> None:
    """
    Ejecuta el bucle principal del menú.
    """

    acciones = obtener_acciones_menu()

    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción: ").strip()

        if opcion == "0":
            print("\nPrograma finalizado.")
            return

        accion = acciones.get(opcion)

        if accion is None:
            print("\nOpción no válida.")
            pausar()
            limpiar_pantalla()
            continue

        limpiar_pantalla()

        try:
            accion()
        except KeyboardInterrupt:
            print("\n\nEjecución interrumpida por el usuario.")
        except Exception as error:
            # Evita que una demo cierre todo el programa.
            print("\nNo se pudo completar la demostración.")
            print(f"Detalle técnico: {error}")

        pausar()
        limpiar_pantalla()


if __name__ == "__main__":
    ejecutar_menu()
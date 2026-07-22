"""
Menú principal de demostraciones del asistente de onboarding.
"""
from __future__ import annotations
from typing import Any, Callable

# Importaciones de las demostraciones del proyecto
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

# Importaciones reales de tu infraestructura de datos y contexto

from config import EMPLEADOS_PATH, EMPRESA_PATH, DOCS_PATH, FAQ_PATH
from context import cargar_json, buscar_empleado

AccionMenu = Callable[[], Any]

# REGISTRO GLOBAL DE DEMOSTRACIONES (Patrón Decorador)
_DEMOS_REGISTRADAS: dict[str, tuple[str, AccionMenu]] = {}


def registrar_demo(opcion: str, descripcion: str) -> Callable[[AccionMenu], AccionMenu]:
    """Decorador para indexar automáticamente las funciones en el menú."""
    def decorador(func: AccionMenu) -> AccionMenu:
        _DEMOS_REGISTRADAS[opcion] = (descripcion, func)
        return func
    return decorador


# ============================================================
# FUNCIONES AUXILIARES DE INTERFAZ
# ============================================================

def limpiar_pantalla() -> None:
    """Añade separación visual limpia para la consola."""
    print("\n" * 3)


def pausar() -> None:
    """Espera la confirmación del usuario antes de retornar."""
    print("\n" + "─" * 56)
    input("👉 Pulsa [Enter] para regresar al menú principal...")


def mostrar_menu() -> None:
    """Imprime las opciones formateadas con bloques visuales scannables."""
    print("\n┌" + "═" * 54 + "┐")
    print("│      🤖  EMPLOYEE ONBOARDING ASSISTANT  🤖       │")
    print("│             Sprints 05–07 · Demos                │")
    print("├" + "─" * 54 + "┤")

    # Renderizado dinámico de las opciones decoradas
    for opcion, (descripcion, _) in sorted(_DEMOS_REGISTRADAS.items()):
        print(f"│  {opcion}. {descripcion:<48} │")

    print("├" + "─" * 54 + "┤")
    print("│  0. Salir de la aplicación                          │")
    print("└" + "═" * 54 + "┘")


# ============================================================
# WRAPPERS Y FUNCIONES DE ASIGNACIÓN (DECORADAS)
# ============================================================

@registrar_demo("1", "⚙️  Chat de onboarding funcional")
def demo_1():
    ejecutar_demo_chat_onboarding()


@registrar_demo("2", "⚙️  Generar checklist estructurado (Día 1)")
def demo_2():
    ejecutar_demo_checklist_dia_1()


@registrar_demo("3", "⚙️  Comparativa de perfiles del asistente")
def demo_3():
    ejecutar_demo_comparativa_perfiles()


@registrar_demo("4", "⚙️  Comparativa dinámica de días de onboarding")
def demo_4():
    ejecutar_demo_comparativa_dias_onboarding()


@registrar_demo("5", "🛡️  Comparación de robustez (Seguro vs Vulnerable)")
def ejecutar_demo_5() -> None:
    """Carga el escenario real usando context.py y llama a la demo."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)

    todos_los_empleados = cargar_json(EMPLEADOS_PATH)
    # Selecciona al dev junior por defecto de las demos (emp_01)
    empleado = buscar_empleado(todos_los_empleados, "emp_01")

    if empleado is None:
        empleado = todos_los_empleados[0] if todos_los_empleados else {}

    # Llamada exacta a la firma compartida en GitHub
    ejecutar_demo_vulnerable_vs_seguro(
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
    )


@registrar_demo("6", "🛡️  Inyección de prompts y Casos Trampa")
def demo_6():
    ejecutar_demo_casos_trampa()


@registrar_demo("7", "📊  Benchmark de rendimiento de modelos")
def demo_7() -> None:
    """Import local diferido para evitar sobrecargar el inicio del script."""
    from benchmark import ejecutar_benchmark
    ejecutar_benchmark()


# ============================================================
# FLUJO DE CONTROL PRINCIPAL
# ============================================================

def ejecutar_menu() -> None:
    """Ejecuta el bucle de control interactivo del menú."""
    while True:
        mostrar_menu()
        opcion = input("\n📥 Selecciona una opción (0-7): ").strip()

        if opcion == "0":
            print(
                "\n[OK] Saliendo del programa de demostraciones de forma segura. ¡Buen día!\n")
            return

        registro = _DEMOS_REGISTRADAS.get(opcion)

        if registro is None:
            print(
                "\n❌ [ERROR] Opción no válida. Por favor, introduce un número del listado.")
            pausar()
            limpiar_pantalla()
            continue

        descripcion_demo, funcion_demo = registro
        limpiar_pantalla()

        print(f"🚀 Ejecutando: {descripcion_demo}\n" + "─" * 56 + "\n")

        try:
            funcion_demo()
        except KeyboardInterrupt:
            print("\n\n⚠️ Ejecución cancelada de golpe por el usuario.")
        except Exception as error:
            print("\n💥 El subsistema no pudo completar la demostración.")
            print(f"Detalle técnico del error: {error}")

        pausar()
        limpiar_pantalla()


if __name__ == "__main__":
    ejecutar_menu()

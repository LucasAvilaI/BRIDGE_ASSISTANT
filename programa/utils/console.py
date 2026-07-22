# utils/console.py
import json
from typing import Any

def log_test_header(test_id, model_key):
    print(f"\n{'='*60}")
    print(f"🧪 EVALUANDO: {test_id} | MODELO: {model_key}")
    print(f"{'-'*60}")

def log_result(status, extra_info=""):
    color = "✅" if status == "PASS" else "❌"
    print(f"{color} RESULTADO: {status} | {extra_info}")

# SALIDAS PARA LAS DEMOS
def mostrar_respuesta_demo(
    *,
    respuesta: str,
    json_respuesta: dict,
    llamo_modelo: bool,
    metricas: Any | None = None,
) -> None:
    """
    Muestra de forma homogénea el resultado de una demo.

    - Indica si se llamó al LLM.
    - Muestra una representación legible de la respuesta.
    - Muestra siempre el JSON asociado a la respuesta.
    - Muestra métricas únicamente cuando hubo llamada al modelo.
    """

    print("LLM invocado:", "SÍ" if llamo_modelo else "NO")

    print("\nRespuesta:")

    print(respuesta if respuesta else "(sin respuesta)")

    print("\nJSON de la respuesta:")

    print(
        json.dumps(
            json_respuesta,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    print("\nMétricas LLM:")

    print(
        json.dumps(
            metricas,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
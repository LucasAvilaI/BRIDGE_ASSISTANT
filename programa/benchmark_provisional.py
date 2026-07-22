"""
Benchmark real de modelos Gemini para el Employee Onboarding Assistant.

Este script:
- ejecuta los mismos 10 casos con exactamente los dos modelos configurados;
- usa el cliente real de gemini_client.py, sin fallback;
- registra latencia y usage_metadata reales;
- continúa aunque falle un caso;
- exporta CSV y JSON a output/;
- genera un resumen agregado por modelo;
- calcula la proyección de tráfico x2;
- deja columnas de la rúbrica 1-3 para evaluación manual.

Ubicación recomendada:
    programa/benchmark.py

Ejecución recomendada desde la raíz del proyecto:
    python -m programa.benchmark

Si vuestro proyecto usa imports absolutos sin paquete:
    python programa/benchmark.py
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from programa.config import MAX_OUTPUT_TOKENS, TEMPERATURE_DEFAULT
from programa.gemini_client import GeminiClientError, ejecutar_caso_benchmark
from programa.metrics import (
    calcular_costo,
    proyectar_trafico,
    resumir_resultados_benchmark,
)
from programa.model_utils import listar_modelos_benchmark, validar_modelos_benchmark


# ============================================================
# RUTAS
# ============================================================

_THIS_DIR = Path(__file__).resolve().parent

# Soporta tanto:
#   proyecto/programa/benchmark.py
# como:
#   proyecto/benchmark.py
BASE_DIR = _THIS_DIR.parent if _THIS_DIR.name == "programa" else _THIS_DIR

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# bloque provisional --> borrar al terminar DEBUG
print(
    "[DEBUG] benchmark.py ejecutado desde:",
    Path(__file__).resolve(),
)

print(
    "[DEBUG] archivos guardados en:",
    OUTPUT_DIR.resolve(),
)
# fin del bloque provisional --> borrar completo

PREGUNTAS_BENCHMARK_PATH = DATA_DIR / "preguntas_benchmark.json"

RESULTADOS_JSON_PATH = OUTPUT_DIR / "resultados_benchmark.json"
RESULTADOS_CSV_PATH = OUTPUT_DIR / "resultados_benchmark.csv"
RESUMEN_JSON_PATH = OUTPUT_DIR / "resumen_benchmark.json"
PROYECCION_JSON_PATH = OUTPUT_DIR / "proyeccion_trafico_x2.json"


# ============================================================
# CONFIGURACIÓN DEL BENCHMARK
# ============================================================

BENCHMARK_TEMPERATURE = TEMPERATURE_DEFAULT
BENCHMARK_MAX_OUTPUT_TOKENS = MAX_OUTPUT_TOKENS

# None hace que gemini_client.py aplique la política centralizada del proyecto.
# Así no duplicamos aquí reglas específicas de thinking por modelo.
# BENCHMARK_THINKING_BUDGET: int | None = None

# Nivel de razonamiento común para los dos modelos.
#
# Se utiliza el mismo valor en todo el benchmark para mantener
# condiciones comparables entre Gemini 3.5 Flash y
# Gemini 3.1 Flash-Lite.
BENCHMARK_THINKING_LEVEL: str | None = "low"

CAMPOS_EVALUACION_MANUAL = (
    "fidelidad_1_3",
    "relevancia_1_3",
    "tono_1_3",
    "seguridad_1_3",
)


# ============================================================
# CARGA Y VALIDACIÓN DEL DATASET
# ============================================================

def cargar_casos() -> list[dict[str, Any]]:
    """Carga y valida la batería final de preguntas."""

    if not PREGUNTAS_BENCHMARK_PATH.exists():
        raise FileNotFoundError(
            f"No existe el dataset de benchmark: {PREGUNTAS_BENCHMARK_PATH}"
        )

    with PREGUNTAS_BENCHMARK_PATH.open("r", encoding="utf-8") as archivo:
        casos = json.load(archivo)

    if not isinstance(casos, list):
        raise ValueError(
            "preguntas_benchmark.json debe contener una lista de casos."
        )

    if len(casos) < 10:
        raise ValueError(
            "El benchmark final debe contener al menos 10 casos."
        )

    ids_vistos: set[str] = set()

    for posicion, caso in enumerate(casos, start=1):
        if not isinstance(caso, dict):
            raise ValueError(
                f"El caso {posicion} debe ser un objeto JSON."
            )

        case_id = caso.get("id")
        prompt = caso.get("prompt")

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(
                f"El caso {posicion} no tiene un id válido."
            )

        if case_id in ids_vistos:
            raise ValueError(
                f"ID de benchmark duplicado: {case_id}"
            )

        ids_vistos.add(case_id)

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(
                f"El caso {case_id} no contiene un prompt válido."
            )

    return casos


# ============================================================
# VALIDACIÓN AUTOMÁTICA MÍNIMA DE FORMATO
# ============================================================

def _validar_checklist_json(texto: str) -> bool:
    """Comprueba el contrato mínimo del caso de checklist."""

    try:
        resultado = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return False

    if not isinstance(resultado, dict):
        return False

    campos = {
        "empleado_id",
        "dia",
        "tareas",
        "mensaje_resumen",
    }

    if set(resultado) != campos:
        return False

    if not isinstance(resultado["empleado_id"], str):
        return False

    if (
        not isinstance(resultado["dia"], int)
        or isinstance(resultado["dia"], bool)
    ):
        return False

    tareas = resultado["tareas"]

    if not isinstance(tareas, list) or not tareas:
        return False

    campos_tarea = {
        "id",
        "titulo",
        "completada",
        "fuente_doc",
    }

    for tarea in tareas:
        if not isinstance(tarea, dict):
            return False

        if set(tarea) != campos_tarea:
            return False

        if not isinstance(tarea["id"], str):
            return False

        if not isinstance(tarea["titulo"], str):
            return False

        if tarea["completada"] is not False:
            return False

        if not isinstance(tarea["fuente_doc"], str):
            return False

    return isinstance(resultado["mensaje_resumen"], str)


def comprobar_formato_respuesta(
    *,
    case_id: str,
    respuesta: str,
) -> bool:
    """Valida automáticamente solo lo que puede comprobarse sin juzgar calidad."""

    if not isinstance(respuesta, str) or not respuesta.strip():
        return False

    if "checklist" in case_id.lower():
        return _validar_checklist_json(respuesta)

    return True


# ============================================================
# EJECUCIÓN DE UN CASO
# ============================================================

def ejecutar_caso(
    *,
    run_id: str,
    caso: dict[str, Any],
    model_id: str,
) -> dict[str, Any]:
    """Ejecuta un caso real y devuelve una fila normalizada."""

    case_id = caso["id"]
    prompt = caso["prompt"]

    timestamp = datetime.now(timezone.utc).isoformat()

    fila: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": timestamp,
        "case_id": case_id,
        "model_key": model_id,
        "model_id": model_id,
        "temperature": BENCHMARK_TEMPERATURE,
        "thinking_level": BENCHMARK_THINKING_LEVEL,
        "llamada_modelo": True,
        "status": "error",
        "error": "",
        "latencia_total_ms": None,
        "latencia_modelo_ms": None,
        "tokens_input": None,
        "tokens_output": None,
        "thinking_tokens": None,
        "tokens_total": None,
        "coste_estimado_usd": None,
        "respuesta": "",
        "cumple_schema": False,
        "fidelidad_1_3": "",
        "relevancia_1_3": "",
        "tono_1_3": "",
        "seguridad_1_3": "",
    }

    inicio_total = perf_counter()

    try:
        respuesta, metricas = ejecutar_caso_benchmark(
            prompt,
            model_id=model_id,
            temperature=BENCHMARK_TEMPERATURE,
            max_output_tokens=BENCHMARK_MAX_OUTPUT_TOKENS,
            thinking_level=BENCHMARK_THINKING_LEVEL,
        )

        fila["latencia_total_ms"] = round(
            (perf_counter() - inicio_total) * 1000
        )
        fila["latencia_modelo_ms"] = metricas.elapsed_ms
        fila["tokens_input"] = metricas.prompt_tokens
        fila["tokens_output"] = metricas.output_tokens
        fila["thinking_tokens"] = metricas.thinking_tokens
        fila["tokens_total"] = metricas.total_tokens
        fila["respuesta"] = respuesta
        fila["cumple_schema"] = comprobar_formato_respuesta(
            case_id=case_id,
            respuesta=respuesta,
        )
        fila["coste_estimado_usd"] = calcular_costo(
            model_key=model_id,
            tokens_input=metricas.prompt_tokens,
            tokens_output=metricas.output_tokens,
            thinking_tokens=metricas.thinking_tokens,
        )
        fila["status"] = "ok"

    except (GeminiClientError, ValueError, TypeError, KeyError) as error:
        fila["latencia_total_ms"] = round(
            (perf_counter() - inicio_total) * 1000
        )
        fila["error"] = f"{type(error).__name__}: {error}"

    return fila


# ============================================================
# EXPORTACIÓN
# ============================================================

def guardar_json(
    ruta: Path,
    contenido: Any,
) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)

    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(
            contenido,
            archivo,
            indent=2,
            ensure_ascii=False,
        )


def guardar_csv(
    ruta: Path,
    filas: list[dict[str, Any]],
) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)

    if not filas:
        raise ValueError(
            "No hay filas de benchmark para exportar."
        )

    campos = list(filas[0].keys())

    with ruta.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=campos,
        )
        writer.writeheader()
        writer.writerows(filas)


# ============================================================
# BENCHMARK COMPLETO
# ============================================================

def ejecutar_benchmark() -> dict[str, Any]:
    """
    Ejecuta los 10+ casos contra exactamente dos modelos.

    Una excepción de un caso no aborta el benchmark completo:
    se registra en la fila correspondiente y se continúa.
    """

    validar_modelos_benchmark()

    modelos = listar_modelos_benchmark()

    if len(modelos) != 2:
        raise ValueError(
            "El benchmark debe ejecutar exactamente dos modelos activos."
        )

    casos = cargar_casos()

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid4().hex[:8]
    )

    resultados: list[dict[str, Any]] = []

    print(
        f"\n[benchmark] run_id={run_id} "
        f"casos={len(casos)} modelos={len(modelos)}"
    )

    for caso in casos:
        for model_id in modelos:
            print(
                f"[benchmark] caso={caso['id']} "
                f"modelo={model_id}"
            )

            fila = ejecutar_caso(
                run_id=run_id,
                caso=caso,
                model_id=model_id,
            )

            resultados.append(fila)

            if fila["status"] == "ok":
                print(
                    "  [OK] "
                    f"{fila['latencia_modelo_ms']} ms | "
                    f"in={fila['tokens_input']} "
                    f"out={fila['tokens_output']} "
                    f"think={fila['thinking_tokens']}"
                )
            else:
                print(
                    f"  [ERROR] {fila['error']}"
                )

    guardar_json(
        RESULTADOS_JSON_PATH,
        resultados,
    )

    guardar_csv(
        RESULTADOS_CSV_PATH,
        resultados,
    )

    # bloque provisional --> borrar después de DEBUG
    print("\n[DEBUG] Calculando resumen agregado...")

    try:
        resumen = resumir_resultados_benchmark(
            resultados
        )
    except Exception as error:
        print(
            "[ERROR] No se ha podido calcular "
            "resumen_benchmark.json."
        )
        print(f"Tipo: {type(error).__name__}")
        print(f"Detalle: {error}")
        raise
    # fin del bloque provisional --> borrar completo

    # resumen = resumir_resultados_benchmark(
    #     resultados
    # )

    guardar_json(
        RESUMEN_JSON_PATH,
        resumen,
    )

    # bloque provisional --> borrar después de DEBUG
    print("\n[DEBUG] Calculando proyección de tráfico...")

    try:
        proyecciones = {
            model_id: proyectar_trafico(
                resumen_modelo,
                factor=2,
            )
            for model_id, resumen_modelo
            in resumen.items()
        }
    except Exception as error:
        print(
            "[ERROR] No se ha podido calcular "
            "proyeccion_trafico_x2.json."
        )
        print(f"Tipo: {type(error).__name__}")
        print(f"Detalle: {error}")
        raise
    # fin bloque provisional --> borrar completo

    # proyecciones = {
    #     model_id: proyectar_trafico(
    #         resumen_modelo,
    #         factor=2,
    #     )
    #     for model_id, resumen_modelo
    #     in resumen.items()
    # }

    guardar_json(
        PROYECCION_JSON_PATH,
        proyecciones,
    )

    print("\n[benchmark] Archivos generados:")
    print(f"- {RESULTADOS_JSON_PATH}")
    print(f"- {RESULTADOS_CSV_PATH}")
    print(f"- {RESUMEN_JSON_PATH}")
    print(f"- {PROYECCION_JSON_PATH}")
    print(
        "\n[benchmark] Falta únicamente puntuar manualmente "
        "fidelidad, relevancia, tono y seguridad (1-3) en el CSV "
        "antes de generar la decisión final."
    )

    return {
        "run_id": run_id,
        "resultados": resultados,
        "resumen": resumen,
        "proyecciones": proyecciones,
    }


if __name__ == "__main__":
    ejecutar_benchmark()
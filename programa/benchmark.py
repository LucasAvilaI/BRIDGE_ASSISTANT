"""Benchmark funcional y reproducible para comparar los modelos Gemini."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import (
    BENCHMARK_MAX_CASES,
    BENCHMARK_MAX_OUTPUT_TOKENS,
    BENCHMARK_MIN_CASES,
    BENCHMARK_TEMPERATURE,
    BENCHMARK_THINKING_BUDGET,
    PREGUNTAS_BENCHMARK_PATH,
    RESULTADOS_BENCHMARK_PATH,
)
from gemini_auth import configurar_gemini_api_key, GeminiAuthError
from gemini_client import (
    GeminiClientError,
    ejecutar_caso_benchmark,
    parsear_json,
)
from model_utils import (
    listar_modelos_benchmark,
    obtener_modelo,
    validar_modelos_benchmark,
)
from metrics import calcular_costo, resumir_resultados_benchmark
from prompts import build_secure_system_instruction
from validators import validar_respuesta_estructurada


CSV_RESULTADOS_PATH = RESULTADOS_BENCHMARK_PATH.with_suffix(".csv")


def cargar_casos(
    ruta: Path = PREGUNTAS_BENCHMARK_PATH,
) -> list[dict[str, Any]]:
    """Carga y valida el dataset oficial del benchmark."""
    with ruta.open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if isinstance(contenido, dict):
        contenido = contenido.get("preguntas", [])

    if not isinstance(contenido, list):
        raise ValueError("El dataset debe contener una lista de casos.")

    casos: list[dict[str, Any]] = []
    ids: set[str] = set()

    for posicion, caso in enumerate(contenido, start=1):
        if not isinstance(caso, dict):
            raise ValueError(f"El caso {posicion} debe ser un objeto JSON.")

        case_id_raw = caso.get("id")
        prompt_raw = caso.get("prompt") or caso.get("consulta")
        case_id = str(case_id_raw).strip() if case_id_raw is not None else ""

        if not case_id:
            raise ValueError(f"El caso {posicion} no contiene un id válido.")
        if case_id in ids:
            raise ValueError(f"ID de caso duplicado: {case_id}")
        if not isinstance(prompt_raw, str) or not prompt_raw.strip():
            raise ValueError(f"El caso '{case_id}' no contiene prompt o consulta.")

        ids.add(case_id)
        casos.append({**caso, "id": case_id, "prompt": prompt_raw.strip()})

    if len(casos) < BENCHMARK_MIN_CASES:
        raise ValueError(
            f"El benchmark debe contener al menos {BENCHMARK_MIN_CASES} casos."
        )
    if len(casos) > BENCHMARK_MAX_CASES:
        raise ValueError(
            f"El benchmark no puede superar {BENCHMARK_MAX_CASES} casos."
        )

    return casos


# calcular_costo() se importa desde metrics.py para evitar mantener
# la misma fórmula duplicada en el chat y en el benchmark.


def crear_resultado_base(
    *,
    run_id: str,
    timestamp: str,
    caso: dict[str, Any],
    model_key: str,
    model_id: str,
) -> dict[str, Any]:
    """Crea una fila homogénea antes de ejecutar el modelo."""
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "case_id": caso["id"],
        "model_key": model_key,
        "model_id": model_id,
        "temperature": BENCHMARK_TEMPERATURE,
        "thinking_budget": BENCHMARK_THINKING_BUDGET,
        # CORRECCIÓN DE ROBUSTEZ: Forzamos 'seguro' por diseño del producto
        # independientemente de lo que venga escrito en la semilla JSON.
        "modo": "seguro",
        "tipo": caso.get("tipo", "chat"),
        "categoria_esperada": caso.get("categoria_esperada"),
        "empleado_id": caso.get("empleado_id"),
        "dia_onboarding": caso.get("dia_onboarding"),
        "status": "pending",
        "error": None,
        "latencia_total_ms": None,
        "latencia_modelo_ms": None,
        "tokens_input": None,
        "tokens_output": None,
        "thinking_tokens": None,
        "tokens_total": None,
        "coste_estimado_usd": None,
        "respuesta": None,
        "document_ids": [],
        "faq_ids": [],
        "cumple_schema": False,
        "errores_schema": [],
        "fidelidad_1_3": None,
        "relevancia_1_3": None,
        "tono_1_3": None,
        "seguridad_1_3": None,
    }


def ejecutar_caso(
    *,
    caso: dict[str, Any],
    model_key: str,
    run_id: str,
    timestamp: str,
) -> dict[str, Any]:
    """Ejecuta un caso sin fallback y conserva los errores en el informe."""
    modelo = obtener_modelo(model_key)
    model_id = modelo["model_id"]
    resultado = crear_resultado_base(
        run_id=run_id,
        timestamp=timestamp,
        caso=caso,
        model_key=model_key,
        model_id=model_id,
    )

    inicio_total = datetime.now(timezone.utc)

    try:
        # Aquí se fuerza de manera inmutable el flujo de la instrucción de sistema segura
        texto, metricas = ejecutar_caso_benchmark(
            caso["prompt"],
            model_id=model_id,
            system_instruction=build_secure_system_instruction(),
            temperature=BENCHMARK_TEMPERATURE,
            json_mode=True,
            max_output_tokens=BENCHMARK_MAX_OUTPUT_TOKENS,
            thinking_budget=BENCHMARK_THINKING_BUDGET,
        )
        respuesta = parsear_json(texto)
        validacion = validar_respuesta_estructurada(respuesta)

        resultado["respuesta"] = respuesta
        resultado["document_ids"] = respuesta.get("document_ids", [])
        resultado["faq_ids"] = respuesta.get("faq_ids", [])
        resultado["cumple_schema"] = bool(validacion["valido"])
        resultado["errores_schema"] = list(validacion["errores"])
        resultado["status"] = "ok" if validacion["valido"] else "invalid_schema"

        resultado["latencia_modelo_ms"] = metricas.elapsed_ms
        resultado["tokens_input"] = metricas.prompt_tokens
        resultado["tokens_output"] = metricas.output_tokens
        resultado["thinking_tokens"] = metricas.thinking_tokens
        resultado["tokens_total"] = metricas.total_tokens
        resultado["coste_estimado_usd"] = calcular_costo(
            model_key=model_key,
            tokens_input=metricas.prompt_tokens,
            tokens_output=metricas.output_tokens,
            thinking_tokens=metricas.thinking_tokens,
        )
    except (GeminiClientError, ValueError, KeyError, TypeError) as error:
        resultado["status"] = "error"
        resultado["error"] = f"{type(error).__name__}: {error}"
    finally:
        fin_total = datetime.now(timezone.utc)
        resultado["latencia_total_ms"] = round(
            (fin_total - inicio_total).total_seconds() * 1000
        )

    return resultado


def ejecutar_benchmark() -> list[dict[str, Any]]:
    """Ejecuta todos los casos con los dos modelos y exporta los resultados."""
    
    # CORRECCIÓN DE ROBUSTEZ: Asegurar la API Key sin interactividad para procesos desasistidos
    try:
        configurar_gemini_api_key(interactivo=False)
    except GeminiAuthError as e:
        raise RuntimeError(f"No se pudo iniciar el benchmark debido a credenciales: {e}")

    validar_modelos_benchmark()
    casos = cargar_casos()
    modelos = listar_modelos_benchmark()

    run_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    resultados = [
        ejecutar_caso(
            caso=caso,
            model_key=model_key,
            run_id=run_id,
            timestamp=timestamp,
        )
        for caso in casos
        for model_key in modelos
    ]

    exportar_resultados(resultados)
    return resultados


def serializar_valor_csv(valor: Any) -> Any:
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, sort_keys=True)
    return valor


def exportar_resultados(resultados: list[dict[str, Any]]) -> None:
    """Guarda el detalle en JSON y CSV."""
    RESULTADOS_BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTADOS_BENCHMARK_PATH.open("w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, ensure_ascii=False, indent=2)

    if not resultados:
        return

    columnas = list(resultados[0])
    with CSV_RESULTADOS_PATH.open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=columnas)
        writer.writeheader()
        for resultado in resultados:
            writer.writerow(
                {
                    columna: serializar_valor_csv(resultado.get(columna))
                    for columna in columnas
                }
            )


if __name__ == "__main__":
    filas = ejecutar_benchmark()
    filas_validas = sum(fila["status"] == "ok" for fila in filas)
    print(
        f"Benchmark finalizado: {len(filas)} ejecuciones, "
        f"{filas_validas} respuestas válidas.\n"
        f"JSON: {RESULTADOS_BENCHMARK_PATH}\n"
        f"CSV: {CSV_RESULTADOS_PATH}"
    )

    resumen_por_modelo = resumir_resultados_benchmark(filas)

    print("\nResumen por modelo:")
    for model_key, resumen in resumen_por_modelo.items():
        print(
            f"- {model_key}: "
            f"éxito_schema={resumen['tasa_exito_schema']} "
            f"latencia_modelo_media_ms={resumen['latencia_modelo_ms']['media']} "
            f"coste_total_usd={resumen['coste_total_usd']} "
            f"ratio_thinking_medio={resumen['ratio_thinking_medio']}"
        )
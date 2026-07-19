"""Benchmark funcional para comparar los modelos Gemini del proyecto."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import PREGUNTAS_BENCHMARK_PATH, RESULTADOS_BENCHMARK_PATH
from gemini_client import generar_respuesta_estructurada
from model_registry import BENCHMARK_MAX_OUTPUT_TOKENS, BENCHMARK_TEMPERATURE
from model_utils import (
    listar_modelos_benchmark,
    obtener_modelo,
    validar_modelos_benchmark,
)
from prompts import build_secure_system_instruction


CSV_RESULTADOS_PATH = RESULTADOS_BENCHMARK_PATH.with_suffix(".csv")


def validar_respuesta_benchmark(respuesta: Any) -> dict[str, Any]:
    """Comprueba el contrato mínimo de la respuesta de chat."""
    campos_esperados = {
        "in_scope",
        "category",
        "answer",
        "document_ids",
        "faq_ids",
        "needs_escalation",
        "escalation_department",
    }
    errores: list[str] = []

    if not isinstance(respuesta, dict):
        return {
            "valido": False,
            "errores": ["La respuesta debe ser un diccionario."],
        }

    campos_recibidos = set(respuesta)
    faltantes = campos_esperados - campos_recibidos
    sobrantes = campos_recibidos - campos_esperados

    if faltantes:
        errores.append("Faltan campos: " + ", ".join(sorted(faltantes)))
    if sobrantes:
        errores.append("Sobran campos: " + ", ".join(sorted(sobrantes)))

    if "in_scope" in respuesta and not isinstance(respuesta["in_scope"], bool):
        errores.append("'in_scope' debe ser booleano.")
    if "category" in respuesta and not isinstance(respuesta["category"], str):
        errores.append("'category' debe ser una cadena.")
    if "answer" in respuesta and not isinstance(respuesta["answer"], str):
        errores.append("'answer' debe ser una cadena.")
    if "document_ids" in respuesta and not isinstance(respuesta["document_ids"], list):
        errores.append("'document_ids' debe ser una lista.")
    if "faq_ids" in respuesta and not isinstance(respuesta["faq_ids"], list):
        errores.append("'faq_ids' debe ser una lista.")
    if "needs_escalation" in respuesta and not isinstance(
        respuesta["needs_escalation"], bool
    ):
        errores.append("'needs_escalation' debe ser booleano.")

    departamento = respuesta.get("escalation_department")
    if departamento is not None and not isinstance(departamento, str):
        errores.append("'escalation_department' debe ser una cadena o None.")

    if respuesta.get("needs_escalation") is True and not departamento:
        errores.append(
            "Si 'needs_escalation' es True, debe indicarse "
            "'escalation_department'."
        )

    return {"valido": not errores, "errores": errores}


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

        case_id = caso.get("id")
        prompt = caso.get("prompt") or caso.get("consulta")

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"El caso {posicion} no contiene un id válido.")
        if case_id in ids:
            raise ValueError(f"ID de caso duplicado: {case_id}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"El caso '{case_id}' no contiene prompt o consulta.")

        ids.add(case_id)
        casos.append({**caso, "id": case_id.strip(), "prompt": prompt.strip()})

    if len(casos) < 10:
        raise ValueError("El benchmark oficial debe contener al menos 10 casos.")

    return casos


def calcular_costo(
    *,
    model_key: str,
    tokens_input: int | None,
    tokens_output: int | None,
) -> float | None:
    """Calcula el coste estimado con los precios registrados para el modelo."""
    if tokens_input is None or tokens_output is None:
        return None

    modelo = obtener_modelo(model_key)

    try:
        coste_entrada = float(modelo["cost_input_per_m"])
        coste_salida = float(modelo["cost_output_per_m"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Costes inválidos para el modelo '{model_key}'.") from error

    return round(
        (tokens_input / 1_000_000) * coste_entrada
        + (tokens_output / 1_000_000) * coste_salida,
        8,
    )


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
        "modo": caso.get("modo", "seguro"),
        "tipo": caso.get("tipo", "chat"),
        "empleado_id": caso.get("empleado_id"),
        "dia_onboarding": caso.get("dia_onboarding"),
        "llamada_modelo": True,
        "status": "pending",
        "error": None,
        "latencia_total_ms": None,
        "latencia_modelo_ms": None,
        "tokens_input": None,
        "tokens_output": None,
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
    """Ejecuta un caso y conserva cualquier error sin detener el benchmark."""
    modelo = obtener_modelo(model_key)
    model_id = str(modelo["model_id"])
    resultado = crear_resultado_base(
        run_id=run_id,
        timestamp=timestamp,
        caso=caso,
        model_key=model_key,
        model_id=model_id,
    )

    inicio_total = datetime.now(timezone.utc)

    try:
        respuesta, metricas = generar_respuesta_estructurada(
            model_id=model_id,
            system_instruction=build_secure_system_instruction(),
            contents=caso["prompt"],
            temperature=BENCHMARK_TEMPERATURE,
            max_output_tokens=BENCHMARK_MAX_OUTPUT_TOKENS,
        )

        validacion = validar_respuesta_benchmark(respuesta)

        resultado["respuesta"] = respuesta
        resultado["document_ids"] = respuesta.get("document_ids", [])
        resultado["faq_ids"] = respuesta.get("faq_ids", [])
        resultado["cumple_schema"] = bool(validacion["valido"])
        resultado["errores_schema"] = list(validacion["errores"])
        resultado["status"] = "ok" if validacion["valido"] else "invalid_schema"

        resultado["latencia_modelo_ms"] = metricas.get("latencia_modelo_ms")
        resultado["tokens_input"] = metricas.get("tokens_input")
        resultado["tokens_output"] = metricas.get("tokens_output")
        resultado["tokens_total"] = metricas.get("tokens_total")
        resultado["coste_estimado_usd"] = calcular_costo(
            model_key=model_key,
            tokens_input=resultado["tokens_input"],
            tokens_output=resultado["tokens_output"],
        )
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        resultado["status"] = "error"
        resultado["error"] = f"{type(error).__name__}: {error}"
    finally:
        fin_total = datetime.now(timezone.utc)
        resultado["latencia_total_ms"] = round(
            (fin_total - inicio_total).total_seconds() * 1000
        )

    return resultado


def ejecutar_benchmark() -> list[dict[str, Any]]:
    """Ejecuta todos los casos con los dos modelos activos y exporta resultados."""
    validar_modelos_benchmark()
    casos = cargar_casos()
    modelos = listar_modelos_benchmark()

    run_id = uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    resultados: list[dict[str, Any]] = []

    for caso in casos:
        for model_key in modelos:
            resultados.append(
                ejecutar_caso(
                    caso=caso,
                    model_key=model_key,
                    run_id=run_id,
                    timestamp=timestamp,
                )
            )

    exportar_resultados(resultados)
    return resultados


def serializar_valor_csv(valor: Any) -> Any:
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, sort_keys=True)
    return valor


def exportar_resultados(resultados: list[dict[str, Any]]) -> None:
    """Guarda el detalle en JSON y una tabla equivalente en CSV."""
    RESULTADOS_BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RESULTADOS_BENCHMARK_PATH.open("w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, ensure_ascii=False, indent=2)

    if not resultados:
        return

    columnas = list(resultados[0].keys())
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

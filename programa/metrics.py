"""
Métricas del asistente (Área: LLM y Benchmark).

Fórmulas y utilidades para extraer indicadores de valor a partir de
las llamadas al modelo Gemini.

Este módulo NO llama al modelo ni conoce el SDK de google-genai:
solo transforma objetos MetricasLlamada (definidos en gemini_client.py)
y listas de resultados de benchmark en indicadores derivados.

Responsabilidades:
- Calcular el coste estimado de una llamada (chat o benchmark).
- Calcular métricas de rendimiento: tokens/segundo, ratio de
  tokens de razonamiento sobre el total facturable.
- Construir un resumen legible de una única llamada (turno de chat).
- Agregar métricas sobre una serie de llamadas: medias, medianas,
  percentil 95 de latencia, tasa de éxito de esquema, coste total.
- Proyectar coste y volumen de tokens ante un incremento de tráfico
  ("¿Qué pasaría si duplicáramos el tráfico?").

Este módulo NO decide qué modelo usar (model_utils.py) ni valida
contratos JSON (validators.py). Tampoco construye prompts (prompts.py)
ni decide cuándo llamar al modelo (logic.py).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Iterable

from model_utils import obtener_modelo

try:
    # Solo se usa para anotar tipos; metrics.py no importa el SDK.
    from gemini_client import MetricasLlamada
except ImportError:  # pragma: no cover
    MetricasLlamada = Any  # type: ignore[assignment,misc]


# ============================================================
# COSTE ESTIMADO
# ============================================================

def tokens_facturables(
    tokens_output: int | None,
    thinking_tokens: int | None,
) -> int | None:
    """Devuelve la salida facturable: tokens de salida + razonamiento.

    Gemini factura los tokens de razonamiento (thinking) como tokens
    de salida. Si tokens_output es None no hay datos suficientes.
    """
    if tokens_output is None:
        return None

    return tokens_output + (thinking_tokens or 0)


def calcular_costo(
    *,
    model_key: str,
    tokens_input: int | None,
    tokens_output: int | None,
    thinking_tokens: int | None,
) -> float | None:
    """Estima el coste en USD de una llamada concreta.

    model_key debe coincidir con la clave usada en model_registry.py
    (en este proyecto es el propio model_id, p. ej. "gemini-2.5-flash").
    Devuelve None si faltan los recuentos de tokens necesarios.
    """
    if tokens_input is None or tokens_output is None:
        return None

    modelo = obtener_modelo(model_key)
    salida_facturable = tokens_facturables(tokens_output, thinking_tokens) or 0

    return round(
        (tokens_input / 1_000_000) * modelo["cost_input_per_m"]
        + (salida_facturable / 1_000_000) * modelo["cost_output_per_m"],
        8,
    )


# ============================================================
# RENDIMIENTO DE UNA LLAMADA
# ============================================================

def tokens_por_segundo(
    *,
    tokens_output: int | None,
    thinking_tokens: int | None,
    elapsed_ms: int | None,
) -> float | None:
    """Rendimiento de generación: tokens facturables por segundo.

    Es un indicador de percepción de velocidad, no de coste.
    Devuelve None si faltan datos o si elapsed_ms es 0.
    """
    salida_facturable = tokens_facturables(tokens_output, thinking_tokens)

    if salida_facturable is None or not elapsed_ms:
        return None

    return round(salida_facturable / (elapsed_ms / 1000), 2)


def ratio_thinking(
    *,
    tokens_output: int | None,
    thinking_tokens: int | None,
) -> float | None:
    """Proporción de tokens de razonamiento sobre la salida facturable.

    Un valor alto indica que gran parte del coste de salida se dedica
    a razonar en vez de a producir la respuesta final. Útil para
    comparar Gemini 2.5 Pro vs Flash en el benchmark.
    """
    salida_facturable = tokens_facturables(tokens_output, thinking_tokens)

    if not salida_facturable:
        return None

    return round((thinking_tokens or 0) / salida_facturable, 4)


def ratio_uso_contexto(
    *,
    model_key: str,
    tokens_input: int | None,
) -> float | None:
    """Proporción de la ventana de contexto consumida por la entrada.

    Sirve como señal temprana de riesgo de saturación de contexto
    si el histórico o los documentos seleccionados crecen.
    """
    if tokens_input is None:
        return None

    modelo = obtener_modelo(model_key)
    context_window = modelo.get("context_window")

    if not context_window:
        return None

    return round(tokens_input / context_window, 6)


# ============================================================
# RESUMEN DE UNA ÚNICA LLAMADA (TURNO DE CHAT)
# ============================================================

def metricas_de_turno(metricas: "MetricasLlamada") -> dict[str, Any]:
    """Construye un resumen legible de una única llamada al modelo.

    Pensado para el chat interactivo (main.py): un turno, un
    resultado. No agrega series ni requiere una lista de llamadas.
    """
    model_key = metricas.model_id

    coste = None
    rendimiento = None
    thinking_ratio = None
    uso_contexto = None

    if model_key:
        coste = calcular_costo(
            model_key=model_key,
            tokens_input=metricas.prompt_tokens,
            tokens_output=metricas.output_tokens,
            thinking_tokens=metricas.thinking_tokens,
        )
        rendimiento = tokens_por_segundo(
            tokens_output=metricas.output_tokens,
            thinking_tokens=metricas.thinking_tokens,
            elapsed_ms=metricas.elapsed_ms,
        )
        thinking_ratio = ratio_thinking(
            tokens_output=metricas.output_tokens,
            thinking_tokens=metricas.thinking_tokens,
        )
        uso_contexto = ratio_uso_contexto(
            model_key=model_key,
            tokens_input=metricas.prompt_tokens,
        )

    return {
        "model_id": model_key,
        "fallback_used": metricas.fallback_used,
        "latencia_ms": metricas.elapsed_ms,
        "tokens_input": metricas.prompt_tokens,
        "tokens_output": metricas.output_tokens,
        "thinking_tokens": metricas.thinking_tokens,
        "tokens_total": metricas.total_tokens,
        "coste_estimado_usd": coste,
        "tokens_por_segundo": rendimiento,
        "ratio_thinking": thinking_ratio,
        "ratio_uso_contexto": uso_contexto,
    }


def formatear_metricas_turno(metricas: "MetricasLlamada") -> str:
    """Línea corta y legible para mostrar tras cada turno del chat."""
    resumen = metricas_de_turno(metricas)

    coste = resumen["coste_estimado_usd"]
    coste_texto = f"${coste:.6f}" if coste is not None else "n/d"

    rendimiento = resumen["tokens_por_segundo"]
    rendimiento_texto = (
        f"{rendimiento} tok/s" if rendimiento is not None else "n/d"
    )

    return (
        f"[métricas] modelo={resumen['model_id']} "
        f"latencia={resumen['latencia_ms']} ms "
        f"tokens(in/out/think)="
        f"{resumen['tokens_input']}/{resumen['tokens_output']}/"
        f"{resumen['thinking_tokens']} "
        f"coste≈{coste_texto} "
        f"rendimiento={rendimiento_texto}"
    )


# ============================================================
# ESTADÍSTICOS SOBRE SERIES DE VALORES
# ============================================================

def _percentil(valores: list[float], percentil: float) -> float | None:
    """Percentil por interpolación lineal (método 'nearest-rank' suavizado).

    percentil debe estar entre 0 y 100. Devuelve None con lista vacía.
    """
    if not valores:
        return None

    datos = sorted(valores)

    if len(datos) == 1:
        return datos[0]

    posicion = (percentil / 100) * (len(datos) - 1)
    indice_inferior = int(posicion)
    indice_superior = min(indice_inferior + 1, len(datos) - 1)
    fraccion = posicion - indice_inferior

    return round(
        datos[indice_inferior]
        + (datos[indice_superior] - datos[indice_inferior]) * fraccion,
        2,
    )


def resumir_serie(valores: Iterable[Any]) -> dict[str, float | int | None]:
    """Media, mediana, p95, mínimo, máximo y conteo de una serie numérica.

    Ignora valores None (recuentos que el SDK no proporcionó). Si no
    queda ningún valor numérico, todos los estadísticos son None.
    """
    numericos = [
        float(valor)
        for valor in valores
        if isinstance(valor, (int, float)) and not isinstance(valor, bool)
    ]

    if not numericos:
        return {
            "n": 0,
            "media": None,
            "mediana": None,
            "p95": None,
            "minimo": None,
            "maximo": None,
        }

    return {
        "n": len(numericos),
        "media": round(statistics.fmean(numericos), 2),
        "mediana": round(statistics.median(numericos), 2),
        "p95": _percentil(numericos, 95),
        "minimo": round(min(numericos), 2),
        "maximo": round(max(numericos), 2),
    }


# ============================================================
# AGREGACIÓN POR MODELO (BENCHMARK)
# ============================================================

@dataclass(frozen=True)
class ResumenModelo:
    """Métricas agregadas de un modelo sobre un conjunto de casos."""

    model_key: str
    ejecuciones: int
    tasa_exito_schema: float | None
    latencia_total_ms: dict[str, float | int | None]
    latencia_modelo_ms: dict[str, float | int | None]
    tokens_input: dict[str, float | int | None]
    tokens_output: dict[str, float | int | None]
    thinking_tokens: dict[str, float | int | None]
    coste_total_usd: float | None
    coste_medio_usd: float | None
    ratio_thinking_medio: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_key": self.model_key,
            "ejecuciones": self.ejecuciones,
            "tasa_exito_schema": self.tasa_exito_schema,
            "latencia_total_ms": self.latencia_total_ms,
            "latencia_modelo_ms": self.latencia_modelo_ms,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "thinking_tokens": self.thinking_tokens,
            "coste_total_usd": self.coste_total_usd,
            "coste_medio_usd": self.coste_medio_usd,
            "ratio_thinking_medio": self.ratio_thinking_medio,
        }


def resumir_resultados_benchmark(
    resultados: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Agrupa y resume las filas de benchmark.py por model_key.

    Espera el formato de fila producido por benchmark.py
    (crear_resultado_base / ejecutar_caso): claves como
    model_key, status, latencia_total_ms, latencia_modelo_ms,
    tokens_input, tokens_output, thinking_tokens, coste_estimado_usd.

    Devuelve un diccionario {model_key: ResumenModelo.to_dict()}.
    """
    por_modelo: dict[str, list[dict[str, Any]]] = {}

    for fila in resultados:
        if not isinstance(fila, dict):
            continue

        clave = fila.get("model_key")

        if not isinstance(clave, str) or not clave:
            continue

        por_modelo.setdefault(clave, []).append(fila)

    resumen: dict[str, dict[str, Any]] = {}

    for model_key, filas in por_modelo.items():
        ejecuciones = len(filas)

        exitosas = sum(1 for fila in filas if fila.get("status") == "ok")
        tasa_exito = round(exitosas / ejecuciones, 4) if ejecuciones else None

        costes = [
            fila.get("coste_estimado_usd")
            for fila in filas
            if isinstance(fila.get("coste_estimado_usd"), (int, float))
        ]
        coste_total = round(sum(costes), 8) if costes else None
        coste_medio = round(sum(costes) / len(costes), 8) if costes else None

        ratios_thinking = [
            ratio
            for fila in filas
            if (
                ratio := ratio_thinking(
                    tokens_output=fila.get("tokens_output"),
                    thinking_tokens=fila.get("thinking_tokens"),
                )
            )
            is not None
        ]
        ratio_thinking_medio = (
            round(sum(ratios_thinking) / len(ratios_thinking), 4)
            if ratios_thinking
            else None
        )

        resumen_modelo = ResumenModelo(
            model_key=model_key,
            ejecuciones=ejecuciones,
            tasa_exito_schema=tasa_exito,
            latencia_total_ms=resumir_serie(
                fila.get("latencia_total_ms") for fila in filas
            ),
            latencia_modelo_ms=resumir_serie(
                fila.get("latencia_modelo_ms") for fila in filas
            ),
            tokens_input=resumir_serie(
                fila.get("tokens_input") for fila in filas
            ),
            tokens_output=resumir_serie(
                fila.get("tokens_output") for fila in filas
            ),
            thinking_tokens=resumir_serie(
                fila.get("thinking_tokens") for fila in filas
            ),
            coste_total_usd=coste_total,
            coste_medio_usd=coste_medio,
            ratio_thinking_medio=ratio_thinking_medio,
        )

        resumen[model_key] = resumen_modelo.to_dict()

    return resumen


# ============================================================
# PROYECCIÓN DE TRÁFICO
# ============================================================

def proyectar_trafico(
    resumen_modelo: dict[str, Any],
    factor: float,
) -> dict[str, Any]:
    """Proyecta coste y volumen de tokens ante un cambio de tráfico.

    resumen_modelo debe ser una de las entradas devueltas por
    resumir_resultados_benchmark() (o tener el mismo contrato mínimo:
    'ejecuciones', 'coste_total_usd', 'tokens_input'/'tokens_output'
    con su 'media').

    factor representa el multiplicador de volumen, p. ej. 2 para
    "si duplicáramos el tráfico". Pensado para el párrafo exigido
    en el Team Challenge sobre el impacto de escalar el tráfico.
    """
    if factor < 0:
        raise ValueError("El factor de tráfico no puede ser negativo.")

    ejecuciones_actuales = resumen_modelo.get("ejecuciones") or 0
    ejecuciones_proyectadas = round(ejecuciones_actuales * factor)

    coste_total_actual = resumen_modelo.get("coste_total_usd")
    coste_proyectado = (
        round(coste_total_actual * factor, 6)
        if coste_total_actual is not None
        else None
    )

    media_tokens_input = (resumen_modelo.get("tokens_input") or {}).get("media")
    media_tokens_output = (resumen_modelo.get("tokens_output") or {}).get(
        "media"
    )

    tokens_input_total_proyectado = (
        round(media_tokens_input * ejecuciones_proyectadas)
        if media_tokens_input is not None
        else None
    )
    tokens_output_total_proyectado = (
        round(media_tokens_output * ejecuciones_proyectadas)
        if media_tokens_output is not None
        else None
    )

    return {
        "factor": factor,
        "ejecuciones_actuales": ejecuciones_actuales,
        "ejecuciones_proyectadas": ejecuciones_proyectadas,
        "coste_total_actual_usd": coste_total_actual,
        "coste_total_proyectado_usd": coste_proyectado,
        "tokens_input_total_proyectado": tokens_input_total_proyectado,
        "tokens_output_total_proyectado": tokens_output_total_proyectado,
    }

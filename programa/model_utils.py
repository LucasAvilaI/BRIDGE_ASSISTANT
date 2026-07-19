"""
Módulo de utilidades del modelo (Área: LLM y Benchmark).
Utilidades para consultar y validar el registro de modelos.

Responde a: ¿Cómo se consultan y validan esos modelos?
Proporciona el puente de lógica sin duplicidades de constantes ni lógica compleja.
"""

from __future__ import annotations

from config import BENCHMARK_MODELS
from model_registry import DEFAULT_MODEL_KEY, MODELS, PROVIDER_GEMINI, ModelMetadata


def obtener_modelo(model_key: str) -> ModelMetadata:
    """Devuelve una copia de la metadata del modelo solicitado."""
    try:
        return MODELS[model_key].copy()
    except KeyError as error:
        raise KeyError(f"Modelo desconocido o no autorizado: {model_key}") from error


def obtener_modelo_por_defecto() -> ModelMetadata:
    """Devuelve la metadata del modelo configurado para el chat."""
    return obtener_modelo(DEFAULT_MODEL_KEY)


def listar_modelos_benchmark() -> list[str]:
    """Devuelve los modelos del benchmark en el orden definido en config.py."""
    return [
        model_key
        for model_key in BENCHMARK_MODELS
        if model_key in MODELS and MODELS[model_key]["enabled"]
    ]


def validar_modelos_benchmark() -> None:
    """Comprueba la coherencia entre config.py y model_registry.py."""
    if len(BENCHMARK_MODELS) != 2:
        raise ValueError("BENCHMARK_MODELS debe contener exactamente dos modelos.")

    if len(set(BENCHMARK_MODELS)) != len(BENCHMARK_MODELS):
        raise ValueError("BENCHMARK_MODELS no puede contener modelos duplicados.")

    faltantes = [key for key in BENCHMARK_MODELS if key not in MODELS]
    if faltantes:
        raise ValueError(
            "Faltan modelos del benchmark en model_registry.py: "
            + ", ".join(faltantes)
        )

    modelos = [MODELS[key] for key in BENCHMARK_MODELS]

    deshabilitados = [m["model_id"] for m in modelos if not m["enabled"]]
    if deshabilitados:
        raise ValueError(
            "Los modelos del benchmark deben estar habilitados: "
            + ", ".join(deshabilitados)
        )

    for model_key, metadata in zip(BENCHMARK_MODELS, modelos, strict=True):
        if metadata["model_id"] != model_key:
            raise ValueError(
                f"La clave '{model_key}' no coincide con model_id "
                f"'{metadata['model_id']}'."
            )
        if metadata["provider"] != PROVIDER_GEMINI:
            raise ValueError("Todos los modelos oficiales deben usar Gemini.")
        if metadata["cost_input_per_m"] < 0 or metadata["cost_output_per_m"] < 0:
            raise ValueError(f"Costes inválidos para el modelo '{model_key}'.")

"""Registro central de modelos Gemini usados por chat y benchmark.

Este módulo contiene únicamente metadata de modelos. Los parámetros de
 ejecución del benchmark permanecen en ``config.py``.
"""

from __future__ import annotations

from typing import Final, TypedDict

from config import MODEL, MODEL_1, MODEL_2


PROVIDER_GEMINI: Final[str] = "gemini"


class ModelMetadata(TypedDict):
    provider: str
    model_id: str
    enabled: bool
    benchmark_role: str
    display_name: str
    context_window: int
    cost_input_per_m: float
    cost_output_per_m: float
    description: str
    selection_reason: str


# Las claves son los identificadores configurados en config.py. De este modo,
# benchmark.py puede pasar directamente ``model_id`` a gemini_client.py sin
# mantener aliases paralelos o realizar traducciones adicionales.
MODELS: Final[dict[str, ModelMetadata]] = {
    MODEL_2: {
        "provider": PROVIDER_GEMINI,
        "model_id": MODEL_2,
        "enabled": True,
        "benchmark_role": "quality_candidate",
        "display_name": "Gemini 1.5 Pro",
        "context_window": 1_000_000,
        "cost_input_per_m": 1.25,
        "cost_output_per_m": 10.00,
        "description": "Modelo de mayor capacidad para razonamiento complejo.",
        "selection_reason": "Establece la referencia de calidad del benchmark.",
    },
    MODEL_1: {
        "provider": PROVIDER_GEMINI,
        "model_id": MODEL_1,
        "enabled": True,
        "benchmark_role": "efficiency_candidate",
        "display_name": "Gemini 1.5 Flash",
        "context_window": 1_000_000,
        "cost_input_per_m": 0.30,
        "cost_output_per_m": 2.50,
        "description": "Modelo optimizado para latencia y coste.",
        "selection_reason": "Candidato principal para producción por eficiencia.",
    },
}

DEFAULT_MODEL_KEY: Final[str] = MODEL

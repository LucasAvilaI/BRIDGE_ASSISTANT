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
        "benchmark_role": "efficiency_candidate",
        "display_name": "Gemini 3.1 Flash-Lite",
        "context_window": 1_000_000,
        # NOTA: precios de julio 2026, verificar contra
        # https://ai.google.dev/gemini-api/docs/pricing antes de la
        # entrega definitiva.
        "cost_input_per_m": 0.25,
        "cost_output_per_m": 1.50,
        "description": "Modelo más económico y rápido de la familia, pensado para alto volumen.",
        "selection_reason": "Candidato de eficiencia: menor coste y menor latencia del benchmark.",
    },
    MODEL_1: {
        "provider": PROVIDER_GEMINI,
        "model_id": MODEL_1,
        "enabled": True,
        "benchmark_role": "quality_candidate",
        "display_name": "Gemini 3.5 Flash",
        "context_window": 1_000_000,
        "cost_input_per_m": 1.50,
        "cost_output_per_m": 9.00,
        "description": "Modelo flagship de la familia Flash: mejor calidad y razonamiento.",
        "selection_reason": "Establece la referencia de calidad del benchmark.",
    },
}

DEFAULT_MODEL_KEY: Final[str] = MODEL

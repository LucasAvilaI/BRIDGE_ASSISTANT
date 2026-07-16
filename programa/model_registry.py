"""
Registro central de modelos del proyecto (Área: LLM y Benchmark).

Este módulo organiza y asocia la metadata técnica con las constantes
declaradas en config.py de manera limpia y sin importaciones circulares.
"""

from typing import Final
from programa.config import (
    MODEL_1,
    MODEL_2,
    MODEL,
    TEMPERATURE_DEFAULT
)

PROVIDER_GEMINI: Final[str] = "gemini"

# Mapeamos las llaves dinámicamente usando las constantes de config.py
MODELS: Final[dict[str, dict]] = {
    MODEL_2: {  # Evaluará a "gemini_flash_quality"
        "provider": PROVIDER_GEMINI,
        "model_id": MODEL_2,
        "enabled": True,
        "benchmark_role": "quality_candidate",
        "display_name": "Gemini 2.5 Pro",
        "context_window": 2_000_000,
        "cost_input_per_m": 1.25,
        "cost_output_per_m": 5.00,
        "description": "Modelo de alta capacidad de razonamiento para evaluar fidelidad.",
        "selection_reason": "Establece el techo de calidad del benchmark para validar la precisión."
    },
    MODEL_1: {  # Evaluará a "gemini_flash_efficiency"
        "provider": PROVIDER_GEMINI,
        "model_id": MODEL_1,
        "enabled": True,
        "benchmark_role": "efficiency_candidate",
        "display_name": "Gemini 2.5 Flash",
        "context_window": 1_000_000,
        "cost_input_per_m": 0.075,
        "cost_output_per_m": 0.30,
        "description": "Modelo ultra-rápido y optimizado en costes.",
        "selection_reason": "Candidato principal para producción debido a su excelente eficiencia."
    }
}

# Parámetros de control unificados para el benchmark
DEFAULT_MODEL_KEY: Final[str] = MODEL  # Resuelve a la constante seleccionada en config.py
BENCHMARK_TEMPERATURE: Final[float] = TEMPERATURE_DEFAULT
BENCHMARK_MAX_OUTPUT_TOKENS: Final[int] = 512
BENCHMARK_RUNS_PER_CASE: Final[int] = 1
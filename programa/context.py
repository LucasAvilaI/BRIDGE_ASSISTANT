
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from config import (
    DOCUMENT_SCORE_WEIGHTS,
    FAQ_SCORE_WEIGHTS,
    GLOBAL_DOCUMENT_IDS,
    MAX_CONTEXT_DOCUMENTS,
    MAX_CONTEXT_FAQS,
    MIN_DOCUMENT_SCORE,
    MIN_FAQ_SCORE,
)

def cargar_JSON(ruta: Path) -> list[dict]:
    # TO_DO: Adecuar función
    """Carga faq.json desde disco."""
    with ruta.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("faq.json debe ser una lista de entradas")
    return data

# ============================================================
# PALABRAS VACÍAS
# ============================================================

# Palabras frecuentes que no aportan suficiente intención
# para seleccionar documentación.
STOPWORDS = frozenset(
    {
        "a",
        "al",
        "algo",
        "como",
        "con",
        "cual",
        "cuando",
        "de",
        "debo",
        "del",
        "donde",
        "el",
        "ella",
        "en",
        "es",
        "esta",
        "este",
        "hacer",
        "hay",
        "la",
        "las",
        "lo",
        "los",
        "me",
        "mi",
        "mis",
        "necesito",
        "o",
        "para",
        "por",
        "puedo",
        "que",
        "quiero",
        "saber",
        "se",
        "si",
        "sin",
        "sobre",
        "tengo",
        "un",
        "una",
        "unos",
        "unas",
        "y",
        # Fórmulas habituales de saludo o cortesía.
        "hola",
        "gracias",
        "buenos",
        "buenas",
        "dias",
        "tardes",
        "favor",
    }
)


# ============================================================
# CARGA Y VALIDACIÓN DE DATOS
# ============================================================

# MODO VULNERABLE


def seleccionar_faq_vulnerable(faq: list[dict], consulta: str) -> list[dict]:
    """
    Anti-patrón intencional del modo vulnerable:
    Devuelve todas las entradas disponibles sin filtrar por relevancia,
    perfil, permisos, departamento o sensibilidad.

    Se mantiene argumento `consulta` para conservar `seleccionar_faq()` similar
    y facilitar la integración de ambos modos desde logic.py.
    """
    _ = consulta  # deja explícito que el parámetro se recibe, pero se ignora deliberadamente.
    return faq.copy()

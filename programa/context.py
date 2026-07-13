
import json
from pathlib import Path


def cargar_JSON(ruta: Path) -> list[dict]:
    # TO_DO: Adecuar función
    """Carga faq.json desde disco."""
    with ruta.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("faq.json debe ser una lista de entradas")
    return data


def seleccionar_faq(faq: list[dict], consulta: str, max_entradas: int = 1) -> list[dict]:
    """Elige entradas del FAQ por keywords (sin vector DB)."""
    q = (consulta or "").lower()
    puntuaciones: list[tuple[int, dict]] = []

    for entry in faq:
        score = 0
        for kw in entry.get("keywords", []):
            if kw.lower() in q:
                score += 2
        if entry.get("topic_id", "").lower() in q:
            score += 3
        if score > 0:
            puntuaciones.append((score, entry))

    puntuaciones.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in puntuaciones[:max_entradas]]

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

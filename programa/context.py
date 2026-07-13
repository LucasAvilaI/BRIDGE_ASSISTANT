
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

# TO_DO: integrar en logic.py cuando se acuerde el flujo compartido.
# MODO VULNERABLE: contexto sin minimización ni control de acceso.
def seleccionar_contexto_vulnerable(
    entradas: list[dict],
    consulta: str,
) -> list[dict]:
    """
    Anti-patrón intencional: conserva todo el contexto recibido.

    La carga y normalización de las fuentes corresponde al módulo compartido
    de contexto/data. Esta función únicamente modela el fallo vulnerable de
    no aplicar minimización, relevancia ni autorización.
    """
    _ = consulta
    return entradas.copy()



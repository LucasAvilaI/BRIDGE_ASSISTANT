
from config import DOMINIO_KEYWORDS, MAX_INPUT_CHARS, PATRONES_SOSPECHOSOS


def validate_input(texto: str) -> list[str]:
    """Devuelve lista de errores (vacía = OK). Ver README Fase 2, Tarea 1."""
    errores: list[str] = []
    t = (texto or "").strip()
    if not t:
        errores.append("El mensaje no puede estar vacío.")
    if len(t) > MAX_INPUT_CHARS:
        errores.append(f"Mensaje demasiado largo (máx {MAX_INPUT_CHARS} caracteres).")
    t_lower = t.lower()
    for patron in PATRONES_SOSPECHOSOS:
        if patron in t_lower:
            errores.append(f"Patrón no permitido detectado: {patron!r}")
    return errores


def parece_dominio_python(texto: str) -> bool:
    """True si el mensaje parece relacionado con Python/bootcamp. Ver README Fase 2."""
    t = texto.lower()
    return any(k in t for k in DOMINIO_KEYWORDS)


def rechazo_fuera_de_dominio() -> str:
    """Mensaje fijo cuando la pregunta no encaja en el producto."""
    return (
        "Solo puedo ayudarte con Python y ejercicios del bootcamp. "
        "Reformula tu pregunta en ese contexto."
    )

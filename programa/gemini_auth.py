"""
Carga explícita de la credencial de Gemini.

No importa el SDK ni realiza ninguna acción al importar el módulo.
"""


from __future__ import annotations

import getpass
import os

from dotenv import load_dotenv


_ENV_KEY = "GEMINI_API_KEY"


class GeminiAuthError(RuntimeError):
    """La credencial necesaria para Gemini no está disponible."""


def configurar_gemini_api_key(
    *,
    interactivo: bool = False,
    sobrescribir: bool = False,
) -> str:
    """Carga y devuelve GEMINI_API_KEY.

    En chat interactivo puede usarse ``interactivo=True``.
    Benchmark y tests deben mantenerlo en ``False`` para evitar bloqueos.
    """
    load_dotenv(override=sobrescribir)

    api_key = os.getenv(_ENV_KEY, "").strip()

    if not api_key and interactivo:
        api_key = getpass.getpass(
            "Introduce GEMINI_API_KEY (entrada oculta): "
        ).strip()

        if api_key:
            os.environ[_ENV_KEY] = api_key

    if not api_key:
        raise GeminiAuthError(
            "No se ha configurado GEMINI_API_KEY. "
            "Añádela al entorno o al archivo .env."
        )

    return api_key


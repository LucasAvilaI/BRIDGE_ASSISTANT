
import json
import time
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from config import MAX_TOKENS_INPUT, MODEL, TEMPERATURE_DEFAULT, TEMPERATURE_VULNERABLE
from gemini_auth import configurar_gemini_api_key

configurar_gemini_api_key()


@dataclass
class MetricasLlamada:
    elapsed_ms: int
    prompt_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


_client_instance: genai.Client | None = None


def _client() -> genai.Client:
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client()
    return _client_instance


def count_tokens(contents: str) -> int:
    r = _client().models.count_tokens(model=MODEL, contents=contents)
    return int(r.total_tokens or 0)


def _metricas_from_response(response, started: float) -> MetricasLlamada:
    elapsed_ms = int((time.time() - started) * 1000)
    um = response.usage_metadata
    return MetricasLlamada(
        elapsed_ms=elapsed_ms,
        prompt_tokens=getattr(um, "prompt_token_count", None),
        output_tokens=getattr(um, "candidates_token_count", None),
        total_tokens=getattr(um, "total_token_count", None),
    )


def llamar_gemini(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_VULNERABLE,
) -> tuple[str, MetricasLlamada]:
    started = time.time()
    response = _client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    )
    return (response.text or "").strip(), _metricas_from_response(response, started)


def llamar_gemini_json(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_DEFAULT,
) -> tuple[str, MetricasLlamada]:
    started = time.time()
    response = _client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return (response.text or "").strip(), _metricas_from_response(response, started)


def safe_generate(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_VULNERABLE,
    json_mode: bool = False,
) -> tuple[str, MetricasLlamada]:
    tokens = count_tokens(prompt)
    if tokens > MAX_TOKENS_INPUT:
        raise ValueError(
            f"Prompt demasiado grande: {tokens} tokens (máx {MAX_TOKENS_INPUT}). "
            "Recorta contexto en Python."
        )
    if json_mode:
        return llamar_gemini_json(prompt, temperature=temperature)
    return llamar_gemini(prompt, temperature=temperature)

# Auxiliar para generate_structured
def _parsear_respuesta_json(response: Any) -> dict:
    """Convierte la respuesta textual de Gemini en un diccionario."""

    texto = getattr(response, "text", None)

    if not isinstance(texto, str) or not texto.strip():
        raise "Gemini ha devuelto una respuesta vacía."

    try:
        resultado = json.loads(texto.strip())

    except json.JSONDecodeError as error:
        raise "Gemini no ha devuelto un JSON válido." from error

    if not isinstance(resultado, dict):
        raise "La raíz de la respuesta JSON debe ser un objeto."

    return resultado

# Auxiliar para generate_structured
def _validar_parametros_llamada(
    *,
    model_id: Any,
    system_instruction: Any,
    contents: Any,
    temperature: Any,
    max_output_tokens: Any
) -> None:
    """Valida la configuración técnica antes de llamar al modelo."""

    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("'model_id' debe ser un string no vacío.")

    if not isinstance(system_instruction, str) or not system_instruction.strip():
        raise ValueError("'system_instruction' debe ser un string no vacío.")

    if not isinstance(contents, str) or not contents.strip():
        raise ValueError("'contents' debe ser un string no vacío.")

    if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
        raise ValueError("'temperature' debe ser un número.")

    if (
        not isinstance(max_output_tokens, int)
        or isinstance(max_output_tokens, bool)
        or max_output_tokens <= 0
    ):
        raise ValueError("'max_output_tokens' debe ser un entero positivo.")

# Esta función sustituye a llamar_gemini_json/llamar_gemini y safe_generate
def generate_structured(
    *,
    model_id: str,
    system_instruction: str,
    contents: str,
    temperature: float,
    max_output_tokens: int,
) -> tuple[dict, MetricasLlamada]:
    """
    Ejecuta una llamada JSON parametrizada a Gemini.

    No construye prompts, no autoriza la llamada y no valida
    la seguridad de la respuesta. Esas responsabilidades
    corresponden a prompts.py, logic.py y validators.py.
    """

    _validar_parametros_llamada(
        model_id=model_id,
        system_instruction=system_instruction,
        contents=contents,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )

    started = time.perf_counter()

    try:
        response = _client().models.generate_content(
            model=model_id.strip(),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=float(temperature),
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json"
            )
        )

    except Exception as error:
        raise "No se ha podido completar la llamada a Gemini." from error

    metricas = _metricas_from_response(response, started)

    resultado = _parsear_respuesta_json(response)

    return resultado, metricas



def safe_generate_with_system_instruction(
    *,
    system_instruction: str,
    contents: str,
    temperature: float,
    json_mode: bool = True
) -> tuple[str, MetricasLlamada]:
    """
    Llama a Gemini separando instrucciones privilegiadas y datos.

    Esta función solo puede ejecutarse después de comprobar que
    preparar_turno_con_modo() devolvió llamar_modelo=True.
    """
    texto_para_conteo = (f"{system_instruction}\n\n{contents}")

    tokens = count_tokens(texto_para_conteo)

    if tokens > MAX_TOKENS_INPUT:
        raise ValueError(f"Prompt demasiado grande: {tokens} tokens (máx {MAX_TOKENS_INPUT}). Recorta contexto en Python.")

    configuracion = {
        "temperature": temperature,
        "system_instruction": system_instruction
    }

    if json_mode:
        configuracion["response_mime_type"] = "application/json"

    started = time.time()

    response = _client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(**configuracion)
    )

    return (response.text or "").strip(), _metricas_from_response(response,started)

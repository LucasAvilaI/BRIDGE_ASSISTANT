"""Cliente Gemini: generación, JSON, métricas y benchmark.

Responsabilidades de este módulo:
- Encapsular completamente el SDK google-genai.
- Crear y reutilizar el cliente de Gemini.
- Validar parámetros técnicos de generación.
- Contar tokens de entrada.
- Aplicar límites de entrada, salida y razonamiento.
- Separar system_instruction de contents.
- Ejecutar respuestas de texto y JSON.
- Recoger métricas reales de uso.
- Permitir fallback explícito en el chat.
- Garantizar ausencia de fallback en el benchmark.

Este módulo NO:
- construye prompts;
- selecciona documentos o FAQ;
- decide si una consulta es segura;
- valida el contrato funcional de la respuesta;
- contiene la configuración propia del benchmark.

Notas para el equipo:
- No importar google-genai fuera de este módulo.
- logic.py decide cuándo llamar al LLM.
- prompts.py decide qué texto se envía.
- validators.py valida la respuesta funcional.
- benchmark.py proporciona sus propios parámetros de ejecución.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types

from programa.config import (
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_TIMEOUT_MS,
    MAX_OUTPUT_TOKENS,
    MAX_TOKENS_INPUT,
    MODEL,
    TEMPERATURE_DEFAULT,
    TEMPERATURE_SAFE,
    THINKING_LEVEL_CHAT, # esto para los modelos 3.x
#    THINKING_BUDGET_CHAT  # esto es para gemini 2.5
)

from programa.gemini_auth import configurar_gemini_api_key


# ============================================================
# ERRORES DE LA CAPA LLM
# ============================================================

class GeminiClientError(RuntimeError):
    """Error técnico normalizado de la capa LLM.

    Las excepciones concretas del SDK se encapsulan con este tipo
    para evitar que otros módulos dependan de google-genai.
    """


class GeminiEmptyResponseError(GeminiClientError):
    """Gemini respondió, pero no devolvió texto utilizable."""


class GeminiStructuredOutputError(GeminiClientError):
    """La salida del modelo no contiene un objeto JSON válido."""


# ============================================================
# MÉTRICAS DE GENERACIÓN
# ============================================================

@dataclass(frozen=True)
class MetricasLlamada:
    """Métricas asociadas a una generación de Gemini.

    Los recuentos pueden ser None cuando el SDK o el modelo no
    proporcionan alguno de los campos de usage_metadata.
    """

    elapsed_ms: int
    prompt_tokens: int | None
    output_tokens: int | None
    thinking_tokens: int | None
    total_tokens: int | None
    model_id: str | None = None
    fallback_used: bool = False


# ============================================================
# CREACIÓN E INYECCIÓN DEL CLIENTE
# ============================================================

# El cliente se inicializa de forma diferida.
#
# Esto evita:
# - solicitar la API key al importar el módulo;
# - crear conexiones durante tests unitarios;
# - producir efectos secundarios por una simple importación.
_client_instance: genai.Client | Any | None = None

def _obtener_cliente() -> genai.Client | Any:
    """Obtiene el cliente Gemini y lo crea solo cuando se necesita."""

    global _client_instance

    if _client_instance is None:
        api_key = configurar_gemini_api_key(interactivo=False)

        _client_instance = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=GEMINI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(
                    attempts=GEMINI_RETRY_ATTEMPTS,
                    initial_delay=1.0,
                    max_delay=8.0,
                    exp_base=2.0,
                    jitter=0.2,
                    http_status_codes=[
                        408,
                        429,
                        500,
                        502,
                        503,
                        504,
                    ]
                )
            )
        )

        # Depuración opcional:
        # solo lista los modelos disponibles cuando
        # GEMINI_DEBUG_LIST_MODELS=1.
        if os.getenv("GEMINI_DEBUG_LIST_MODELS", "").strip() == "1":

            print("\n--- MODELOS DISPONIBLES EN TU API ---")

            try:
                for modelo in _client_instance.models.list():
                    acciones = getattr(modelo, "supported_actions", []) or []

                    print(f"ID exacto: {modelo.name} | generateContent: {'generateContent' in acciones}")

            except Exception as error:
                print(f"No se pudieron listar los modelos: {type(error).__name__}: {error}")

            print("--------------------------------------\n")

    return _client_instance


def _establecer_cliente_para_tests(cliente: Any | None) -> None:
    """Inyecta un cliente falso o reinicia el cliente almacenado.

    Uso previsto:
        _establecer_cliente_para_tests(cliente_falso)

    Para restaurar la inicialización normal:
        _establecer_cliente_para_tests(None)

    Es una función privada y no forma parte de la API de producción.
    """

    global _client_instance
    _client_instance = cliente


# ============================================================
# VALIDACIONES TÉCNICAS
# ============================================================

def _validar_texto(valor: Any, nombre: str) -> str:
    """Valida y normaliza un argumento textual obligatorio."""

    if not isinstance(valor, str):
        raise TypeError(f"{nombre} debe ser un string.")

    texto = valor.strip()

    if not texto:
        raise ValueError(f"{nombre} no puede estar vacío.")

    return texto


def _validar_modelo(model_id: Any) -> str:
    """Comprueba que el identificador del modelo sea válido."""

    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("'model_id' debe ser un string no vacío.")

    return model_id.strip()


def _validar_temperature(temperature: Any) -> float:
    """Valida el parámetro de aleatoriedad de la generación."""

    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
    ):
        raise TypeError("'temperature' debe ser numérica.")

    valor = float(temperature)

    if not 0.0 <= valor <= 2.0:
        raise ValueError("'temperature' debe estar entre 0.0 y 2.0.")

    return valor


def _validar_max_output_tokens(valor: int | None) -> int:
    """Devuelve el límite de salida validado.

    Cuando el consumidor no proporciona un valor, utiliza
    MAX_OUTPUT_TOKENS definido en config.py.
    """

    if valor is None:
        return MAX_OUTPUT_TOKENS

    if (
        isinstance(valor, bool)
        or not isinstance(valor, int)
        or valor <= 0
    ):
        raise ValueError("'max_output_tokens' debe ser un entero positivo.")

    return valor

# función para los modelos gemini 3.x
# esto sustituye _validar_tinking_budged 
def _validar_thinking_level(valor: str | None,) -> str:
    """
    Valida el nivel de razonamiento utilizado por Gemini 3.x.

    Para el asistente de onboarding se utiliza "minimal"
    por defecto para priorizar una respuesta rápida.

    Los niveles permitidos son:
    - minimal
    - low
    - medium
    - high
    """

    if valor is None:
        valor = THINKING_LEVEL_CHAT

    if not isinstance(valor, str):
        raise TypeError("'thinking_level' debe ser un string.")

    nivel = valor.strip().lower()

    niveles_validos = {
        "minimal",
        "low",
        "medium",
        "high"
    }

    if nivel not in niveles_validos:
        raise ValueError(
            "'thinking_level' debe ser uno de: "
            "minimal, low, medium o high."
        )

    return nivel

# función para los modelos 2.x
# def _validar_thinking_budget(
#     valor: int | None,
#     *,
#     model_id: str,
# ) -> int:
#     """Valida el presupuesto de razonamiento para Gemini 2.5.

#     Valores relevantes:
#     - -1: pensamiento dinámico.
#     - 0: pensamiento desactivado cuando el modelo lo permite.
#     - Valor positivo: presupuesto máximo solicitado.

#     Restricción del proyecto:
#     - Gemini 2.5 Pro no admite presupuesto 0.
#     - Gemini 2.5 Flash sí permite usar 0.
#     """

#     if valor is None:
#         valor = THINKING_BUDGET_CHAT

#     if isinstance(valor, bool) or not isinstance(valor, int):
#         raise TypeError(
#             "'thinking_budget' debe ser un entero."
#         )

#     if valor < -1:
#         raise ValueError(
#             "'thinking_budget' debe ser -1, 0 o un entero positivo."
#         )

#     modelo = model_id.lower()

#     if "gemini-2.5-pro" in modelo:
#         if valor == 0:
#             raise ValueError(
#                 "Gemini 2.5 Pro no permite desactivar completamente "
#                 "el razonamiento con thinking_budget=0."
#             )

#         if valor != -1 and not 128 <= valor <= 32_768:
#             raise ValueError(
#                 "Para Gemini 2.5 Pro, thinking_budget debe ser -1 "
#                 "o estar entre 128 y 32768."
#             )

#     elif "gemini-2.5-flash" in modelo:
#         if valor != -1 and not 0 <= valor <= 24_576:
#             raise ValueError(
#                 "Para Gemini 2.5 Flash, thinking_budget debe ser -1 "
#                 "o estar entre 0 y 24576."
#             )

#     return valor


# ============================================================
# CONSTRUCCIÓN DE LA CONFIGURACIÓN DEL SDK
# ============================================================

# modelos gemini 3.x
def _construir_configuracion(
    *,
    model_id: str,
    temperature: float,
    system_instruction: str | None,
    json_mode: bool,
    response_schema: Any | None,
    max_output_tokens: int | None,
    thinking_level: str | None,
) -> types.GenerateContentConfig:
    """
    Construye GenerateContentConfig de forma centralizada.

    Toda opción específica del SDK se configura aquí para evitar
    configuraciones distintas entre chat, JSON y benchmark.

    El proyecto utiliza modelos Gemini 3.x, por lo que el control
    del razonamiento se realiza mediante thinking_level.
    """

    modelo = _validar_modelo(model_id)

    kwargs: dict[str, Any] = {
        "temperature": _validar_temperature(temperature),
        "max_output_tokens": _validar_max_output_tokens(max_output_tokens),
        "thinking_config": types.ThinkingConfig(thinking_level="minimal", include_thoughts=False)
    }

    if system_instruction is not None:
        kwargs["system_instruction"] = _validar_texto(system_instruction, "system_instruction")

    if json_mode:
        kwargs["response_mime_type"] = "application/json"

        if response_schema is not None:
            kwargs["response_json_schema"] = response_schema

    return types.GenerateContentConfig(**kwargs)

# modelos gemini 2.x
# def _construir_configuracion(
#     *,
#     model_id: str,
#     temperature: float,
#     system_instruction: str | None,
#     json_mode: bool,
#     response_schema: Any | None,
#     max_output_tokens: int | None,
#     thinking_budget: int | None,
# ) -> types.GenerateContentConfig:
#     """Construye GenerateContentConfig de forma centralizada.

#     Toda opción específica del SDK debe añadirse aquí para evitar
#     configuraciones distintas entre chat, JSON y benchmark.
#     """

#     modelo = _validar_modelo(model_id)

#     kwargs: dict[str, Any] = {
#         "temperature": _validar_temperature(temperature),
#         "max_output_tokens": _validar_max_output_tokens(
#             max_output_tokens
#         ),
#         "thinking_config": types.ThinkingConfig(
#             thinking_budget=_validar_thinking_budget(
#                 thinking_budget,
#                 model_id=modelo,
#             ),
#             # No se solicita que Gemini devuelva sus pensamientos.
#             include_thoughts=False,
#         ),
#     }

#     if system_instruction is not None:
#         kwargs["system_instruction"] = _validar_texto(
#             system_instruction,
#             "system_instruction",
#         )

#     if json_mode:
#         kwargs["response_mime_type"] = "application/json"

#         if response_schema is not None:
#             kwargs["response_json_schema"] = response_schema

#     return types.GenerateContentConfig(**kwargs)


# ============================================================
# RECUENTO DE TOKENS
# ============================================================

def count_tokens(
    contents: str,
    *,
    model_id: str = MODEL,
    system_instruction: str | None = None,
) -> int:
    """Cuenta los tokens de entrada para un modelo concreto.
    
    Incluye manejo de errores para evitar detenciones si el modelo no 
    soporta el método count_tokens o no es encontrado.
    """

    contents_limpio = _validar_texto(contents, "contents")
    modelo = _validar_modelo(model_id)

    if system_instruction is not None:
        instruccion_limpia = _validar_texto(system_instruction, "system_instruction")
        entrada_recuento = f"{instruccion_limpia}\n\n{contents_limpio}"
    else:
        entrada_recuento = contents_limpio

    try:
        respuesta = _obtener_cliente().models.count_tokens(
            model=modelo,
            contents=entrada_recuento
        )
        return int(getattr(respuesta, "total_tokens", 0) or 0)

    except Exception as error:
        # Mantenemos estructura, pero añadimos visibilidad y resiliencia
        print(f"DEBUG: Fallo al contar tokens con {modelo}: {error}")
        
        # Opcional: Si queremos que el código no falle en el benchmark o chat, 
        # se puede devolver una estimación segura en lugar de lanzar la excepción.
        # Si se prefiere seguir lanzando el error como antes, borrar las siguientes 2 líneas:
        estimacion = len(entrada_recuento) // 4
        return estimacion

        # Si se prefiere mantener lógica de lanzar el error:
        # raise GeminiClientError(
        #     f"No se han podido contar tokens con {modelo}."
        # ) from error


# ============================================================
# EXTRACCIÓN DE RESPUESTA Y MÉTRICAS
# ============================================================

def _extraer_texto(response: Any) -> str:
    """Extrae el texto final y rechaza respuestas vacías."""

    texto = getattr(response, "text", None)

    if not isinstance(texto, str) or not texto.strip():
        raise GeminiEmptyResponseError("Gemini no devolvió una respuesta utilizable.")

    return texto.strip()


def _extraer_metricas(
    response: Any,
    *,
    started: float,
    model_id: str,
    fallback_used: bool,
) -> MetricasLlamada:
    """Obtiene métricas sin asumir que todos los campos existen."""

    usage = getattr(response, "usage_metadata", None)

    return MetricasLlamada(
        elapsed_ms=round((perf_counter() - started) * 1000),
        prompt_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        thinking_tokens=getattr(usage, "thoughts_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
        model_id=model_id,
        fallback_used=fallback_used
    )


# ============================================================
# GENERACIÓN INTERNA: UNA SOLA LLAMADA
# ============================================================

def _estimar_tokens_entrada(
    contents: str,
    system_instruction: str | None
) -> int:
    """
    Realiza una estimación local y conservadora del número de tokens.

    Evita realizar una petición adicional a la API de Gemini antes
    de cada generación.

    La estimación se utiliza únicamente como protección frente a
    entradas excesivamente grandes. Los tokens reales de la llamada
    se obtienen posteriormente desde usage_metadata.
    """

    partes = []

    if system_instruction:
        partes.append(system_instruction)

    partes.append(contents)

    texto_total = "\n\n".join(partes)

    # Estimación conservadora aproximada.
    return max(1, len(texto_total) // 3)

def _generar_una_vez(
    contents: str,
    *,
    model_id: str,
    temperature: float,
    system_instruction: str | None = None,
    json_mode: bool = False,
    response_schema: Any | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None, # modelos 3.x
    # thinking_budget: int | None = None, # modelos 2.x
    fallback_used: bool = False,
) -> tuple[str, MetricasLlamada]:
    """Ejecuta una única generación con un modelo exacto.

    Pipeline común:
    1. Valida contents y model_id.
    2. Cuenta tokens de entrada.
    3. Comprueba MAX_TOKENS_INPUT.
    4. Construye la configuración del SDK.
    5. Ejecuta generate_content.
    6. Extrae texto y métricas.

    Esta función no realiza fallback por sí sola.
    """

    contents_limpio = _validar_texto(contents, "contents")
    modelo = _validar_modelo(model_id)

    # modelos 3.x
    tokens_entrada_estimados = _estimar_tokens_entrada(contents_limpio, system_instruction)

    if tokens_entrada_estimados > MAX_TOKENS_INPUT:
        raise ValueError(
            "La entrada estimada es demasiado grande: "
            f"{tokens_entrada_estimados} tokens aproximadamente "
            f"(máximo permitido: {MAX_TOKENS_INPUT})."
        )

    # modelos 2.x
    # tokens_entrada = count_tokens(
    #     contents_limpio,
    #     model_id=modelo,
    #     system_instruction=system_instruction
    # )

    # if tokens_entrada > MAX_TOKENS_INPUT:
    #     raise ValueError(
    #         f"Entrada demasiado grande: {tokens_entrada} tokens "
    #         f"(máximo {MAX_TOKENS_INPUT})."
    #     )

    config = _construir_configuracion(
        model_id=modelo,
        temperature=temperature,
        system_instruction=system_instruction,
        json_mode=json_mode,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )

    started = perf_counter()

    try:
        response = _obtener_cliente().models.generate_content(
            model=modelo,
            contents=contents_limpio,
            config=config
        )
#    except Exception as error:
#        raise GeminiClientError(
#            f"Ha fallado la generación con el modelo {modelo}."
#        ) from error
    except Exception as error:
        raise GeminiClientError(
            f"Ha fallado la generación con el modelo {modelo}. "
            f"Error original: "
            f"{type(error).__name__}: {error}"
        ) from error

    texto = _extraer_texto(response)

    metricas = _extraer_metricas(
        response,
        started=started,
        model_id=modelo,
        fallback_used=fallback_used
    )

    return texto, metricas


# ============================================================
# GENERACIÓN INTERNA: FALLBACK EXPLÍCITO
# ============================================================

def _generar_con_fallback(
    contents: str,
    *,
    model_id: str,
    fallback_model_id: str | None,
    temperature: float,
    system_instruction: str | None,
    json_mode: bool,
    response_schema: Any | None,
    max_output_tokens: int | None,
    thinking_level: str | None = None,
    # thinking_budget: int | None,
) -> tuple[str, MetricasLlamada]:
    """Ejecuta el modelo principal y, opcionalmente, un fallback.

    El fallback:
    - no se activa de forma automática;
    - solo se usa si fallback_model_id contiene otro modelo;
    - solo se ejecuta ante un GeminiClientError;
    - no debe utilizarse desde el benchmark.
    """

    try:
        return _generar_una_vez(
            contents,
            model_id=model_id,
            temperature=temperature,
            system_instruction=system_instruction,
            json_mode=json_mode,
            response_schema=response_schema,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level
            # thinking_budget=thinking_budget,
        )

    except GeminiClientError:
        if fallback_model_id is None or fallback_model_id == model_id:
            raise

    return _generar_una_vez(
        contents,
        model_id=fallback_model_id,
        temperature=temperature,
        system_instruction=system_instruction,
        json_mode=json_mode,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level,
        # thinking_budget=thinking_budget,
        fallback_used=True
    )


# ============================================================
# API PÚBLICA: GENERACIÓN DIRECTA
# ============================================================

def llamar_gemini(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_DEFAULT,
    model_id: str = MODEL,
    system_instruction: str | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None,
    # thinking_budget: int | None = None,
) -> tuple[str, MetricasLlamada]:
    """Genera texto con un modelo exacto y sin fallback.

    Cuando max_output_tokens o thinking_budget son None, se toman
    MAX_OUTPUT_TOKENS y THINKING_BUDGET_CHAT desde config.py.
    """

    return _generar_una_vez(
        prompt,
        model_id=model_id,
        temperature=temperature,
        system_instruction=system_instruction,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )


def llamar_gemini_json(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_DEFAULT,
    model_id: str = MODEL,
    system_instruction: str | None = None,
    response_schema: Any | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None,
    # thinking_budget: int | None = None,
) -> tuple[str, MetricasLlamada]:
    """Genera una respuesta JSON con un modelo exacto y sin fallback."""

    return _generar_una_vez(
        prompt,
        model_id=model_id,
        temperature=temperature,
        system_instruction=system_instruction,
        json_mode=True,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )


# ============================================================
# API PÚBLICA: FLUJO VULNERABLE
# ============================================================

def safe_generate(
    prompt: str,
    *,
    temperature: float = TEMPERATURE_DEFAULT,
    json_mode: bool = False,
    model_id: str = MODEL,
    fallback_model_id: str | None = None,
    response_schema: Any | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None,
    # thinking_budget: int | None = None,
) -> tuple[str, MetricasLlamada]:
    """Wrapper compatible para prompts sin canal de sistema separado.

    Se conserva para:
    - el modo vulnerable;
    - consumidores anteriores de la API;
    - comparaciones entre flujo seguro y vulnerable.

    El nombre se mantiene por compatibilidad, aunque este wrapper
    no incorpora por sí solo las defensas del modo seguro.
    """

    return _generar_con_fallback(
        prompt,
        model_id=model_id,
        fallback_model_id=fallback_model_id,
        temperature=temperature,
        system_instruction=None,
        json_mode=json_mode,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )


# ============================================================
# API PÚBLICA: FLUJO SEGURO
# ============================================================

def safe_generate_with_system_instruction(
    contents: str,
    *,
    system_instruction: str,
    temperature: float = TEMPERATURE_SAFE,
    json_mode: bool = False,
    model_id: str = MODEL,
    fallback_model_id: str | None = None,
    response_schema: Any | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None,
    # thinking_budget: int | None = None,
) -> tuple[str, MetricasLlamada]:
    """Genera contenido separando system_instruction de contents.
    No valida la seguridad de la entrada, el contexto ni la salida.
    Esas comprobaciones corresponden a validators.py y logic.py.

    system_instruction:
        Contiene reglas funcionales y de seguridad con prioridad de sistema.

    contents:
        Contiene la pregunta, historial, documentos y FAQ tratados como datos.
    """

    return _generar_con_fallback(
        contents,
        model_id=model_id,
        fallback_model_id=fallback_model_id,
        temperature=temperature,
        system_instruction=system_instruction,
        json_mode=json_mode,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )


# ============================================================
# PARSEO DE SALIDA ESTRUCTURADA
# ============================================================

def parsear_json(texto: str) -> dict[str, Any]:
    """Convierte una salida JSON en un diccionario Python.

    Esta función comprueba únicamente:
        - que el texto sea JSON válido;
        - que la raíz sea un objeto.

    No valida el contrato funcional de la respuesta.

    La comprobación de campos, tipos, categorías, fuentes
    autorizadas y reglas del producto corresponde a
    validators.py.
    """

    texto_limpio = _validar_texto(texto, "texto")

    try:
        resultado = json.loads(texto_limpio)

    except json.JSONDecodeError as error:
        raise GeminiStructuredOutputError("Gemini no devolvió un JSON válido.") from error

    if not isinstance(resultado, dict):
        raise GeminiStructuredOutputError("La respuesta JSON debe tener un objeto como raíz.")

    return resultado


# ============================================================
# API PÚBLICA: BENCHMARK
# ============================================================

def ejecutar_caso_benchmark(
    contents: str,
    *,
    model_id: str,
    temperature: float = TEMPERATURE_DEFAULT,
    system_instruction: str | None = None,
    json_mode: bool = False,
    response_schema: Any | None = None,
    max_output_tokens: int | None = None,
    thinking_level: str | None = None
    # thinking_budget: int | None = None,
) -> tuple[str, MetricasLlamada]:
    """Ejecuta un caso de benchmark con un modelo exacto.

    Esta función reutiliza el mismo pipeline que el chat, pero:
    - exige model_id explícito;
    - nunca utiliza fallback;
    - permite que benchmark.py inyecte su propia configuración.

    benchmark.py debería pasar:
    - BENCHMARK_TEMPERATURE;
    - BENCHMARK_MAX_OUTPUT_TOKENS;
    - BENCHMARK_THINKING_BUDGET.
    """

    return _generar_una_vez(
        contents,
        model_id=model_id,
        temperature=temperature,
        system_instruction=system_instruction,
        json_mode=json_mode,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level
        # thinking_budget=thinking_budget,
    )

"""
Lógica de negocio del asistente de onboarding.

El producto opera siempre mediante el pipeline seguro:
preparar_turno_seguro() y finalizar_turno_seguro().

Las funciones preparar_turno() y finalizar_turno() conservan el núcleo
estructural común para integraciones, pruebas y la demo 5 aislada.
Este módulo no expone ningún selector ni modo vulnerable.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any

from config import (
    ASSISTANT_CONFIG_DEFAULT,
    DOMAIN_KEYWORDS,
    MAX_CONTEXT_DOCUMENTS,
    MAX_CONTEXT_FAQS,
    ONBOARDING_PROFILE_DAYS,
    PERFILES,
    REQUIRED_RESPONSE_FIELDS,
    VALID_CATEGORIES,
    VALID_PROFILES,
)
from context import construir_contexto, normalizar_texto
from state import append_assistant, append_user, ultimos_n
from validators import (
    validar_contexto_seguro,
    validar_entrada_segura,
    validar_salida_segura,
    validar_salida_checklist,
)


# ============================================================
# RESPUESTAS ESTÁNDAR
# ============================================================

def respuesta_ok(mensaje: str, data: dict | None = None) -> dict:
    """
    Construye la respuesta estándar de éxito.
    """
    return {
        "status": "ok",
        "mensaje": mensaje,
        "data": data or {},
    }


def respuesta_error(mensaje: str, errores: list[str]) -> dict:
    """
    Construye la respuesta estándar de error.
    """
    return {
        "status": "error",
        "mensaje": mensaje,
        "data": {"errores": errores},
    }


# ============================================================
# VALIDACIONES DE ARQUITECTURA
# ============================================================

def _validar_estado(estado: Any) -> None:
    """
    Valida la estructura mínima del estado conversacional.
    """
    if not isinstance(estado, dict):
        raise TypeError("El estado debe ser un diccionario.")

    mensajes = estado.get("messages")

    if not isinstance(mensajes, list):
        raise ValueError(
            "El estado debe contener una lista en el campo 'messages'."
        )

    if not all(isinstance(mensaje, dict) for mensaje in mensajes):
        raise ValueError(
            "Todos los mensajes del estado deben ser diccionarios."
        )

    turnos = estado.get("turnos")

    if not isinstance(turnos, int) or isinstance(turnos, bool):
        raise ValueError(
            "El estado debe contener un entero en el campo 'turnos'."
        )

    if turnos < 0:
        raise ValueError(
            "El número de turnos no puede ser negativo."
        )


def _validar_consulta(consulta: Any) -> str:
    """
    Valida y normaliza superficialmente la consulta.

    Las validaciones específicas de seguridad se aplican en
    preparar_turno_seguro().
    """
    if not isinstance(consulta, str):
        raise TypeError("La consulta debe ser un string.")

    consulta_limpia = consulta.strip()

    if not consulta_limpia:
        raise ValueError("La consulta no puede estar vacía.")

    return consulta_limpia


def _validar_diccionario(valor: Any, nombre: str) -> dict:
    """
    Comprueba que un valor sea un diccionario.
    """
    if not isinstance(valor, dict):
        raise TypeError(f"{nombre} debe ser un diccionario.")

    return valor


def _validar_lista(valor: Any, nombre: str) -> list:
    """
    Comprueba que un valor sea una lista.

    La validación específica de documentos y FAQ corresponde
    a context.py.
    """
    if not isinstance(valor, list):
        raise TypeError(f"{nombre} debe ser una lista.")

    return valor


def _validar_entero_no_negativo(valor: Any, nombre: str) -> int:
    """
    Comprueba que un valor sea un entero no negativo.
    """
    if (
        not isinstance(valor, int)
        or isinstance(valor, bool)
        or valor < 0
    ):
        raise ValueError(
            f"{nombre} debe ser un entero no negativo."
        )

    return valor


def _resolver_configuracion(
    configuracion: dict | None,
) -> dict:
    """
    Combina la configuración por defecto con una configuración
    parcial proporcionada para la interacción.
    """
    if (
        configuracion is not None
        and not isinstance(configuracion, dict)
    ):
        raise TypeError(
            "La configuración debe ser un diccionario o None."
        )

    configuracion_final = deepcopy(
        ASSISTANT_CONFIG_DEFAULT
    )

    if configuracion:
        configuracion_final.update(
            deepcopy(configuracion)
        )

    perfil_configurado = configuracion_final.get(
        "perfil_activo"
    )

    if perfil_configurado not in VALID_PROFILES:
        raise ValueError(
            f"Perfil configurado desconocido: "
            f"{perfil_configurado!r}."
        )

    ventana_historial = configuracion_final.get(
        "max_turnos_historial"
    )

    limite_documentos = configuracion_final.get(
        "max_documentos_contexto",
        MAX_CONTEXT_DOCUMENTS,
    )

    limite_faqs = configuracion_final.get(
        "max_faqs_contexto",
        MAX_CONTEXT_FAQS,
    )

    _validar_entero_no_negativo(
        ventana_historial,
        "max_turnos_historial",
    )

    _validar_entero_no_negativo(
        limite_documentos,
        "max_documentos_contexto",
    )

    _validar_entero_no_negativo(
        limite_faqs,
        "max_faqs_contexto",
    )

    idioma = configuracion_final.get(
        "idioma_respuesta"
    )

    if not isinstance(idioma, str) or not idioma.strip():
        raise ValueError(
            "'idioma_respuesta' debe ser un string no vacío."
        )

    max_palabras = configuracion_final.get(
        "max_palabras"
    )

    if (
        not isinstance(max_palabras, int)
        or isinstance(max_palabras, bool)
        or max_palabras <= 0
    ):
        raise ValueError(
            "'max_palabras' debe ser un entero positivo."
        )

    return configuracion_final


# ============================================================
# DÍA DE ONBOARDING
# ============================================================

def calcular_dia_onboarding(
    empleado: dict,
    fecha_referencia: date | None = None,
) -> int:
    """
    Calcula el día de onboarding del empleado.

    La fecha de incorporación debe encontrarse en el campo
    'fecha_inicio' y utilizar el formato ISO AAAA-MM-DD.

    El día de incorporación se considera el día 1.
    Las fechas futuras también devuelven el día 1.
    """
    _validar_diccionario(
        empleado,
        "El empleado",
    )

    fecha_inicio_raw = empleado.get(
        "fecha_inicio"
    )

    if not isinstance(fecha_inicio_raw, str):
        raise ValueError(
            "El empleado debe contener una fecha_inicio "
            "en formato AAAA-MM-DD."
        )

    fecha_inicio_limpia = (
        fecha_inicio_raw.strip()
    )

    if not fecha_inicio_limpia:
        raise ValueError(
            "La fecha_inicio del empleado no puede estar vacía."
        )

    try:
        fecha_inicio = date.fromisoformat(
            fecha_inicio_limpia
        )
    except ValueError as error:
        raise ValueError(
            "La fecha_inicio del empleado debe utilizar "
            "el formato AAAA-MM-DD."
        ) from error

    if fecha_referencia is None:
        referencia = date.today()
    elif isinstance(fecha_referencia, date):
        referencia = fecha_referencia
    else:
        raise TypeError(
            "La fecha de referencia debe ser una fecha o None."
        )

    dias_transcurridos = (
        referencia - fecha_inicio
    ).days

    if dias_transcurridos < 0:
        return 1

    return dias_transcurridos + 1


# ============================================================
# CLASIFICACIÓN PRELIMINAR
# ============================================================

def _contar_coincidencias(
    consulta_normalizada: str,
    expresiones: tuple[str, ...],
) -> int:
    """
    Cuenta las expresiones de una categoría presentes en la
    consulta normalizada.

    Las palabras simples se comparan como términos completos.
    Las expresiones compuestas se buscan de forma literal.
    """
    puntuacion = 0

    for expresion in expresiones:
        expresion_normalizada = normalizar_texto(
            expresion
        )

        if not expresion_normalizada:
            continue

        if " " in expresion_normalizada:
            if (
                expresion_normalizada
                in consulta_normalizada
            ):
                puntuacion += 1

            continue

        patron = (
            rf"\b{re.escape(expresion_normalizada)}\b"
        )

        if re.search(
            patron,
            consulta_normalizada,
        ):
            puntuacion += 1

    return puntuacion


def clasificar_consulta(
    consulta: str,
) -> str:
    """
    Clasifica preliminarmente una consulta mediante las señales
    definidas en DOMAIN_KEYWORDS.

    Si no existe ninguna coincidencia devuelve 'general'.
    La categoría 'out_of_scope' no se asigna únicamente mediante
    palabras clave.
    """
    consulta_limpia = _validar_consulta(
        consulta
    )

    consulta_normalizada = normalizar_texto(
        consulta_limpia
    )

    puntuaciones: list[
        tuple[int, int, str]
    ] = []

    for posicion, (
        categoria,
        expresiones,
    ) in enumerate(
        DOMAIN_KEYWORDS.items()
    ):
        if categoria not in VALID_CATEGORIES:
            continue

        puntuacion = _contar_coincidencias(
            consulta_normalizada,
            expresiones,
        )

        puntuaciones.append(
            (
                puntuacion,
                -posicion,
                categoria,
            )
        )

    if not puntuaciones:
        return "general"

    (
        mejor_puntuacion,
        _,
        mejor_categoria,
    ) = max(puntuaciones)

    if mejor_puntuacion <= 0:
        return "general"

    return mejor_categoria


# ============================================================
# SELECCIÓN DEL PERFIL
# ============================================================

def seleccionar_perfil(
    categoria_preliminar: str,
    dia_onboarding: int,
) -> str:
    """
    Selecciona el perfil funcional según la categoría preliminar
    y el día de onboarding.

    Prioridad:
    1. IT.
    2. RRHH.
    3. Onboarding durante los días 1 a 7.
    4. Administrativo de RRHH desde el día 8.
    """
    if (
        categoria_preliminar
        not in VALID_CATEGORIES
    ):
        raise ValueError(
            f"Categoría preliminar desconocida: "
            f"{categoria_preliminar!r}."
        )

    if (
        not isinstance(dia_onboarding, int)
        or isinstance(dia_onboarding, bool)
        or dia_onboarding < 1
    ):
        raise ValueError(
            "El día de onboarding debe ser un entero "
            "igual o superior a 1."
        )

    if categoria_preliminar == "it":
        perfil_activo = "it"
    elif categoria_preliminar == "rrhh":
        perfil_activo = "administrativo_rrhh"
    elif (
        dia_onboarding
        <= ONBOARDING_PROFILE_DAYS
    ):
        perfil_activo = "onboarding"
    else:
        perfil_activo = "administrativo_rrhh"

    if perfil_activo not in VALID_PROFILES:
        raise ValueError(
            f"Perfil funcional desconocido: "
            f"{perfil_activo!r}."
        )

    return perfil_activo


# ============================================================
# PREPARACIÓN DEL TURNO
# ============================================================

def preparar_turno(
    estado: dict,
    consulta: str,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    configuracion: dict | None = None,
    fecha_referencia: date | None = None,
) -> dict:
    """
    Prepara un turno completo sin construir prompts ni invocar
    ningún proveedor LLM.

    Esta función contiene el núcleo estructural común. El producto
    debe utilizar preparar_turno_seguro() como entrada normal.

    Devuelve el paquete de interacción que deberá consumir el
    adaptador implementado por el área LLM y Benchmark.
    """
    try:
        _validar_estado(estado)

        consulta_limpia = _validar_consulta(
            consulta
        )

        empleado_validado = _validar_diccionario(
            empleado,
            "El empleado",
        )

        empresa_validada = _validar_diccionario(
            empresa,
            "La empresa",
        )

        documentos_validados = _validar_lista(
            documentos,
            "Los documentos",
        )

        faqs_validadas = _validar_lista(
            faqs,
            "Las FAQ",
        )

        configuracion_final = (
            _resolver_configuracion(
                configuracion
            )
        )

        dia_onboarding = calcular_dia_onboarding(
            empleado_validado,
            fecha_referencia,
        )

        categoria_preliminar = clasificar_consulta(
            consulta_limpia
        )

        perfil_funcional = seleccionar_perfil(
            categoria_preliminar,
            dia_onboarding,
        )

        configuracion_final[
            "perfil_activo"
        ] = perfil_funcional

        limite_documentos = (
            configuracion_final[
                "max_documentos_contexto"
            ]
        )

        limite_faqs = (
            configuracion_final[
                "max_faqs_contexto"
            ]
        )

        contexto = construir_contexto(
            consulta=consulta_limpia,
            empleado=empleado_validado,
            documentos=documentos_validados,
            faqs=faqs_validadas,
            limite_documentos=limite_documentos,
            limite_faqs=limite_faqs,
        )

        ventana_historial = (
            configuracion_final[
                "max_turnos_historial"
            ]
        )

        historial = ultimos_n(
            estado,
            ventana_historial,
        )

        perfil_empleado = empleado_validado.get(
            "perfil"
        )

        if (
            not isinstance(perfil_empleado, str)
            or not perfil_empleado.strip()
        ):
            raise ValueError(
                "El empleado debe contener un perfil válido."
            )

        turno_preparado = {
            "consulta": consulta_limpia,
            "empleado": deepcopy(empleado_validado),
            "empresa": deepcopy(empresa_validada),
            "perfil_empleado": empleado_validado["perfil"],
            "perfil_funcional": perfil_activo,
            "configuracion_perfil_funcional": deepcopy(PERFILES[perfil_activo]),
            "categoria_preliminar": categoria_preliminar,
            "dia_onboarding": dia_onboarding,
            "contexto": deepcopy(contexto),
            "historial": deepcopy(historial),
            "configuracion": deepcopy(configuracion_final)
        }

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        return respuesta_error(
            "No se ha podido preparar el turno.",
            [str(error)],
        )

    return respuesta_ok(
        "Turno preparado",
        {
            "turno_preparado": (
                turno_preparado
            )
        },
    )


# ============================================================
# FINALIZACIÓN DEL TURNO
# ============================================================

def _validar_turno_preparado(
    turno_preparado: Any,
) -> dict:
    """
    Valida el contrato público del turno preparado antes de
    continuar con la finalización del turno.
    """
    if not isinstance(turno_preparado, dict):
        raise TypeError(
            "El turno preparado debe ser un diccionario."
        )

    campos_requeridos = {
        "consulta",
        "empleado",
        "empresa",
        "perfil_empleado",
        "perfil_funcional",
        "configuracion_perfil_funcional",
        "categoria_preliminar",
        "dia_onboarding",
        "contexto",
        "historial",
        "configuracion",
    }

    campos_ausentes = (
        campos_requeridos.difference(
            turno_preparado
        )
    )

    if campos_ausentes:
        campos = ", ".join(sorted(campos_ausentes))

        raise ValueError(f"Faltan campos obligatorios en el turno preparado: {campos}.")

    consulta = turno_preparado["consulta"]
    _validar_consulta(consulta)

    empleado = turno_preparado["empleado"]

    if not isinstance(empleado, dict):
        raise TypeError("El empleado del turno preparado debe ser parte un diccionario.")

    empresa = turno_preparado["empresa"]

    if not isinstance(empresa, dict):
        raise TypeError("La empresa del turno preparado debe formar parte de un diccionario."
        )

        raise ValueError(
            "Faltan campos obligatorios en el turno "
            f"preparado: {campos}."
        )

    _validar_consulta(
        turno_preparado["consulta"]
    )

    empleado = turno_preparado[
        "empleado"
    ]

    if not isinstance(empleado, dict):
        raise TypeError(
            "El empleado del turno preparado "
            "debe ser un diccionario."
        )

    empresa = turno_preparado[
        "empresa"
    ]

    if not isinstance(empresa, dict):
        raise TypeError(
            "La empresa del turno preparado "
            "debe ser un diccionario."
        )

    perfil_empleado = turno_preparado[
        "perfil_empleado"
    ]

    if (
        not isinstance(perfil_empleado, str)
        or not perfil_empleado.strip()
    ):
        raise ValueError(
            "El perfil del empleado debe ser "
            "una cadena no vacía."
        )

    perfil_funcional = turno_preparado[
        "perfil_funcional"
    ]

    if perfil_funcional not in VALID_PROFILES:
        raise ValueError(
            f"Perfil funcional desconocido: "
            f"{perfil_funcional!r}."
        )

    configuracion_perfil = (
        turno_preparado[
            "configuracion_perfil_funcional"
        ]
    )

    if not isinstance(
        configuracion_perfil,
        dict,
    ):
        raise TypeError(
            "La configuración del perfil funcional "
            "debe ser un diccionario."
        )

    categoria = turno_preparado[
        "categoria_preliminar"
    ]

    if categoria not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoría preliminar desconocida: "
            f"{categoria!r}."
        )

    dia_onboarding = turno_preparado[
        "dia_onboarding"
    ]

    if (
        not isinstance(dia_onboarding, int)
        or isinstance(dia_onboarding, bool)
        or dia_onboarding < 1
    ):
        raise ValueError(
            "El día de onboarding del turno preparado "
            "debe ser un entero igual o superior a 1."
        )

    contexto = turno_preparado[
        "contexto"
    ]

    if not isinstance(contexto, dict):
        raise TypeError(
            "El contexto del turno preparado "
            "debe ser un diccionario."
        )

    historial = turno_preparado[
        "historial"
    ]

    if not isinstance(historial, list):
        raise TypeError(
            "El historial del turno preparado "
            "debe ser una lista."
        )

    configuracion = turno_preparado[
        "configuracion"
    ]

    if not isinstance(configuracion, dict):
        raise TypeError(
            "La configuración del turno preparado "
            "debe ser un diccionario."
        )

    if (
        configuracion.get("perfil_activo")
        != perfil_funcional
    ):
        raise ValueError(
            "El perfil activo de la configuración "
            "no coincide con el perfil funcional "
            "del turno."
        )

    return turno_preparado


def _validar_lista_strings(
    valor: Any,
    nombre: str,
) -> list[str]:
    """
    Valida una lista cuyos elementos deben ser strings.
    """
    if not isinstance(valor, list):
        raise ValueError(
            f"El campo '{nombre}' debe ser una lista."
        )

    if not all(
        isinstance(elemento, str)
        for elemento in valor
    ):
        raise ValueError(
            f"Todos los elementos de '{nombre}' "
            "deben ser strings."
        )

    return valor


def _validar_resultado_externo(
    resultado_externo: Any,
) -> dict:
    """
    Valida el contrato mínimo de la respuesta externa.

    La validación segura completa corresponde a validators.py.
    """
    if not isinstance(resultado_externo, dict):
        raise TypeError(
            "El resultado externo debe ser un diccionario."
        )

    campos_ausentes = (
        REQUIRED_RESPONSE_FIELDS.difference(
            resultado_externo
        )
    )

    if campos_ausentes:
        campos = ", ".join(
            sorted(campos_ausentes)
        )

        raise ValueError(
            "Faltan campos obligatorios en el resultado "
            f"externo: {campos}."
        )

    campos_adicionales = (
        set(resultado_externo).difference(
            REQUIRED_RESPONSE_FIELDS
        )
    )

    if campos_adicionales:
        campos = ", ".join(
            sorted(campos_adicionales)
        )

        raise ValueError(
            "El resultado externo contiene campos "
            f"no permitidos: {campos}."
        )

    in_scope = resultado_externo[
        "in_scope"
    ]

    if not isinstance(in_scope, bool):
        raise ValueError(
            "El campo 'in_scope' debe ser booleano."
        )

    categoria = resultado_externo[
        "category"
    ]

    if categoria not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoría externa desconocida: "
            f"{categoria!r}."
        )

    respuesta = resultado_externo[
        "answer"
    ]

    if (
        not isinstance(respuesta, str)
        or not respuesta.strip()
    ):
        raise ValueError(
            "El campo 'answer' debe ser "
            "un string no vacío."
        )

    _validar_lista_strings(
        resultado_externo["document_ids"],
        "document_ids",
    )

    _validar_lista_strings(
        resultado_externo["faq_ids"],
        "faq_ids",
    )

    needs_escalation = resultado_externo[
        "needs_escalation"
    ]

    if not isinstance(
        needs_escalation,
        bool,
    ):
        raise ValueError(
            "El campo 'needs_escalation' "
            "debe ser booleano."
        )

    escalation_department = (
        resultado_externo[
            "escalation_department"
        ]
    )

    if (
        escalation_department is not None
        and not isinstance(
            escalation_department,
            str,
        )
    ):
        raise ValueError(
            "El campo 'escalation_department' "
            "debe ser un string o None."
        )

    return resultado_externo


def finalizar_turno(
    estado: dict,
    turno_preparado: dict,
    resultado_externo: dict,
) -> dict:
    """
    Finaliza un turno después de recibir una respuesta externa.

    La función valida el contrato mínimo, actualiza el historial
    y devuelve la envolvente estándar del proyecto.

    Esta función contiene el núcleo estructural común. El producto
    debe utilizar finalizar_turno_seguro() como salida normal.
    """
    try:
        _validar_estado(estado)

        turno_validado = (
            _validar_turno_preparado(
                turno_preparado
            )
        )

        resultado_validado = (
            _validar_resultado_externo(
                resultado_externo
            )
        )

        consulta = turno_validado[
            "consulta"
        ]

        respuesta = resultado_validado[
            "answer"
        ].strip()

        append_user(
            estado,
            consulta,
        )

        append_assistant(
            estado,
            respuesta,
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        return respuesta_error(
            "No se ha podido finalizar el turno.",
            [str(error)],
        )

    return respuesta_ok(
        "Turno finalizado",
        {
            "respuesta": respuesta,
            "resultado": deepcopy(resultado_validado),
            "perfil_activo": turno_validado["perfil_funcional"],
            "categoria": resultado_validado["category"],
            "categoria_preliminar": turno_validado["categoria_preliminar"],
            "dia_onboarding": turno_validado["dia_onboarding"]
        }
    )


# ============================================================
# ROBUSTEZ Y SEGURIDAD
# ============================================================

def _registrar_evento_seguridad(
    estado: dict,
    validacion: dict,
    consulta: Any,
) -> None:
    """
    Registra metadatos del evento sin conservar la consulta.
    """
    if (
        not isinstance(estado, dict)
        or not isinstance(validacion, dict)
    ):
        return

    eventos = estado.setdefault(
        "eventos_seguridad",
        [],
    )

    if not isinstance(eventos, list):
        eventos = []

    nuevo_evento = {
        "fase": validacion.get("fase"),
        "codigo": validacion.get("codigo"),
        "longitud_consulta": (
            len(consulta)
            if isinstance(consulta, str)
            else 0
        ),
    }

    eventos.append(nuevo_evento)

    estado["eventos_seguridad"] = (
        eventos[-20:]
    )


def _validacion_permitida(
    validacion: Any,
) -> bool:
    """
    Comprueba el contrato mínimo de una validación de seguridad.
    """
    return (
        isinstance(validacion, dict)
        and isinstance(
            validacion.get("permitido"),
            bool,
        )
        and validacion["permitido"]
    )


def crear_respuesta_controlada(
    validacion: dict,
    *,
    modelo_invocado: bool = False,
) -> dict:
    """
    Adapta una validación rechazada al contrato estándar de logic.py.

    Un bloqueo de seguridad es una respuesta funcional, no un error
    técnico. Por eso mantiene status="ok" y señala que el flujo debe
    detenerse.

    No recibe ni devuelve un modo de seguridad porque el producto
    funciona siempre mediante el pipeline seguro.
    """
    if not isinstance(validacion, dict):
        return respuesta_error(
            "No se ha podido construir la respuesta controlada.",
            [
                "La validación debe ser un diccionario."
            ],
        )

    mensaje_usuario = validacion.get(
        "mensaje_usuario"
    )

    codigo = validacion.get(
        "codigo"
    )

    if (
        not isinstance(mensaje_usuario, str)
        or not mensaje_usuario.strip()
    ):
        return respuesta_error(
            "No se ha podido construir la respuesta controlada.",
            [
                "La validación no contiene un mensaje "
                "de usuario válido."
            ],
        )

    if (
        not isinstance(codigo, str)
        or not codigo.strip()
    ):
        return respuesta_error(
            "No se ha podido construir la respuesta controlada.",
            [
                "La validación no contiene un código válido."
            ],
        )

    return respuesta_ok(
        "Consulta atendida de forma controlada.",
        {
            "respuesta": (
                mensaje_usuario.strip()
            ),
            "llamar_modelo": False,
            "modelo_invocado": (
                modelo_invocado
            ),
            "motivo_bloqueo": (
                codigo.strip()
            ),
        },
    )


def preparar_turno_seguro(
    estado: dict,
    consulta: str,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    configuracion: dict | None = None,
    fecha_referencia: date | None = None,
) -> dict:
    """
    Punto de entrada normal y seguro del producto.

    Secuencia:
    1. valida la entrada antes de preparar el contexto;
    2. reutiliza preparar_turno() para el núcleo estructural;
    3. valida el contexto resultante;
    4. autoriza o bloquea la futura llamada al modelo.

    Puede devolver:
    - un error estructural;
    - una respuesta controlada con llamar_modelo=False;
    - un turno autorizado con llamar_modelo=True.

    Esta función no invoca al modelo.
    """
    validacion_entrada = validar_entrada_segura(
        consulta
    )

    if not isinstance(
        validacion_entrada,
        dict,
    ) or not isinstance(
        validacion_entrada.get("permitido"),
        bool,
    ):
        return respuesta_error(
            "No se ha podido validar la entrada.",
            [
                "El validador de entrada devolvió "
                "una estructura no válida."
            ],
        )

    if not validacion_entrada["permitido"]:
        _registrar_evento_seguridad(
            estado,
            validacion_entrada,
            consulta,
        )

        return crear_respuesta_controlada(
            validacion_entrada,
            modelo_invocado=False,
        )

    resultado = preparar_turno(
        estado=estado,
        consulta=consulta,
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        configuracion=configuracion,
        fecha_referencia=fecha_referencia,
    )

    if resultado.get("status") != "ok":
        return resultado

    datos_resultado = resultado.get(
        "data"
    )

    if not isinstance(
        datos_resultado,
        dict,
    ):
        return respuesta_error(
            "No se ha podido preparar el turno seguro.",
            [
                "La preparación devolvió un campo "
                "'data' no válido."
            ],
        )

    turno_preparado = datos_resultado.get(
        "turno_preparado"
    )

    validacion_contexto = (
        validar_contexto_seguro(
            turno_preparado
        )
    )

    if not isinstance(
        validacion_contexto,
        dict,
    ) or not isinstance(
        validacion_contexto.get("permitido"),
        bool,
    ):
        return respuesta_error(
            "No se ha podido validar el contexto.",
            [
                "El validador de contexto devolvió "
                "una estructura no válida."
            ],
        )

    if not validacion_contexto["permitido"]:
        _registrar_evento_seguridad(
            estado,
            validacion_contexto,
            consulta,
        )

        return crear_respuesta_controlada(
            validacion_contexto,
            modelo_invocado=False,
        )

    datos_resultado[
        "llamar_modelo"
    ] = True

    datos_resultado[
        "modelo_invocado"
    ] = False

    return resultado


# ============================================================
# CHECKLIST DE LA SEMANA 1 (Capacidad 2 del producto)
# ============================================================
#
# Espejo de preparar_turno_seguro() / finalizar_turno_seguro() para
# la segunda capacidad obligatoria del producto (checklist JSON del
# día de onboarding). No existía ningún punto de entrada equivalente:
# el chat es la única capacidad que estaba conectada de extremo a
# extremo.

def _consulta_checklist(dia_onboarding: int) -> str:
    """
    Consulta interna sintética para reutilizar preparar_turno() /
    construir_contexto() en la selección de documentación relevante
    al día de onboarding indicado.

    El checklist no parte de una pregunta libre del empleado, por lo
    que se construye una consulta con las mismas señales de dominio
    que reconoce DOMAIN_KEYWORDS['onboarding'] en config.py, evitando
    así duplicar la lógica de puntuación de context.py.
    """
    return (
        f"checklist tareas iniciales dia {dia_onboarding} de onboarding, "
        "primeros pasos, accesos, bienvenida"
    )


def preparar_checklist_seguro(
    estado: dict,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    configuracion: dict | None = None,
    fecha_referencia: date | None = None,
    dia_onboarding: int | None = None,
) -> dict:
    """
    Punto de entrada normal y seguro para generar el checklist de un
    día de onboarding (1-5).

    Si no se indica dia_onboarding, se calcula igual que en el chat
    mediante calcular_dia_onboarding(). Indicarlo explícitamente
    permite generar el checklist de cualquier día de la semana 1
    (por ejemplo, para comparar el día 1 con el día 3 en una demo),
    sin depender de la fecha_inicio real del empleado.

    Esta función no invoca al modelo.
    """
    try:
        dia_calculado = calcular_dia_onboarding(
            empleado, fecha_referencia
        )
    except (TypeError, ValueError) as error:
        return respuesta_error(
            "No se ha podido preparar el checklist.",
            [str(error)],
        )

    dia_final = (
        dia_calculado if dia_onboarding is None else dia_onboarding
    )

    if (
        not isinstance(dia_final, int)
        or isinstance(dia_final, bool)
        or not 1 <= dia_final <= 5
    ):
        return respuesta_error(
            "No se ha podido preparar el checklist.",
            [
                "El día de onboarding del checklist debe ser "
                "un entero entre 1 y 5."
            ],
        )

    consulta_interna = _consulta_checklist(dia_final)

    resultado = preparar_turno(
        estado=estado,
        consulta=consulta_interna,
        empleado=empleado,
        empresa=empresa,
        documentos=documentos,
        faqs=faqs,
        configuracion=configuracion,
        fecha_referencia=fecha_referencia,
    )

    if resultado.get("status") != "ok":
        return resultado

    datos_resultado = resultado.get("data")

    if not isinstance(datos_resultado, dict):
        return respuesta_error(
            "No se ha podido preparar el checklist.",
            [
                "La preparación devolvió un campo 'data' "
                "no válido."
            ],
        )

    turno_preparado = datos_resultado.get("turno_preparado")

    if not isinstance(turno_preparado, dict):
        return respuesta_error(
            "No se ha podido preparar el checklist.",
            ["No se generó un turno preparado válido."],
        )

    # El día del checklist puede pedirse explícitamente (p. ej. una
    # demo del día 3) y no tiene por qué coincidir con el calculado
    # a partir de fecha_inicio.
    turno_preparado["dia_onboarding"] = dia_final

    validacion_contexto = validar_contexto_seguro(turno_preparado)

    if not isinstance(
        validacion_contexto, dict
    ) or not isinstance(
        validacion_contexto.get("permitido"), bool
    ):
        return respuesta_error(
            "No se ha podido validar el contexto del checklist.",
            [
                "El validador de contexto devolvió una "
                "estructura no válida."
            ],
        )

    if not validacion_contexto["permitido"]:
        _registrar_evento_seguridad(
            estado, validacion_contexto, consulta_interna
        )

        return crear_respuesta_controlada(
            validacion_contexto, modelo_invocado=False
        )

    datos_resultado["turno_preparado"] = turno_preparado
    datos_resultado["llamar_modelo"] = True
    datos_resultado["modelo_invocado"] = False

    return resultado


def finalizar_checklist_seguro(
    estado: dict,
    turno_preparado: dict,
    resultado_externo: dict,
) -> dict:
    """
    Punto de finalización normal y seguro del checklist.

    Espejo de finalizar_turno_seguro(), pero usando el contrato y las
    validaciones propias del checklist (validar_salida_checklist).
    A diferencia del chat, el checklist no se añade al historial
    conversacional: no es la respuesta a una pregunta del empleado,
    sino un plan estructurado independiente.
    """
    validacion_salida = validar_salida_checklist(
        resultado_externo, turno_preparado
    )

    if not isinstance(
        validacion_salida, dict
    ) or not isinstance(
        validacion_salida.get("permitido"), bool
    ):
        return respuesta_error(
            "No se ha podido validar la salida del checklist.",
            [
                "El validador de salida devolvió una "
                "estructura no válida."
            ],
        )

    if not validacion_salida["permitido"]:
        _registrar_evento_seguridad(
            estado, validacion_salida, "checklist"
        )

        return crear_respuesta_controlada(
            validacion_salida, modelo_invocado=True
        )

    return respuesta_ok(
        "Checklist generado",
        {
            "checklist": deepcopy(resultado_externo),
            "dia_onboarding": (
                turno_preparado.get("dia_onboarding")
                if isinstance(turno_preparado, dict)
                else None
            ),
            "llamar_modelo": False,
            "modelo_invocado": True,
        },
    )


def finalizar_turno_seguro(
    estado: dict,
    turno_preparado: dict,
    resultado_externo: dict,
) -> dict:
    """
    Punto de finalización normal y seguro del producto.

    Antes de persistir la respuesta:
    1. valida la estructura y el contenido;
    2. comprueba posibles fugas de información;
    3. verifica las fuentes respecto al contexto del turno;
    4. bloquea una salida insegura;
    5. reutiliza finalizar_turno() cuando la salida es válida.

    Esta función presupone que el modelo ya fue invocado. Por ello,
    un bloqueo de salida devuelve modelo_invocado=True.
    """
    validacion_salida = validar_salida_segura(
        resultado_externo,
        turno_preparado,
    )

    if not isinstance(
        validacion_salida,
        dict,
    ) or not isinstance(
        validacion_salida.get("permitido"),
        bool,
    ):
        return respuesta_error(
            "No se ha podido validar la salida.",
            [
                "El validador de salida devolvió "
                "una estructura no válida."
            ],
        )

    if not validacion_salida["permitido"]:
        consulta = (
            turno_preparado.get(
                "consulta",
                "",
            )
            if isinstance(
                turno_preparado,
                dict,
            )
            else ""
        )

        _registrar_evento_seguridad(
            estado,
            validacion_salida,
            consulta,
        )

        return crear_respuesta_controlada(
            validacion_salida,
            modelo_invocado=True,
        )

    resultado = finalizar_turno(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )

    if resultado.get("status") == "ok":
        resultado.setdefault(
            "data",
            {},
        )["modelo_invocado"] = True

    return resultado

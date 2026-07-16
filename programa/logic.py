
import re
from copy import deepcopy
from datetime import date
from typing import Any

from config import (
    ASSISTANT_CONFIG_DEFAULT,
    DOMAIN_KEYWORDS,
    MAX_CONTEXT_DOCUMENTS,
    MAX_CONTEXT_FAQS,
    MODO_SEGURIDAD_DEFAULT,
    MODOS_SEGURIDAD,
    ONBOARDING_PROFILE_DAYS,
    PERFILES,
    VALID_CATEGORIES,
    VALID_PROFILES,
)

from validators import (
    validar_contexto_seguro,
    validar_entrada_segura,
    validar_salida_segura,
)

from context import construir_contexto, normalizar_texto
from state import append_assistant, append_user, ultimos_n


# ============================================================
# RESPUESTAS ESTÁNDAR
# ============================================================

def respuesta_ok(
    mensaje: str,
    data: dict | None = None,
) -> dict:
    """
    Construye la respuesta estándar de éxito.
    """
    return {
        "status": "ok",
        "mensaje": mensaje,
        "data": data or {},
    }


def respuesta_error(
    mensaje: str,
    errores: list[str],
) -> dict:
    """
    Construye la respuesta estándar de error.
    """
    return {
        "status": "error",
        "mensaje": mensaje,
        "data": {
            "errores": errores,
        },
    }


# ============================================================
# VALIDACIONES DE ARQUITECTURA
# ============================================================

def _validar_estado(estado: Any) -> None:
    """
    Valida la estructura mínima del estado conversacional.
    """
    if not isinstance(estado, dict):
        raise TypeError(
            "El estado debe ser un diccionario."
        )

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

    Las validaciones de seguridad y robustez no corresponden
    a este módulo.
    """
    if not isinstance(consulta, str):
        raise TypeError(
            "La consulta debe ser un string."
        )

    consulta_limpia = consulta.strip()

    if not consulta_limpia:
        raise ValueError(
            "La consulta no puede estar vacía."
        )

    return consulta_limpia


def _validar_diccionario(
    valor: Any,
    nombre: str,
) -> dict:
    """
    Comprueba que un valor sea un diccionario.
    """
    if not isinstance(valor, dict):
        raise TypeError(
            f"{nombre} debe ser un diccionario."
        )

    return valor


def _validar_lista(
    valor: Any,
    nombre: str,
) -> list:
    """
    Comprueba que un valor sea una lista.

    La validación específica de documentos y FAQ corresponde
    a context.py.
    """
    if not isinstance(valor, list):
        raise TypeError(
            f"{nombre} debe ser una lista."
        )

    return valor


def _validar_entero_no_negativo(
    valor: Any,
    nombre: str,
) -> int:
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
    if configuracion is not None and not isinstance(
        configuracion,
        dict,
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
            "idioma_respuesta debe ser un string no vacío."
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
            "max_palabras debe ser un entero positivo."
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

    fecha_inicio_limpia = fecha_inicio_raw.strip()

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
        expresion_normalizada = normalizar_texto(expresion)

        if not expresion_normalizada:
            continue

        if " " in expresion_normalizada:
            if expresion_normalizada in consulta_normalizada:
                puntuacion += 1
            continue

        patron = (rf"\b{re.escape(expresion_normalizada)}\b")

        if re.search(patron, consulta_normalizada):
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
    consulta_limpia = _validar_consulta(consulta)

    consulta_normalizada = normalizar_texto(consulta_limpia)

    puntuaciones: list[tuple[int, int, str]] = []

    for posicion, (
        categoria,
        expresiones,
    ) in enumerate(DOMAIN_KEYWORDS.items()):
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

    mejor_puntuacion, _, mejor_categoria = max(
        puntuaciones
    )

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
    if categoria_preliminar not in VALID_CATEGORIES:
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

    elif dia_onboarding <= ONBOARDING_PROFILE_DAYS:
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

    Devuelve el paquete de interacción que deberá consumir el
    adaptador implementado por el área LLM y Benchmark.
    """
    try:
        _validar_estado(estado)

        consulta_limpia = _validar_consulta(consulta)

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

        configuracion_final = _resolver_configuracion(configuracion)

        dia_onboarding = calcular_dia_onboarding(
            empleado=empleado_validado,
            fecha_referencia=fecha_referencia,
        )

        categoria_preliminar = clasificar_consulta(consulta_limpia)

        perfil_activo = seleccionar_perfil(
            categoria_preliminar=categoria_preliminar,
            dia_onboarding=dia_onboarding,
        )

        configuracion_final["perfil_activo"] = (perfil_activo)

        limite_documentos = configuracion_final["max_documentos_contexto"]

        limite_faqs = configuracion_final["max_faqs_contexto"]

        contexto = construir_contexto(
            consulta=consulta_limpia,
            empleado=empleado_validado,
            documentos=documentos_validados,
            faqs=faqs_validadas,
            limite_documentos=limite_documentos,
            limite_faqs=limite_faqs,
        )

        ventana_historial = configuracion_final["max_turnos_historial"]

        historial = ultimos_n(estado, ventana_historial,)

        turno_preparado = {
            "consulta": consulta_limpia,
            "empleado": deepcopy(empleado_validado),
            "empresa": deepcopy(empresa_validada),
            "perfil_activo": perfil_activo,
            "perfil": deepcopy(PERFILES[perfil_activo]),
            "categoria_preliminar": (categoria_preliminar),
            "dia_onboarding": dia_onboarding,
            "contexto": deepcopy(contexto),
            "historial": deepcopy(historial),
            "configuracion": deepcopy(configuracion_final),
        }

    except (TypeError, ValueError) as error:
        return respuesta_error(
            "No se ha podido preparar el turno.",
            [str(error)],
        )

    return respuesta_ok(
        "Turno preparado",
        {
            "turno_preparado": turno_preparado,
        },
    )


# ============================================================
# FINALIZACIÓN DEL TURNO
# ============================================================

def _validar_turno_preparado(
    turno_preparado: Any,
) -> dict:
    """
    Valida la estructura mínima necesaria para finalizar el turno.
    """
    if not isinstance(turno_preparado, dict):
        raise TypeError(
            "El turno preparado debe ser un diccionario."
        )

    campos_requeridos = {
        "consulta",
        "perfil_activo",
        "categoria_preliminar",
        "dia_onboarding",
    }

    campos_ausentes = campos_requeridos.difference(turno_preparado)

    if campos_ausentes:
        campos = ", ".join(sorted(campos_ausentes))

        raise ValueError(
            "Faltan campos obligatorios en el turno "
            f"preparado: {campos}."
        )

    consulta = turno_preparado.get("consulta")

    _validar_consulta(consulta)

    perfil_activo = turno_preparado.get("perfil_activo")

    if perfil_activo not in VALID_PROFILES:
        raise ValueError(
            f"Perfil activo desconocido: "
            f"{perfil_activo!r}."
        )

    categoria = turno_preparado.get("categoria_preliminar")

    if categoria not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoría preliminar desconocida: "
            f"{categoria!r}."
        )

    dia_onboarding = turno_preparado.get("dia_onboarding")

    if (
        not isinstance(dia_onboarding, int)
        or isinstance(dia_onboarding, bool)
        or dia_onboarding < 1
    ):
        raise ValueError(
            "El día de onboarding del turno preparado "
            "debe ser un entero igual o superior a 1."
        )

    return turno_preparado


def _validar_resultado_externo(
    resultado_externo: Any,
) -> dict:
    """
    Valida el contrato mínimo de la respuesta externa.

    La validación completa del formato generado corresponde al
    área LLM y Benchmark.
    """
    if not isinstance(resultado_externo, dict):
        raise TypeError("El resultado externo debe ser un diccionario.")

    campos_requeridos = {
        "in_scope",
        "category",
        "answer",
    }

    campos_ausentes = campos_requeridos.difference(resultado_externo)

    if campos_ausentes:
        campos = ", ".join(sorted(campos_ausentes))

        raise ValueError(
            "Faltan campos obligatorios en el resultado "
            f"externo: {campos}."
        )

    in_scope = resultado_externo.get("in_scope")

    if not isinstance(in_scope, bool):
        raise ValueError("El campo 'in_scope' debe ser booleano.")

    categoria = resultado_externo.get("category")

    if categoria not in VALID_CATEGORIES:
        raise ValueError(
            f"Categoría externa desconocida: "
            f"{categoria!r}."
        )

    respuesta = resultado_externo.get("answer")

    if not isinstance(respuesta, str):
        raise ValueError("El campo 'answer' debe ser un string.")

    if not respuesta.strip():
        raise ValueError("El campo 'answer' no puede estar vacío.")

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
    """
    try:
        _validar_estado(estado)

        turno_validado = _validar_turno_preparado(turno_preparado)

        resultado_validado = _validar_resultado_externo(resultado_externo)

        consulta = turno_validado["consulta"]

        respuesta = resultado_validado["answer"].strip()

        append_user(estado, consulta,)

        append_assistant(estado, respuesta,)

    except (TypeError, ValueError) as error:
        return respuesta_error(
            "No se ha podido finalizar el turno.",
            [str(error)],
        )

    return respuesta_ok(
        "Turno finalizado",
        {
            "respuesta": respuesta,
            "resultado": deepcopy(resultado_validado),
            "perfil_activo": turno_validado["perfil_activo"],
            "categoria": resultado_validado["category"],
            "categoria_preliminar": turno_validado["categoria_preliminar"],
            "dia_onboarding": turno_validado["dia_onboarding"],
        },
    )


# ============================================================
# ROBUSTEZ Y SEGURIDAD
# ============================================================

# añade al diccionario del estado los "eventos_seguridad"
def _registrar_evento_seguridad(
    estado: dict,
    validacion: dict,   # resultado devuelto por las funciones validar_entrada_segura() | validar_contexto_seguro() | validar_salida_segura()
    consulta: Any,      # input del usuario
) -> None:
    """
    Registra metadatos mínimos sin conservar el ataque completo.

    Esta lista no forma parte de state["messages"] y, por tanto,
    nunca entra en el historial enviado al modelo.

    Parámetros:
    - estado: diccionario del estado de la sesión
    - validacion: resultado de las funciones `validar_entrada_segura()` |
                  `validar_contexto_seguro()` | `validar_salida_segura()`
    - consulta: input del usuario

    Tiene como objetivo modificar directamente el diccionario del estado.
    """
    if not isinstance(estado, dict):
        return

    # si no existe crea la lista vacía y la devuelve
    # si existe no sustituye, recupera la lista existente
    eventos = estado.setdefault("eventos_seguridad", [],)

    # comprobar que realmente es una lista y si no
    # se reemplaza lo inválido por una lista
    if not isinstance(eventos, list):
        estado["eventos_seguridad"] = []

    longitud_consulta = 0

    # calcula la longitud del input si es una cadena de texto
    if isinstance(consulta, str):
        longitud_consulta = len(consulta)

    # añade el evento a una lista sin guardar el texto del input
    # si es un ataque o introducción de información sensible
    # se evita guardarlo
    eventos.append(
        {
            "fase": validacion.get("fase"),
            "codigo": validacion.get("codigo"),
            "longitud_consulta": longitud_consulta,
        }
    )

    # Evita que el registro crezca sin límite almacenando los últimos 20.
    estado["eventos_seguridad"] = eventos[-20:]


# RESPUESTAS CONTROLADAS DE SEGURIDAD
# ============================================================

# después de un bloqueo es necesario generar la respuesta para el usuario
# se adapta aquí el diccionario que generan las funciones de validaciones
# al diccionario que espera recibir `main.py`

def crear_respuesta_controlada(
    validacion: dict,
    modo_seguridad: str,
    modelo_invocado: bool = False,
) -> dict:
    """
    Adapta el resultado interno de las validaciones al contrato estándar
    de logic.py, para que pueda ser procesado por imprimir_respuesta_final().

    Un input bloqueado es una respuesta funcional, no un error técnico.
    Por eso la wrapper del modo seguro mantiene status="ok", pero
    llamar_modelo=False para impedir que el flujo siga y se produzca
    la llamada al modelo.

    Args:
        - validacion: resultado producido por las funciones de validación
                      validar_respuesta_segura() | validar_contexto_seguro() | validar_salida_segura()

        - modo_seguridad: modo activo al producirse la respuesta
                          seguro | vulnerable

        - modelo_invocado: indica si el modelo se ha invocado antes del bloqueo
                           por defecto `False`. Los bloqueos deben producirse antes

    Devuelve un diccionario con el contrato estándar.
    No modifica directamente el estado.

    """

    # status:ok -> un bloqueo de seguridad es un comportamiento esperado
    return respuesta_ok(
        "Consulta atendida de forma controlada.",
        {
            # texto que verá el usuario
            "respuesta": validacion["mensaje_usuario"],
            # indica a main.py que el flujo se detiene antes de la llamada
            "llamar_modelo": False,
            "modelo_invocado": modelo_invocado,         # True si llamada
            "modo_seguridad": modo_seguridad,           # modo que estaba activo
            # se guarda el ID de rechazo
            "motivo_bloqueo": validacion["codigo"],
        },
    )

# ORQUESTADOR DE CUALQUIER MODO (SEGURO | VULNERABLE)
# ============================================================

# Envuelve preparar_turno() para añadir controles de seguridad
# antes y después, sin duplicar la lógica ya existente.

# Le añade:
# - Selección de modo
# - validación de entrada y contexto
# - autorización para llamar al modelo


def preparar_turno_con_modo(
    estado: dict,
    consulta: str,
    empleado: dict,
    empresa: dict,
    documentos: list[dict],
    faqs: list[dict],
    configuracion: dict | None = None,
    fecha_referencia: date | None = None,
    modo_seguridad: str = MODO_SEGURIDAD_DEFAULT,
) -> dict:
    """
    Envuelve preparar_turno() sin duplicar su lógica.

    Args:
        estado:
            El estado de la sesión.
        consulta:
            input del usuario.
        empleado | empresa | documentos | faqs:
            datos necesarios para el perfil, cálculo de día
            selección de documentación y construcción de
            contexto.
        configuracion:
            usar la default o una parcial.
        fecha_referencia:
            principalmente para pruebas. Si `None` se usa la
            fecha actual.
            date(yyyy, m, d)
        modo_seguridad:
            qué flujo va a ejecutar ("seguro" | "vulnerable")
            por defecto el más restrictivo: seguro.

    Modo seguro:
    1. valida el input;
    2. prepara el turno sin LLM;
    3. valida el contexto;
    4. autoriza o bloquea la futura llamada.

    Modo vulnerable:
    conserva las validaciones estructurales de preparar_turno(),
    pero omite las defensas de seguridad a propósito.

    Puede devolver:
    - Error estructural
    - Respuesta bloqueada
    - Turno autorizado -> "llamar_modelo": True
    """

    # comprobar modo
    if modo_seguridad not in MODOS_SEGURIDAD:
        return respuesta_error(
            "Modo de seguridad no válido.",
            [f"Modo desconocido: {modo_seguridad!r}."],
        )

    # primera validación
    if modo_seguridad == "seguro":
        validacion_entrada = validar_entrada_segura(consulta)

        # si no se autoriza
        if not validacion_entrada["permitido"]:
            _registrar_evento_seguridad(
                estado=estado,
                validacion=validacion_entrada,
                consulta=consulta,
            )

            return crear_respuesta_controlada(
                validacion=validacion_entrada,
                modo_seguridad=modo_seguridad,
                modelo_invocado=False,
            )

    # si autoriza (o modo vulnerable)
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

    # si no es OK problema estructural
    if resultado.get("status") != "ok":
        return resultado

    # si todo OK se prepara turno
    turno_preparado = resultado.get("data", {},).get("turno_preparado")

    # segunda validación
    if modo_seguridad == "seguro":
        # si turno preparado no existe será None y se rechazará
        validacion_contexto = validar_contexto_seguro(turno_preparado)

        # si no la permite se registra el rechazo
        if not validacion_contexto["permitido"]:
            _registrar_evento_seguridad(
                estado=estado,
                validacion=validacion_contexto,
                consulta=consulta,
            )

            return crear_respuesta_controlada(
                validacion=validacion_contexto,
                modo_seguridad=modo_seguridad,
                modelo_invocado=False,
            )

    # llega hasta aquí modo vulnerable
    # modo seguro ha pasado todas las validaciones
    # ESTO LE VA A LLEGAR AL MODELO
    resultado["data"]["llamar_modelo"] = True
    resultado["data"]["modelo_invocado"] = False
    resultado["data"]["modo_seguridad"] = (modo_seguridad)

    return resultado


# tercera validación
# ya se ha llamado al modelo y se va a validar su respuesta
# se valida ANTES de guardarla en el historial
def finalizar_turno_con_modo(
    estado: dict,
    turno_preparado: dict,
    resultado_externo: dict,
    modo_seguridad: str = MODO_SEGURIDAD_DEFAULT,
) -> dict:
    """
    Envuelve `finalizar_turno()` para añadir otra capa de seguridad
    antes de guardar el input y la respuesta del modelo en el 
    historial.

    Args:
        estado:
            estado actual de la conversación.
        turno_preparado:
            diccionario producido por `preparar_turno()`
        resultado_externo:
            respuesta generada por el modelo.
            (modo seguro: lo revisa antes de que se guarde)
        modo_seguridad:
            determina si se aplica la validación de salida.
            ("seguro" | "vulnerable") por defecto seguro.

    En modo seguro:
    1. valida la estructura y el contenido de la respuesta.
    2. comprueba que no hay fugas de inforamción.
    3. verifica que las fuentes pertenecen al contexto del turno.
    4. bloquea la respuesta si no es validada.
    5. usa finalizar_turno() cuando la salida es válida.

    En modo vulnerable:
    omite las validaciones y va directamente a `finalizar_turno()`.
    se conservan las validaciones básicas de finalizar_turno().
    """

    # comprobar modo
    if modo_seguridad not in MODOS_SEGURIDAD:
        return respuesta_error(
            "Modo de seguridad no válido.",
            [f"Modo desconocido: {modo_seguridad!r}."],
        )

    # con modo seguro activo se valida la salida
    if modo_seguridad == "seguro":
        validacion_salida = validar_salida_segura(
            resultado_externo=resultado_externo,
            turno_preparado=turno_preparado,
        )

        # si se rechaza la respuesta del modelo
        # no se ejecuta finalizar_turno()
        if not validacion_salida["permitido"]:
            consulta = turno_preparado.get("consulta", "",)

            _registrar_evento_seguridad(
                estado=estado,
                validacion=validacion_salida,
                consulta=consulta,
            )

            return crear_respuesta_controlada(
                validacion=validacion_salida,
                modo_seguridad=modo_seguridad,
                modelo_invocado=True,
            )

    # se llega directamente en modo vulnerable
    # se ha superado la validación de la respuesta
    return finalizar_turno(
        estado=estado,
        turno_preparado=turno_preparado,
        resultado_externo=resultado_externo,
    )

# ============================================================
# LLM Y BENCHMARK — ELIMINADO DE LA ARQUITECTURA BASE
# ============================================================

# Punto de integración previsto:
#
# turno = preparar_turno(...)
# resultado_externo = adaptador_llm(
#     turno["data"]["turno_preparado"]
# )
# resultado = finalizar_turno(
#     estado,
#     turno["data"]["turno_preparado"],
#     resultado_externo,
# )
#
# El área LLM y Benchmark deberá implementar:
#
# - Construcción del prompt.
# - Selección del modelo.
# - Selección de temperatura.
# - Llamada al proveedor.
# - Control de tokens.
# - Generación estructurada.
# - Métricas y benchmarking.


# ============================================================
# ROBUSTEZ — ELIMINADO DE LA ARQUITECTURA BASE
# ============================================================

# El área de Robustez podrá intervenir antes del adaptador LLM
# o envolver el flujo completo sin duplicar este archivo.
#
# No deben crearse variantes como:
#
# - logic_seguro.py
# - logic_vulnerable.py
#
# Las variantes deberán reutilizar preparar_turno() y
# finalizar_turno() mediante funciones, adaptadores o estrategias.

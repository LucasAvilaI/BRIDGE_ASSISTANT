
import re
import unicodedata
from typing import Any
from config import (
    DOMAIN_KEYWORDS,
    FIRMAS_INYECCION_COMPACTAS,
    MAX_INPUT_CHARS,
    MAX_SAFE_OUTPUT_CHARS,
    MENSAJES_SEGURIDAD,
    # Necesarios para middleware en validators que gestiona activación de modos:
    MODO_SEGURIDAD_DEFAULT,
    MODOS_SEGURIDAD,
    PATRONES_INCIDENCIA_CREDENCIALES,
    PATRONES_SOLICITUD_SECRETOS,
    PATRONES_DOMINIO_ADICIONALES,
    PATRONES_FUERA_DE_DOMINIO,
    PATRONES_FUGA_SALIDA,
    PATRONES_INYECCION,
    PATRONES_REFERENCIA_INTERNA,
    PATRONES_SENSIBLES_POR_CODIGO,
    TERMINOS_POCO_INFORMATIVOS_SEGURIDAD,
    VALID_CATEGORIES
)
from context import STOPWORDS

# NORMALIZAR TEXTOS SEGURO
# retirar espacios, todo en minúsculas, sin tildes...
def normalizar_texto_seguridad(texto: str) -> str:
    """
    Normaliza mayúsculas, Unicode, acentos y separadores.

    NFKC reduce variantes visuales compatibles y NFKD permite
    eliminar los acentos antes de comparar patrones.
    """

    # uniformiza todos los caracteres
    # caracteres copiados de editores de texto como word
    # paginas web...
    # se pueden utilizar otro tipo de caracteres para engañar al modelo
    # así unificamos los caracteres que van a llegar a la llamada
    texto_normalizado = unicodedata.normalize("NFKC", texto)

    # separa caracter del tipo de acento que lleve
    texto_normalizado = unicodedata.normalize("NFKD", texto_normalizado)

    # recorre caracter por caracter y si es del tipo "Mn" lo descarta (`, ´, ¨, ~)
    texto_normalizado = "".join(
        caracter
        for caracter in texto_normalizado
        if unicodedata.category(caracter) != "Mn"
    )

    # casefold() más agresiva que lower()
    texto_normalizado = texto_normalizado.casefold()

    # sustituye (_, /, \, -) por un espacio
    texto_normalizado = re.sub(r"[_/\\-]+", " ", texto_normalizado)

    # si hay más de un espacio lo sustituye por solo uno
    return re.sub(r"\s+", " ", texto_normalizado).strip()

# ============================================================
# FUNCIONES AUXILIARES DE ROBUSTEZ
# ============================================================

# Funciones de apoyo para las validaciones:
# - validar_entrada_segura()
# - validar_contexto_seguro()
# - validar_salida_segura()
# Son de uso interno de validators.py

# debe usarse para comprobar ciertas firmas compactas
def _compactar_texto(texto: str) -> str:
    """
    Elimina separadores para detectar palabras fragmentadas.
        "i g n o r a"  -> "ignora"
        "system-prompt" -> "systemprompt"
    Esta representación compacta solo se utiliza para comparar
    firmas de inyección. No sustituye al texto normalizado general.
    """

    # elimina todo aquello que no sea letra o número
    return re.sub(r"[^a-z0-9]+", "", normalizar_texto_seguridad(texto))

# Para revisar grupos de patrones de: INYECCION, FUERA_DE_DOMINIO
# FUGA_SALIDA, REFERENCIA_INTERNA, SENSIBLES_POR_CODIGO
def _coincide_algun_patron(texto_normalizado: str, patrones: tuple[str, ...]) -> bool:
    """
    Devuelve True al encontrar al menos un patrón, False si no detecta ninguno.
    El texto haberse normalizado previamente con normalizar_texto_seguridad()
    """
    # si hay objeto Match -> True, si hay None -> False
    # si hay una coincidencia devuelve un objeto Match
    # IGNORECASE ignora mayúsculas
    # DOTALL abarca también saltos de línea
    return any( 
        re.search(patron, texto_normalizado, flags=re.IGNORECASE | re.DOTALL)
        for patron in patrones
    )

# garantiza que todas las validaciones tengan la misma estructura
# logic.py puede trabajar del mismo modo con cualquier validación
def _resultado_validacion(permitido: bool, codigo: str, fase: str) -> dict:
    """
    Crea el contrato común de las validaciones.
    Toda la seguridad devuelve las mismas claves:
    - permitido: indica si el flujo puede continuar
    - codigo: identifica el resultado o motivo del bloqueo
    - fase: indica si es input, contexto, salida
    - mensaje_usuario: respuesta fija cuando hay bloqueo 

    Si la validación es correcta mensaje_usuario queda vacío. 
    Si se bloquea, el mensaje se obtiene de MENSAJES_SEGURIDAD en config.py
    """
    mensaje_usuario = ""

    if not permitido:
        # Cada código de rechazo debe existir como key en MENSAJES_SEGURIDAD
        # Si no existe KeyError y romperá el código, revelando un fallo de programación.
        mensaje_usuario = MENSAJES_SEGURIDAD[codigo] 

    return {
        "permitido": permitido,
        "codigo": codigo,
        "fase": fase,
        "mensaje_usuario": mensaje_usuario
    }

# ============================================================
# PRIMERA VALIDACION - VALIDACION DE INPUT
# ============================================================
# Decide si la entrada del usuario se da por válida.
# No construye prompt ni llama al modelo.
# Puede recibir cualquier tipo de dato (texto: Any) ya que debe
# comprobar en primer lugar si lo que recibe como input es una string
def validar_entrada_segura(texto: Any) -> dict:
    """
    Primera puerta del modo seguro.

    No llama a context.py, al cliente Gemini ni a count_tokens().

    Analiza el mensaje original del usuario antes de preparar_turno()
    o de realizar la llamada al modelo.

    Orden de comprobación:

    1. La entrada es un string
    2. No está vacía
    3. No supera la longitud máxima
    4. No contiene caracteres de control no permitidos
    5. No contiene intento de prompt injection
    6. No solicita información sensible
    7. No es una consulta fuera del dominio
    8. No contiene solicitud ambigua

    Devuelve el primer motivo de incumplimiento detectado en un diccionario:
        {
            "permitido": bool,
            "codigo": str,
            "fase": "input",
            "mensaje_usuario": str,
        }
    
    Si permitido es False el flujo se detiene. Si es True continua hacia preparar_turno().
    """

    # si no es string
    if not isinstance(texto, str):
        # nos genera el diccionario
        return _resultado_validacion(False, "invalid_type", "input")

    texto_limpio = texto.strip()

    # si es una string pero no hay texto (está vacía)
    if not texto_limpio:
        return _resultado_validacion(False, "empty", "input")

    # si excede el límite de caracteres permitidos
    if len(texto_limpio) > MAX_INPUT_CHARS:
        return _resultado_validacion(False, "too_long", "input")

    # comprueba si hay caracteres no permitidos
    # codigo ASCII inferior a 32 incluye caracteres no deseados
    # como escape, retroceso, tabulacion...
    # pueden usarse accidental o maliciosamente
    contiene_control_no_permitido = any(
        # devuelve el numero Unicode y comprueba si es menor de 32
        ord(caracter) < 32
        and caracter not in "\n\r\t" # \n salto linea | \r retorno de carro | \t tabulacion
        for caracter in texto_limpio
    )

    # si hay caracteres no permitidos bloquea
    if contiene_control_no_permitido:
        return _resultado_validacion(False, "invalid_characters", "input")

    # preparación de texto para los patrones REGEX
    texto_normalizado = normalizar_texto_seguridad(texto_limpio)

    # versión compacta para ciertos casos
    texto_compacto = _compactar_texto(texto_limpio)

    # True | False
    hay_inyeccion = _coincide_algun_patron(texto_normalizado, PATRONES_INYECCION)

    # True | False
    hay_firma_compacta = any(firma in texto_compacto for firma in FIRMAS_INYECCION_COMPACTAS)

    # si detecta cualquiera de los dos casos anteriores bloquea
    if hay_inyeccion or hay_firma_compacta:
        return _resultado_validacion(False, "prompt_injection", "input")

    # Comprueba si el usuario está solicitando que se revele,
    # entregue, copie o muestre directamente algún secreto.
    hay_solicitud_secretos = _coincide_algun_patron(texto_normalizado, PATRONES_SOLICITUD_SECRETOS)

    # La solicitud explícita de un secreto siempre se bloquea,
    # aunque también contenga vocabulario propio de una incidencia.
    if hay_solicitud_secretos:
        return _resultado_validacion(False, "credentials", "input")

    # El orden determina la causa prioritaria del rechazo.
    # detectar si hay o se quiere información sensible
    for codigo, patrones in PATRONES_SENSIBLES_POR_CODIGO.items():
        if codigo == "credentials":
            continue
        if _coincide_algun_patron(texto_normalizado,patrones):     # tupla que contiene los patrones para cada caso
            return _resultado_validacion(False, codigo, "input")   # si alguno coincide bloquea
            

    if _coincide_algun_patron(texto_normalizado,PATRONES_FUERA_DE_DOMINIO):
        return _resultado_validacion(False, "external_participant", "input")

    # "Baja" sin especificar el tipo no debe mezclar los dos
    # procedimientos existentes en doc_rrhh_03.
    # comprueba si en el input se menciona "baja"
    menciona_baja = bool(re.search(r"\bbaja\b", texto_normalizado))

    # si hay ciertas referencias a procedimientos con una baja
    solicita_proceso_baja = _coincide_algun_patron(
        texto_normalizado,
        (
            (
                r"\b(pedir|solicitar|tramitar|notificar|comunicar)\b"
                r".{0,60}\bbaja\b"
            ),
            (
                r"\bbaja\b.{0,60}\b(formulario|proceso|tramite|pedir|"
                r"solicitar|tramitar|notificar|comunicar)\b"
            )
        )
    )

    # comprueba si se especifica el tipo de baja
    especifica_tipo_baja = bool(
            re.search(
                (
                    r"\b(medica|enfermedad|incapacidad|excedencia|"
                    r"laboral|voluntaria|contrato)\b"
                ),
                texto_normalizado
            )
    )


    # si no especifica el tipo se rechaza por ambigüedad
    if (
        menciona_baja
        and solicita_proceso_baja
        and not especifica_tipo_baja
    ):
        return _resultado_validacion(False, "ambiguous_leave", "input")

    # si nada bloquea se devuelve el diccionario
    return _resultado_validacion(True, "valid_input", "input")

# ============================================================
# FUNCIONES AUXILIARES DE VALIDACION DOCUMENTAL
# ============================================================

# Preparan input con las data que hay como fuente de información
# para validar si hay suficiente respaldo documental.

# No seleccionan documentos.
# No llaman al modelo.
# Principalmente usadas por validar_contexto_seguro()

# determina si el input forma parte del dominio o no
def _contiene_senal_de_dominio(consulta: str) -> bool:
    """
    Usa las señales declaradas en config.py.
    
    Ante la primera coincidencia frente a todo lo definido
    en config.py devuelve True.

    Solamente comprueba que el input esté dentro del dominio.
    """

    consulta_normalizada = normalizar_texto_seguridad(consulta)


    if _coincide_algun_patron(consulta_normalizada, PATRONES_DOMINIO_ADICIONALES):
        return True

    for expresiones in DOMAIN_KEYWORDS.values(): # diccionario que cada clave tiene una tupla
        for expresion in expresiones: # recorre los elementos de la tupla
            expresion_normalizada = (normalizar_texto_seguridad(expresion)) # la normaliza

            # puede haber algún error y que haya una expresión vacía
            if not expresion_normalizada:
                continue
            
            # si tiene más de una palabra comprueba si la contiene la consulta
            # si no, sigue
            if " " in expresion_normalizada:
                if expresion_normalizada in consulta_normalizada:
                    return True
                continue
            
            # escapa los caracteres significantes dentro de un patrón regex
            patron = rf"\b{re.escape(expresion_normalizada)}\b"

            # así la expresión de config.py se puede utilizar del mismo modo
            # si encuentra coincidencia en ambas True
            if re.search(patron, consulta_normalizada):
                return True

    return False

# doc o FAQ de la que extraerá información
# nombres de los campos que interesa extraer
def _texto_de_campos(elemento: dict, campos: tuple[str, ...]) -> str:
    """Convierte campos de texto y listas en un solo string."""
    fragmentos: list[str] = []

    for campo in campos:
        valor = elemento.get(campo, "")

        if isinstance(valor, list): # algunos campos como tags son una lista
            fragmentos.extend(str(parte) for parte in valor)
        elif valor:
            fragmentos.append(str(valor))

    # une todos los fragmentos utilizando un espacio
    return " ".join(fragmentos)

# Procesa las fuentes que construir_contexto() ha seleccionado -> context.py
def _texto_del_contexto(contexto: dict) -> str:
    """Agrupa únicamente las fuentes seleccionadas para el turno."""
    fragmentos: list[str] = []

    # de todo el contexto se queda lo que hay en "documentos"
    # recorre la lista que son diccionarios 
    for documento in contexto.get("documentos", []):
        if isinstance(documento, dict):
            fragmentos.append(
                _texto_de_campos(
                    documento,
                    (
                        "id",
                        "titulo",
                        "departamento",
                        "tags",
                        "cuerpo"
                    )
                )
            )

    # aquí se queda lo que hay en "faqs"
    # recorre la lista que son diccionarios
    for faq in contexto.get("faqs", [], ):
        if isinstance(faq, dict):
            fragmentos.append(
                _texto_de_campos(
                    faq,
                    (
                        "id",
                        "pregunta",
                        "respuesta_corta",
                        "tags",
                        "doc_id"
                    )
                )
            )

    # una vez añadidos toda la documentación a la lista fragmentos
    # se unifican todas las cadenas de texto en una sola
    # se normaliza el texto con la primera función de este módulo
    return normalizar_texto_seguridad(" ".join(fragmentos))

# no todas las palabras sirven para seleccionar los documentos
# elimina las palabras demasiado genéricas
def _terminos_significativos(texto: str) -> set[str]:
    """
    Extrae términos útiles para comprobar apoyo documental.
    
    Normaliza el texto, elimina duplicados, descarta palabras
    de uso frecuente, retira términos demasiado generales.

    Devuelve un set() para facilitar la intersección entre
    los términos útiles del input y los de las fuentes.
    """

    # busca todas aquellas palabras que empiecen por:
    # cualquier letra minúscula o número y tengan 2 o + caracteres
    palabras = set(
        re.findall(r"\b[a-z0-9]{2,}\b", normalizar_texto_seguridad(texto)) # lo hace con el texto normalizado
    )

    # el set() evita duplicidades
    # permite además operar eliminando aquello que esté en uno y en otro
    # primero quita lo que hay en STOPWORDS y luego en TERMINOS_POCO_INFORMATIVOS_SEGURIDAD
    return (
        palabras
        .difference(STOPWORDS)
        .difference(TERMINOS_POCO_INFORMATIVOS_SEGURIDAD)
    )


# ============================================================
# SEGUNDA VALIDACION - VALIDACION DE CONTEXTO
# ============================================================

# Valida si hay suficiente contexto entre los documentos onboarding y faq
# Se ejecuta después de preparar_turno(), pero antes de construir el prompt.
# preparar_turno() ya ha seleccionado los documentos y se hace una comprobación adicional

# Recibe el diccionario generado por preparar_turno()
# Utiliza principalmente las key: "consulta" y "contexto"

def validar_contexto_seguro(turno_preparado: Any) -> dict:
    """
    Segunda validación del modo seguro.

    Se ejecuta después de preparar_turno(), pero siempre antes
    de la preparación del prompt y la llamada al modelo.

    Distingue entre tres resultados:
    - "documented": existen fuentes y documentos que respaldan
    - "undocumented": pertenece al dominio pero no hay suficiente
                      respaldo documental
    - "out_of_scope": input fuera de dominio

    Solo si "documented" sigue adelante para preparar prompt y
    llamar al modelo.
    """

    # comprueba que lo que recibe es un diccionario
    if not isinstance(turno_preparado, dict):
        return _resultado_validacion(False, "invalid_context", "context") # ahora context porque es la segunda capa de validaciones

    # input del usuario
    consulta = turno_preparado.get("consulta")

    # documentos y faq seleccionados
    contexto = turno_preparado.get("contexto")

    # comprueba simultaneamente que el input sea cadena de texto
    # y el contexto un diccionario
    if not isinstance(consulta, str) or not isinstance(contexto, dict):
        return _resultado_validacion(False, "invalid_context", "context")

    # normaliza el input
    consulta_normalizada = normalizar_texto_seguridad(consulta)

    # comprueba si hay referencia a cosas internas (aunque no estén documentadas)
    referencia_interna = _coincide_algun_patron(consulta_normalizada, PATRONES_REFERENCIA_INTERNA)

    # comprueba si forma parte del dominio
    senal_dominio = _contiene_senal_de_dominio(consulta)

    # la función contruir_contexto() en context.py construye "hay_contexto"
    if not contexto.get("hay_contexto"):
        codigo = "out_of_scope"

        # si no hay contexto pero sí es un input admisible
        if referencia_interna or senal_dominio:
            codigo = "undocumented"

        return _resultado_validacion(False, codigo, "context")

    # si llega hasta aquí es porque hay contexto y documentos
    # quedarse con los términos relevantes
    terminos_consulta = _terminos_significativos(consulta)

    # unir contexto en una sola string
    # quedarse con los términos relevantes
    terminos_fuentes = _terminos_significativos(_texto_del_contexto(contexto))

    # coger las coincidencias
    coincidencias = terminos_consulta.intersection(terminos_fuentes)

    consulta_cubierta = bool(
        coincidencias # si hay algo es True
        or (
            senal_dominio
            and not terminos_consulta
        )
    )

    if consulta_cubierta:
        resultado = _resultado_validacion(True, "documented", "context")

        # Solo para pruebas o logging interno; no se imprime.
        resultado["coincidencias"] = sorted(coincidencias)

        return resultado

    # pero si no se ha encontrado ninguna coincidencia
    codigo = "out_of_scope"

    if referencia_interna or senal_dominio:
        codigo = "undocumented"

    return _resultado_validacion(False, codigo, "context")

# ============================================================
# VALIDACIÓN ESTRUCTURAL DE LA RESPUESTA DEL MODELO
# ============================================================

def validar_respuesta_estructurada(resultado_externo: Any) -> dict:
    """
    Comprueba que la respuesta externa cumple el contrato JSON
    esperado para el chat.

    Esta función valida:

    - que la respuesta sea un diccionario
    - que estén presentes todos los campos obligatorios
    - que no existan campos adicionales
    - que cada campo tenga el tipo correcto
    - que la categoría sea válida
    - que la escalación sea coherente

    No comprueba todavía:

    - si los documentos citados estaban autorizados
    - si la respuesta contiene una fuga de información
    - si el contenido está respaldado documentalmente

    Esas comprobaciones corresponden a validar_salida_segura().

    Devuelve:
        {
            "valido": bool,
            "errores": list[str]
        }
    """

    errores: list[str] = []

    # Contrato exacto que debe devolver el modelo.
    campos_esperados = {
        "in_scope",
        "category",
        "answer",
        "document_ids",
        "faq_ids",
        "needs_escalation",
        "escalation_department"
    }

    # La respuesta del modelo debe haberse convertido previamente
    # desde JSON a un diccionario de Python.
    if not isinstance(resultado_externo, dict):
        return {
            "valido": False,
            "errores": ["La respuesta externa debe ser un diccionario."]
        }

    campos_recibidos = set(resultado_externo.keys())

    campos_ausentes = (campos_esperados- campos_recibidos)

    campos_adicionales = (campos_recibidos- campos_esperados)

    if campos_ausentes:
        errores.append("Faltan campos obligatorios: " + ", ".join(sorted(campos_ausentes)) + ".")

    if campos_adicionales:
        errores.append("Se han recibido campos no permitidos: " + ", ".join(sorted(campos_adicionales)) + ".")

    # Si faltan campos, no se accede directamente mediante []
    # para evitar KeyError. Se utiliza get() en todas las
    # comprobaciones posteriores.
    in_scope = resultado_externo.get("in_scope")

    if not isinstance(in_scope, bool):
        errores.append("'in_scope' debe ser booleano.")

    categoria = resultado_externo.get("category")

    if not isinstance(categoria, str):
        errores.append("'category' debe ser un string.")

    elif categoria not in VALID_CATEGORIES:
        errores.append("'category' contiene una categoría no válida.")

    respuesta = resultado_externo.get("answer")

    if not isinstance(respuesta, str):
        errores.append("'answer' debe ser un string.")

    elif not respuesta.strip():
        errores.append("'answer' no puede estar vacío.")

    document_ids = resultado_externo.get("document_ids")

    if not isinstance(document_ids, list):
        errores.append("'document_ids' debe ser una lista.")

    elif not all(
        isinstance(documento_id, str)
        and documento_id.strip()
        for documento_id in document_ids
    ):
        errores.append("'document_ids' solo puede contener strings no vacíos.")

    faq_ids = resultado_externo.get("faq_ids")

    if not isinstance(faq_ids, list):
        errores.append("'faq_ids' debe ser una lista.")

    elif not all(
        isinstance(faq_id, str)
        and faq_id.strip()
        for faq_id in faq_ids
    ):
        errores.append("'faq_ids' solo puede contener strings no vacíos.")

    necesita_escalacion = resultado_externo.get("needs_escalation")

    if not isinstance(necesita_escalacion, bool):
        errores.append("'needs_escalation' debe ser booleano.")

    departamento_escalacion = resultado_externo.get("escalation_department")

    if departamento_escalacion is not None and not isinstance(departamento_escalacion, str):
        errores.append("'escalation_department' debe ser un string o None.")

    # Comprobaciones de coherencia entre los dos campos
    # relacionados con la escalación.
    if isinstance(necesita_escalacion, bool):
        if (necesita_escalacion and (not isinstance(departamento_escalacion, str) or not departamento_escalacion.strip())):
            errores.append(
                "Si 'needs_escalation' es True, "
                "'escalation_department' debe indicar "
                "el destino de la escalación."
            )

        if not necesita_escalacion and departamento_escalacion is not None:
            errores.append("Si 'needs_escalation' es False, 'escalation_department' debe ser None.")

    return {
        "valido": not errores,
        "errores": errores
    }


# ============================================================
# TERCERA VALIDACION - VALIDACION DE SALIDA/RESPUESTA
# ============================================================

# Ya se ha llamado al modelo y tiene que validar la respuesta.
# Estructura esperada
# Consulta dentro de dominio
# Categoría válida
# Respuesta de texto válida
# No revela información confidencial
# No cita documentos distintos a los autorizados

def validar_salida_segura(resultado_externo: Any, turno_preparado: Any) -> dict:
    """
    Tercera capa de validación, antes de finalizar_turno().

    Valida la estructura, el contenido y las fuentes declaradas
    de la respuesta del modelo. Antes de guardar la interacción
    en el historial.
    """

    if (not isinstance(resultado_externo, dict) or not isinstance(turno_preparado, dict)):
        return _resultado_validacion(False, "unsafe_output", "output")

    validacion_estructura = validar_respuesta_estructurada(resultado_externo)

    if not validacion_estructura["valido"]:
        return _resultado_validacion(False,"unsafe_output","output")

    contexto = turno_preparado.get("contexto",{})

    ids_documentos_permitidos = set(contexto.get("document_ids", []))

    ids_faq_permitidas = set(contexto.get("faq_ids", []))

    ids_documentos_devueltos = set(resultado_externo["document_ids"])

    ids_faq_devueltas = set(resultado_externo["faq_ids"])

    if not ids_documentos_devueltos.issubset(ids_documentos_permitidos):
        return _resultado_validacion(False,"unsafe_output","output")

    if not ids_faq_devueltas.issubset(ids_faq_permitidas):
        return _resultado_validacion(False,"unsafe_output","output")

    respuesta_normalizada = normalizar_texto_seguridad(resultado_externo["answer"])

    if len(resultado_externo["answer"]) > MAX_SAFE_OUTPUT_CHARS:
        return _resultado_validacion(False,"unsafe_output","output")

    if _coincide_algun_patron(respuesta_normalizada,PATRONES_FUGA_SALIDA):
        return _resultado_validacion(False,"unsafe_output","output")

    return _resultado_validacion(True,"valid_output","output")



# después de esta validación de respuesta queda cerrar turno
# con finalizar_turno() para guardar la interacción en el historial







# ============================================================
# CODIGO ANTERIOR
# ============================================================

# def validate_input(texto: str) -> list[str]:
        
#     """Devuelve lista de errores (vacía = OK). Ver README Fase 2, Tarea 1."""
#     errores: list[str] = []
#     t = (texto or "").strip()
#     if not t:
#         errores.append("El mensaje no puede estar vacío.")
#     if len(t) > MAX_INPUT_CHARS:
#         errores.append(f"Mensaje demasiado largo (máx {MAX_INPUT_CHARS} caracteres).")
#     t_lower = t.lower()
#     for patron in PATRONES_SOSPECHOSOS:
#         if patron in t_lower:
#             errores.append(f"Patrón no permitido detectado: {patron!r}")
#     return errores


# def parece_dominio_python(texto: str) -> bool:
#     """True si el mensaje parece relacionado con Python/bootcamp. Ver README Fase 2."""
#     t = texto.lower()
#     return any(k in t for k in DOMINIO_KEYWORDS)


# def rechazo_fuera_de_dominio() -> str:
#     """Mensaje fijo cuando la pregunta no encaja en el producto."""
#     return (
#         "Solo puedo ayudarte con Python y ejercicios del bootcamp. "
#         "Reformula tu pregunta en ese contexto."
#     )

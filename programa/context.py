import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from config import (
    DOCUMENT_SCORE_WEIGHTS,
    FAQ_SCORE_WEIGHTS,
    MAX_CONTEXT_DOCUMENTS,
    MAX_CONTEXT_FAQS,
    MIN_DOCUMENT_SCORE,
    MIN_FAQ_SCORE,
    TRANSVERSAL_DOCUMENT_IDS,
)

def cargar_json(ruta: Path | str) -> list[dict] | dict:
    """
    Carga un archivo JSON desde disco.

    Admite como estructura raíz una lista o un diccionario.
    """
    ruta = Path(ruta)

    if not ruta.exists():
        raise FileNotFoundError(
            f"No se ha encontrado el archivo JSON: {ruta}"
        )

    if not ruta.is_file():
        raise ValueError(
            f"La ruta indicada no corresponde a un archivo: {ruta}"
        )

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"El archivo contiene un JSON no válido: {ruta}"
        ) from error

    except OSError as error:
        raise OSError(
            f"No se ha podido leer el archivo JSON: {ruta}"
        ) from error

    if not isinstance(datos, (list, dict)):
        raise ValueError(
            f"El JSON debe contener una lista o un diccionario: {ruta}"
        )

    return datos


# Alias temporal para mantener compatibilidad con módulos
# que todavía utilizan el nombre antiguo.
cargar_JSON = cargar_json


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

# ============================================================
# MODO VULNERABLE
# ============================================================

def seleccionar_contexto_vulnerable(
    entradas: list[dict],
    consulta: str,
) -> list[dict]:
    """
    Anti-patrón intencional del modo vulnerable.

    Devuelve todas las entradas recibidas sin aplicar filtros de relevancia,
    minimización, departamento, perfil, permisos ni sensibilidad.
    """
    _ = consulta
    return entradas.copy()


def validar_lista_diccionarios(
    datos: Any,
    nombre_fuente: str,
    permitir_vacia: bool = False,
) -> list[dict]:
    """
    Comprueba que una fuente contiene una lista de diccionarios.

    Por defecto, una lista vacía se considera una fuente no válida.
    """
    if not isinstance(datos, list):
        raise ValueError(
            f"{nombre_fuente} debe contener una lista de entradas."
        )

    if not datos and not permitir_vacia:
        raise ValueError(
            f"{nombre_fuente} no puede estar vacío."
        )

    if not all(isinstance(entrada, dict) for entrada in datos):
        raise ValueError(
            f"Todas las entradas de {nombre_fuente} deben ser diccionarios."
        )

    return datos


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalizar_texto(texto: str | None) -> str:
    """
    Normaliza un texto para facilitar las comparaciones.

    Convierte el texto a minúsculas, elimina acentos,
    sustituye separadores por espacios y elimina espacios duplicados.
    """
    if texto is None:
        return ""

    texto_normalizado = str(texto).lower().strip()

    texto_normalizado = unicodedata.normalize(
        "NFD",
        texto_normalizado,
    )

    texto_normalizado = "".join(
        caracter
        for caracter in texto_normalizado
        if unicodedata.category(caracter) != "Mn"
    )

    texto_normalizado = re.sub(
        r"[_\-/]+",
        " ",
        texto_normalizado,
    )

    texto_normalizado = re.sub(
        r"\s+",
        " ",
        texto_normalizado,
    )

    return texto_normalizado.strip()


def extraer_palabras(texto: str | None) -> set[str]:
    """
    Extrae las palabras relevantes de un texto normalizado.
    """
    texto_normalizado = normalizar_texto(texto)

    palabras = re.findall(
        r"\b[a-z0-9]+\b",
        texto_normalizado,
    )

    return {
        palabra
        for palabra in palabras
        if len(palabra) > 2
        and palabra not in STOPWORDS
    }


def normalizar_tags(tags: Any) -> set[str]:
    """
    Normaliza una colección de tags.

    Ignora los valores que no sean strings.
    """
    if not isinstance(tags, list):
        return set()

    tags_normalizados: set[str] = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue

        tag_normalizado = normalizar_texto(tag)

        if tag_normalizado:
            tags_normalizados.add(tag_normalizado)

    return tags_normalizados


def extraer_palabras_tags(tags: Any) -> set[str]:
    """
    Convierte una lista de tags en un conjunto de palabras útiles.

    Permite procesar tags simples y expresiones compuestas,
    por ejemplo: 'trabajo remoto' o 'primer_dia'.
    """
    palabras: set[str] = set()

    for tag in normalizar_tags(tags):
        palabras.update(
            extraer_palabras(tag)
        )

    return palabras


# ============================================================
# BÚSQUEDA DE EMPLEADOS
# ============================================================

def buscar_empleado(
    empleados: list[dict],
    empleado_id: str,
) -> dict | None:
    """
    Busca un empleado por su identificador.

    La búsqueda no diferencia entre mayúsculas, minúsculas
    ni acentos.
    """
    validar_lista_diccionarios(
        empleados,
        "empleados_demo.json",
    )

    empleado_id_normalizado = normalizar_texto(
        empleado_id
    )

    if not empleado_id_normalizado:
        return None

    for empleado in empleados:
        identificador = normalizar_texto(
            empleado.get("id", "")
        )

        if identificador == empleado_id_normalizado:
            return empleado

    return None


# ============================================================
# PUNTUACIÓN DE FAQ
# ============================================================

def puntuar_faq(
    faq: dict,
    palabras_pregunta: set[str],
    pregunta_normalizada: str,
) -> int:
    """
    Calcula la relevancia de una FAQ respecto a una pregunta.

    La puntuación combina:
    - coincidencias con tags;
    - coincidencias con la pregunta frecuente;
    - coincidencias con la respuesta corta;
    - coincidencias literales con tags compuestos.
    """
    pregunta_faq = normalizar_texto(
        faq.get("pregunta", "")
    )

    respuesta_corta = normalizar_texto(
        faq.get("respuesta_corta", "")
    )

    tags_normalizados = normalizar_tags(
        faq.get("tags", [])
    )

    palabras_tags = extraer_palabras_tags(
        faq.get("tags", [])
    )

    palabras_pregunta_faq = extraer_palabras(
        pregunta_faq
    )

    palabras_respuesta = extraer_palabras(
        respuesta_corta
    )

    coincidencias_tags = palabras_pregunta.intersection(
        palabras_tags
    )

    coincidencias_pregunta = palabras_pregunta.intersection(
        palabras_pregunta_faq
    )

    coincidencias_respuesta = palabras_pregunta.intersection(
        palabras_respuesta
    )

    puntuacion = 0

    puntuacion += (
        len(coincidencias_tags)
        * FAQ_SCORE_WEIGHTS["tag"]
    )

    puntuacion += (
        len(coincidencias_pregunta)
        * FAQ_SCORE_WEIGHTS["question"]
    )

    puntuacion += (
        len(coincidencias_respuesta)
        * FAQ_SCORE_WEIGHTS["short_answer"]
    )

    # Una coincidencia literal con un tag compuesto recibe
    # una bonificación adicional porque suele representar
    # una intención concreta.
    for tag in tags_normalizados:
        if " " in tag and tag in pregunta_normalizada:
            puntuacion += FAQ_SCORE_WEIGHTS["tag"]

    return puntuacion


def seleccionar_faq(
    faqs: list[dict],
    consulta: str,
    max_entradas: int = MAX_CONTEXT_FAQS,
) -> list[dict]:
    """
    Selecciona las FAQ más relevantes para una consulta.

    Las FAQ funcionan como índice de búsqueda y pueden apuntar
    al documento principal mediante el campo doc_id.
    """
    validar_lista_diccionarios(
        faqs,
        "faq_onboarding.json",
    )

    if not isinstance(consulta, str) or not consulta.strip():
        return []

    if max_entradas <= 0:
        return []

    palabras_pregunta = extraer_palabras(
        consulta
    )

    pregunta_normalizada = normalizar_texto(
        consulta
    )

    faqs_puntuadas: list[tuple[int, dict]] = []

    for faq in faqs:
        puntuacion = puntuar_faq(
            faq=faq,
            palabras_pregunta=palabras_pregunta,
            pregunta_normalizada=pregunta_normalizada,
        )

        if puntuacion >= MIN_FAQ_SCORE:
            faqs_puntuadas.append(
                (puntuacion, faq)
            )

    # En caso de empate se ordena también por ID
    # para obtener resultados deterministas.
    faqs_puntuadas.sort(
        key=lambda elemento: (
            -elemento[0],
            str(elemento[1].get("id", "")),
        )
    )

    return [
        faq
        for _, faq in faqs_puntuadas[:max_entradas]
    ]


# ============================================================
# PUNTUACIÓN DE DOCUMENTOS
# ============================================================

def puntuar_documento(
    documento: dict,
    empleado: dict,
    palabras_pregunta: set[str],
    pregunta_normalizada: str,
) -> int:
    """
    Calcula la relevancia de un documento para una consulta.

    La intención de la pregunta tiene más peso que el departamento
    del empleado. El departamento y el carácter global solo actúan
    como factores de personalización o desempate.
    """
    departamento_empleado = normalizar_texto(
        empleado.get("departamento", "")
    )

    departamento_documento = normalizar_texto(
        documento.get("departamento", "")
    )

    titulo = normalizar_texto(
        documento.get("titulo", "")
    )

    cuerpo = normalizar_texto(
        documento.get("cuerpo", "")
    )

    tags_normalizados = normalizar_tags(
        documento.get("tags", [])
    )

    palabras_tags = extraer_palabras_tags(
        documento.get("tags", [])
    )

    palabras_titulo = extraer_palabras(
        titulo
    )

    palabras_cuerpo = extraer_palabras(
        cuerpo
    )

    coincidencias_tags = palabras_pregunta.intersection(
        palabras_tags
    )

    coincidencias_titulo = palabras_pregunta.intersection(
        palabras_titulo
    )

    coincidencias_cuerpo = palabras_pregunta.intersection(
        palabras_cuerpo
    )

    puntuacion_intencion = 0

    puntuacion_intencion += (
        len(coincidencias_tags)
        * DOCUMENT_SCORE_WEIGHTS["tag"]
    )

    puntuacion_intencion += (
        len(coincidencias_titulo)
        * DOCUMENT_SCORE_WEIGHTS["title"]
    )

    puntuacion_intencion += (
        len(coincidencias_cuerpo)
        * DOCUMENT_SCORE_WEIGHTS["body"]
    )

    # Los tags compuestos obtienen una bonificación adicional
    # cuando aparecen literalmente en la pregunta.
    for tag in tags_normalizados:
        if " " in tag and tag in pregunta_normalizada:
            puntuacion_intencion += DOCUMENT_SCORE_WEIGHTS["tag"]

    puntuacion = puntuacion_intencion

    # El departamento solo añade puntuación cuando ya existe
    # alguna coincidencia real con la intención de la consulta.
    if (
        puntuacion_intencion > 0
        and departamento_documento
        and departamento_documento == departamento_empleado
    ):
        puntuacion += DOCUMENT_SCORE_WEIGHTS[
            "employee_department"
        ]

    # Un documento global no entra únicamente por ser global.
    # Solo recibe bonificación si ya es relevante por contenido.
    documento_id = documento.get("id")

    if (
        puntuacion_intencion > 0
        and documento_id in TRANSVERSAL_DOCUMENT_IDS
    ):
        puntuacion += DOCUMENT_SCORE_WEIGHTS[
            "global_document"
        ]

    return puntuacion


def seleccionar_documentos(
    documentos: list[dict],
    consulta: str,
    empleado: dict,
    max_documentos: int = MAX_CONTEXT_DOCUMENTS,
) -> list[dict]:
    """
    Selecciona los documentos más relevantes para la consulta.

    Los documentos constituyen la fuente principal y autorizada
    para construir la respuesta.
    """
    validar_lista_diccionarios(
        documentos,
        "onboarding_docs.json",
    )

    if not isinstance(empleado, dict):
        raise ValueError(
            "El empleado debe ser un diccionario."
        )

    if not isinstance(consulta, str) or not consulta.strip():
        return []

    if max_documentos <= 0:
        return []

    palabras_pregunta = extraer_palabras(
        consulta
    )

    pregunta_normalizada = normalizar_texto(
        consulta
    )

    documentos_puntuados: list[tuple[int, dict]] = []

    for documento in documentos:
        puntuacion = puntuar_documento(
            documento=documento,
            empleado=empleado,
            palabras_pregunta=palabras_pregunta,
            pregunta_normalizada=pregunta_normalizada,
        )

        if puntuacion >= MIN_DOCUMENT_SCORE:
            documentos_puntuados.append(
                (puntuacion, documento)
            )

    # En caso de empate se ordena también por ID
    # para obtener resultados deterministas.
    documentos_puntuados.sort(
        key=lambda elemento: (
            -elemento[0],
            str(elemento[1].get("id", "")),
        )
    )

    return [
        documento
        for _, documento in documentos_puntuados[
            :max_documentos
        ]
    ]


# ============================================================
# BÚSQUEDA DE DOCUMENTOS
# ============================================================

def obtener_documento_por_id(
    documentos: list[dict],
    doc_id: str | None,
) -> dict | None:
    """
    Busca un documento por su identificador.
    """
    if not doc_id:
        return None

    doc_id_normalizado = normalizar_texto(
        doc_id
    )

    for documento in documentos:
        identificador = normalizar_texto(
            documento.get("id", "")
        )

        if identificador == doc_id_normalizado:
            return documento

    return None


# ============================================================
# COMBINACIÓN DE FAQ Y DOCUMENTOS
# ============================================================

def combinar_documentos(
    documentos_seleccionados: list[dict],
    faqs_seleccionadas: list[dict],
    todos_documentos: list[dict],
    limite: int = MAX_CONTEXT_DOCUMENTS,
) -> list[dict]:
    """
    Combina los documentos seleccionados directamente y los
    documentos referenciados por las FAQ.

    Los documentos asociados a una FAQ tienen prioridad para evitar
    que desaparezcan al aplicar el límite máximo.
    """
    if limite <= 0:
        return []

    documentos_finales: list[dict] = []
    ids_incluidos: set[str] = set()

    # Primero se añaden los documentos referenciados por FAQ.
    for faq in faqs_seleccionadas:
        doc_id = faq.get("doc_id")

        documento = obtener_documento_por_id(
            documentos=todos_documentos,
            doc_id=doc_id,
        )

        if documento is None:
            continue

        documento_id = documento.get("id")

        if not documento_id:
            continue

        documento_id_normalizado = normalizar_texto(
            documento_id
        )

        if documento_id_normalizado in ids_incluidos:
            continue

        documentos_finales.append(documento)
        ids_incluidos.add(documento_id_normalizado)

        if len(documentos_finales) >= limite:
            return documentos_finales

    # Después se completan las posiciones restantes con
    # los documentos seleccionados por puntuación directa.
    for documento in documentos_seleccionados:
        documento_id = documento.get("id")

        if not documento_id:
            continue

        documento_id_normalizado = normalizar_texto(
            documento_id
        )

        if documento_id_normalizado in ids_incluidos:
            continue

        documentos_finales.append(documento)
        ids_incluidos.add(documento_id_normalizado)

        if len(documentos_finales) >= limite:
            break

    return documentos_finales


# ============================================================
# CONSTRUCCIÓN DEL CONTEXTO
# ============================================================

def construir_contexto(
    consulta: str,
    empleado: dict,
    documentos: list[dict],
    faqs: list[dict],
    limite_documentos: int = MAX_CONTEXT_DOCUMENTS,
    limite_faqs: int = MAX_CONTEXT_FAQS,
) -> dict:
    """
    Construye el contexto documental final de una interacción.

    Flujo:
    1. Selecciona las FAQ más relevantes.
    2. Selecciona documentos por intención y departamento.
    3. Añade con prioridad los documentos referenciados por FAQ.
    4. Desduplica y limita las fuentes.
    5. Devuelve las fuentes y sus metadatos.
    """
    validar_lista_diccionarios(
        documentos,
        "onboarding_docs.json",
    )

    validar_lista_diccionarios(
        faqs,
        "faq_onboarding.json",
    )

    if not isinstance(empleado, dict):
        raise ValueError(
            "El empleado debe ser un diccionario."
        )

    if not isinstance(consulta, str):
        raise ValueError(
            "La consulta debe ser un string."
        )

    faqs_seleccionadas = seleccionar_faq(
        faqs=faqs,
        consulta=consulta,
        max_entradas=limite_faqs,
    )

    documentos_seleccionados = seleccionar_documentos(
        documentos=documentos,
        consulta=consulta,
        empleado=empleado,
        max_documentos=limite_documentos,
    )

    documentos_finales = combinar_documentos(
        documentos_seleccionados=documentos_seleccionados,
        faqs_seleccionadas=faqs_seleccionadas,
        todos_documentos=documentos,
        limite=limite_documentos,
    )

    document_ids = [
        documento["id"]
        for documento in documentos_finales
        if documento.get("id")
    ]

    faq_ids = [
        faq["id"]
        for faq in faqs_seleccionadas
        if faq.get("id")
    ]

    return {
        "empleado": empleado,
        "documentos": documentos_finales,
        "faqs": faqs_seleccionadas,
        "document_ids": document_ids,
        "faq_ids": faq_ids,
        "hay_contexto": bool(
            documentos_finales
            or faqs_seleccionadas
        ),
    }

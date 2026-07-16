
from pathlib import Path


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

# config.py se encuentra dentro de la carpeta programa/.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

EMPRESA_PATH = DATA_DIR / "empresa.json"
EMPLEADOS_PATH = DATA_DIR / "empleados_demo.json"
DOCS_PATH = DATA_DIR / "onboarding_docs.json"
FAQ_PATH = DATA_DIR / "faq_onboarding.json"


# ============================================================
# CONFIGURACIÓN RUTAS MODO VULNERABLE
# ============================================================

# El modo vulnerable carga deliberadamente todas las fuentes
# disponibles sin aplicar selección, minimización ni filtrado.
VULNERABLE_CONTEXT_PATHS = [
    EMPRESA_PATH,
    EMPLEADOS_PATH,
    DOCS_PATH,
    FAQ_PATH,
]


# ============================================================
# RUTAS DE DATOS Y ENTREGABLES — LLM Y BENCHMARK
# ============================================================
# El archivo semilla de preguntas (Entrada)
PREGUNTAS_BENCHMARK_PATH = DATA_DIR / "preguntas_benchmark.json"

# El reporte final generado por el script (Salida)
# Lo guardamos en la carpeta de entregables para que sea visible en la entrega final
RESULTADOS_BENCHMARK_PATH = BASE_DIR / "entregables" / "resultados_benchmark.json"


# ============================================================
# LLM Y BENCHMARK
# ============================================================

# Modelos reales disponibles en tu API para el test A/B
MODEL_1 = "gemini-2.5-flash"  # Variante A (Eficiencia)
MODEL_2 = "gemini-2.5-pro"    # Variante B (Calidad)

# Selección de modelo por defecto para el asistente en producción
MODEL = MODEL_1

TEMPERATURE_DEFAULT = 0.2
# TEMPERATURE_SAFE = TEMPERATURE_DEFAULT
TEMPERATURE_VULNERABLE = TEMPERATURE_DEFAULT

MAX_TOKENS_INPUT = 8_000

REQUIRED_RESPONSE_FIELDS = frozenset(
    {
        "in_scope",
        "category",
        "answer",
        "document_ids",
        "faq_ids",
        "needs_escalation",
        "escalation_department",
    }
)

# JSON_SCHEMA_HINT = """
# El área LLM y Benchmark debe definir aquí el contrato de respuesta
# estructurada solicitado al modelo.
# """.strip()


# ============================================================
# CONFIGURACIÓN GENERAL DEL ASISTENTE
# ============================================================

# Número máximo de mensajes recientes incluidos en el historial.
WINDOW = 4

# Extensión máxima aproximada de la respuesta final.
MAX_OUTPUT_WORDS = 200

ASSISTANT_CONFIG_DEFAULT = {
    "model": MODEL,
    "temperature": TEMPERATURE_DEFAULT,
    "perfil_activo": "onboarding",
    "max_turnos_historial": WINDOW,
    "idioma_respuesta": "español",
    "max_palabras": MAX_OUTPUT_WORDS,
    "max_documentos_contexto": 3,
    "max_faqs_contexto": 2,
}


# ============================================================
# LÍMITES DE CONTEXTO Y ONBOARDING
# ============================================================

# Número máximo de fuentes que context.py puede seleccionar
# para una interacción.
MAX_CONTEXT_DOCUMENTS = 3
MAX_CONTEXT_FAQS = 2

# Durante los días 1 a 7, ambos incluidos, se utiliza
# el perfil funcional de onboarding salvo que la categoría
# de la consulta requiera un perfil más específico.
ONBOARDING_PROFILE_DAYS = 7

# El acompañamiento inicial se considera comprendido dentro
# de los primeros 30 días. Superar este límite no bloquea
# el uso del asistente.
MAX_ONBOARDING_DAYS = 30


# ============================================================
# CONFIGURACIÓN DE PUNTUACIÓN DEL CONTEXTO
# ============================================================

# Pesos utilizados por context.py para ordenar los documentos.
DOCUMENT_SCORE_WEIGHTS = {
    "tag": 3,
    "title": 2,
    "body": 1,
    "employee_department": 2,
    "global_document": 1,
}

# Pesos utilizados por context.py para ordenar las FAQ.
FAQ_SCORE_WEIGHTS = {
    "tag": 3,
    "question": 2,
    "short_answer": 1,
}

# Una coincidencia basada únicamente en el departamento o en
# el carácter transversal de un documento no es suficiente
# para incorporarlo al contexto.
MIN_DOCUMENT_SCORE = 2
MIN_FAQ_SCORE = 2


# ============================================================
# DOCUMENTACIÓN TRANSVERSAL
# ============================================================

# IDs de documentos potencialmente aplicables a empleados de
# cualquier departamento.
#
# El carácter transversal solo añade puntuación cuando ya existe
# una coincidencia real entre la consulta y el contenido.
TRANSVERSAL_DOCUMENT_IDS = frozenset(
    {
        "doc_bienvenida_01",
        "doc_it_01",
        "doc_it_02",
        "doc_rrhh_01",
        "doc_rrhh_02",
        "doc_rrhh_03",
        "doc_cultura_01",
        "doc_beneficios_01",
        "doc_people_01",
    }
)


# ============================================================
# PERFILES FUNCIONALES
# ============================================================

# Los perfiles modifican el tono y el nivel de explicación.
# No sustituyen la selección documental ni determinan por sí
# solos la categoría de la consulta.
PERFILES = {
    "onboarding": {
        "rol": (
            "Actúas como acompañante de onboarding para empleados recién "
            "incorporados. Explicas los pasos de manera clara, ordenada y "
            "accesible, evitando asumir conocimientos previos."
        ),
        "nivel_explicacion": "guiado",
        "criterio": (
            "Se utiliza durante los días 1 a 7 desde la fecha de "
            "incorporación, salvo que la consulta requiera un perfil "
            "funcional más específico."
        ),
    },
    "administrativo_rrhh": {
        "rol": (
            "Actúas como asistente administrativo de RRHH. Respondes de "
            "forma directa y profesional sobre políticas, procedimientos, "
            "beneficios, vacaciones, horarios y gestiones internas."
        ),
        "nivel_explicacion": "directo",
        "criterio": (
            "Se utiliza desde el octavo día o cuando la consulta sea "
            "principalmente administrativa o de RRHH."
        ),
    },
    "it": {
        "rol": (
            "Actúas como asistente de soporte IT para el proceso de "
            "onboarding. Explicas los procedimientos técnicos autorizados "
            "de forma clara y accesible."
        ),
        "nivel_explicacion": "técnico_accesible",
        "criterio": (
            "Se utiliza para consultas relacionadas con accesos, cuentas, "
            "dispositivos, herramientas o procedimientos técnicos."
        ),
    },
}

VALID_PROFILES = frozenset(PERFILES.keys())


# ============================================================
# REGLAS FUNCIONALES DEL PRODUCTO
# ============================================================

# Este prompt contiene exclusivamente las reglas funcionales
# del Employee Onboarding Assistant.
#
# Las defensas frente a prompt injection, jailbreak, extracción
# de instrucciones y otras amenazas corresponden al área de Robustez.
SYSTEM_PROMPT = """
Eres el Employee Onboarding Assistant de Bridge SA.

Reglas funcionales:

1. Ayuda únicamente en consultas relacionadas con el onboarding y los
   procedimientos internos autorizados de Bridge SA.

2. Responde únicamente con información presente en el contexto documental
   proporcionado para la interacción actual.

3. Considera onboarding_docs.json como la fuente documental principal.
   Las FAQ sirven como índice y apoyo, pero no sustituyen al documento
   original al que hacen referencia.

4. No inventes políticas, procedimientos, fechas, contactos, permisos,
   herramientas, beneficios ni datos personales.

5. Si la documentación no contiene información suficiente, indícalo con
   claridad y deriva al empleado al departamento correspondiente.

6. Adapta el tono y el nivel de explicación al perfil, departamento y día
   de onboarding del empleado.

7. No afirmes haber realizado acciones externas, creado accesos, enviado
   solicitudes o modificado sistemas. Solo puedes explicar los pasos
   descritos en la documentación.

8. Responde en el idioma configurado para el asistente.
""".strip()


# ============================================================
# CATEGORÍAS DE CONSULTA
# ============================================================

VALID_CATEGORIES = frozenset(
    {
        "onboarding",
        "it",
        "rrhh",
        "people",
        "engineering",
        "sales",
        "operations",
        "general",
        "out_of_scope",
    }
)


# Palabras y expresiones orientativas para clasificar la consulta.
#
# La decisión final corresponde a logic.py, que puede combinar
# estas señales con el perfil del empleado y el contexto recuperado.
DOMAIN_KEYWORDS = {
    "onboarding": (
        "onboarding",
        "incorporación",
        "incorporacion",
        "primer día",
        "primer dia",
        "primera semana",
        "bienvenida",
        "buddy",
        "mentor",
        "checklist",
        "tareas iniciales",
    ),
    "it": (
        "it",
        "soporte",
        "portátil",
        "portatil",
        "ordenador",
        "equipo",
        "contraseña",
        "contrasena",
        "acceso",
        "cuenta",
        "correo",
        "slack",
        "github",
        "vpn",
        "software",
        "herramienta",
        "permisos",
        "autenticación",
        "autenticacion",
    ),
    "rrhh": (
        "rrhh",
        "recursos humanos",
        "vacaciones",
        "ausencia",
        "baja",
        "nómina",
        "nomina",
        "horario",
        "fichaje",
        "contrato",
        "trabajo remoto",
        "teletrabajo",
        "beneficios",
    ),
    "people": (
        "people",
        "cultura",
        "valores",
        "bienestar",
        "feedback",
        "manager",
        "responsable",
        "equipo",
        "integración",
        "integracion",
    ),
    "engineering": (
        "engineering",
        "desarrollo",
        "desarrollador",
        "repositorio",
        "código",
        "codigo",
        "entorno de desarrollo",
        "pull request",
        "git",
        "github",
    ),
    "sales": (
        "sales",
        "ventas",
        "comercial",
        "cliente",
        "crm",
        "pipeline",
        "oportunidad",
        "reunión comercial",
        "reunion comercial",
    ),
    "operations": (
        "operations",
        "operaciones",
        "proceso operativo",
        "incidencia",
        "proveedor",
        "logística",
        "logistica",
        "procedimiento",
    ),
}


# ============================================================
# ESCALACIÓN
# ============================================================

# Los contactos concretos deben obtenerse de empresa.json.
# Este mapa indica qué área debe resolver cada categoría.
ESCALATION_DEPARTMENT_BY_CATEGORY = {
    "onboarding": "people",
    "people": "people",
    "rrhh": "rrhh",
    "it": "it",
    "engineering": "manager",
    "sales": "manager",
    "operations": "manager",
    "general": "people",
    "out_of_scope": None,
}


# ============================================================
# ALIAS TEMPORALES DE INTEGRACIÓN
# ============================================================

# Alias temporal para mantener compatibilidad con módulos que
# todavía utilizan el nombre anterior.
DOMINIO_KEYWORDS = DOMAIN_KEYWORDS


# ============================================================
# ROBUSTEZ — ELIMINADO DE LA ARQUITECTURA BASE
# ============================================================

# Este bloque conserva los puntos previstos para integrar las
# validaciones y defensas responsabilidad del área de Robustez.

# MAX_INPUT_CHARS = 2_000

# SUSPICIOUS_PATTERNS = (
#     "ignora las instrucciones",
#     "ignore previous instructions",
#     "jailbreak",
#     "prompt injection",
# )

# PATRONES_SOSPECHOSOS = SUSPICIOUS_PATTERNS

# El área de Robustez deberá incorporar:
#
# - Validación avanzada de entradas.
# - Detección de prompt injection.
# - Detección de jailbreak.
# - Protección de instrucciones internas.
# - Variantes segura y vulnerable del flujo.

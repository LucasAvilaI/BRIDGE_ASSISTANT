from pathlib import Path
MODEL_1 = "gemini-3-flash-preview"
'''
MODEL_2 = "Llama"
MODEL_3 = Hugging face
'''


TEMPERATURE_DEFAULT = 0.2

TEMPERATURE_VULNERABLE = TEMPERATURE_DEFAULT
TEMPERATURE_SAFE = TEMPERATURE_DEFAULT

# MODO VULNERABLE: Activar solo para tests de seguridad y detección de vulnerabilidades. No filtra ni valida la información.
# EXPERIMENTAL_TEMPERATURES = [0.0, 0.2, 0.7, 1.0]
WINDOW = 4
MAX_TOKENS_INPUT = 8_000
MAX_INPUT_CHARS = 2_000

#TO_DO:


ASSISTANT_CONFIG_DEFAULT = {
    "model": MODEL_1,
    "temperature": TEMPERATURE,
    #TO_DO: Definir perfil del modelo.
    "perfil_activo": "mentor",
    "max_turnos_historial": WINDOW,
    "idioma_respuesta": "español",
    "max_palabras": 200,
}

PERFILES = {
    #TO_DO:Definir roles
    #Onboarding: Recién llegados. Menos de 7 días.
    #Administrativo_RRHH: Más de 7 días en la empresa (inclusive)
    #IT: Seguridad y brechas en el programa. En caso de llamar al modelo con conductas sospechosas, disuadir al cliente.
    
    "Onboarding": {
        "rol": (
            "Eres un compañero de estudio amable. "
            "Explicas con ejemplos cortos y vocabulario accesible."
        ),
        "nivel_explicacion": "básico",
    },
    "senior": {
        "rol": (
            "Eres un ingeniero senior. "
            "Vas al grano y asumes conocimientos previos de Python y APIs."
        ),
        "nivel_explicacion": "avanzado",
    },
    "mentor": {
        "rol": (
            "Eres un mentor pedagógico. "
            "Guías con pasos y preguntas reflexivas, sin abrumar."
        ),
        "nivel_explicacion": "intermedio",
    },
}


#TO_DO: Definir las reglas inmutables
SYSTEM_PROMPT = """
Eres el Employee Onboarding Assistant de Bridge SA.
Reglas inmutables:
-Ayuda únicamente a empleados durante su proceso de onboarding.
-Responde solo con información presente en la documentación proporcionada.
-Si la información no existe o no es suficiente, indícalo y deriva al departamento correspondiente.
-No inventes políticas, procedimientos, fechas ni datos.
-Adapta el tono y la explicación al perfil y al día de onboarding del empleado.
""".strip()

#TO_DO: Definición de dominios.

DOMINIO_KEYWORDS = (
    #TO_DO: Definir
    "python",
    "lista",
    "listas",
    "función",
    "funcion",
    "def ",
    "error",
    "pip",
    "venv",
    "import",
    "for ",
    "while ",
    "dict",
    "tupla",
    "print(",
    "syntax",
    "sintaxis",
    "asistente",
    "assistant",
    "embedding",
    "contexto",
    "prompt",
    "bootcamp",
)


PATRONES_SOSPECHOSOS = (
    #TO_DO: Definir
    "ignora instrucciones",
    "ignore previous",
    "actúa como",
    "actua como",
    "disregard",
    "system:",
    "jailbreak",
)

# TO_DO MODO VULNERABLE > CONTEXTO VULNERABLE
# Carga de contexto sin filtrar: aumenta ruido, coste y superficie de exposición.
# Se deja fuera del MVP porque la vulnerabilidad prioritaria —pasar input
# no validado al LLM— ya está implementada.
#
# Pendiente de integrar cuando el equipo defina la arquitectura compartida
# de carga y normalización de contexto.

'''
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

FAQ_PATH = DATA_DIR / "faq_onboarding.json"
EMPLOYEES_PATH = DATA_DIR / "empleados_demo.json"
ONBOARDING_PATH = DATA_DIR / "onboarding_docs.json"
POLICIES_PATH = DATA_DIR / "empresa.json"

VULNERABLE_CONTEXT_PATHS = [
    FAQ_PATH,
    EMPLOYEES_PATH,
    ONBOARDING_PATH,
    POLICIES_PATH,
]
'''

#TO_DO: Definir respuesta JSON del modelo.
JSON_SCHEMA_HINT = """
Devuelve SOLO un JSON con estas claves:
- "empleado_id": identificador del empleado (p. ej. emp_01)
- "dia": De 1 a 5 
- "tarea": Lista de strings con las tareas por hacer
-"document_id": 
""".strip()

"""
Gestión del estado y del historial de conversación del asistente.

Responsabilidades de este módulo:
- Inicializar el estado de una nueva sesión.
- Mantener el perfil del empleado asociado a la conversación.
- Registrar los mensajes enviados por el usuario.
- Registrar las respuestas generadas por el asistente.
- Mantener el contador de turnos conversacionales.
- Recuperar los últimos turnos del historial para su reutilización
  durante la preparación de nuevas interacciones.

El estado se representa mediante un diccionario que contiene el perfil
del usuario, el historial de mensajes y el número de turnos completados.
Un turno conversacional está formado por un mensaje del usuario y una
respuesta del asistente.

Este módulo NO:
- valida las consultas del usuario;
- selecciona documentos o FAQ;
- construye el contexto documental;
- clasifica consultas ni selecciona perfiles funcionales;
- construye prompts;
- realiza llamadas al modelo;
- valida las respuestas generadas por el LLM.

Notas para el equipo:
- logic.py utiliza este módulo para consultar y actualizar el estado
  durante el procesamiento de cada turno.
- prompts.py puede recibir el historial recuperado para incorporarlo
  al contenido enviado al modelo.
- El perfil del empleado procede de los datos de la aplicación y no
  se infiere automáticamente a partir de los mensajes del usuario.
"""

def inicializar_estado(user_profile: dict | None = None) -> dict:
    """Crea el dict de sesión. Ya implementada; no necesitas modificarla."""
    return {
        "user_profile": user_profile or {},
        #User_profile = Diccionario en empleados_demos.json
        "messages": [],
        "turnos": 0,
    }


def append_user(state: dict, texto: str) -> None:
    """Añade mensaje del usuario al historial. Ya implementada."""
    state["messages"].append({"role": "user", "text": texto.strip()})


def append_assistant(state: dict, texto: str) -> None:
    """Añade respuesta del asistente al historial. Ya implementada."""
    state["messages"].append({"role": "assistant", "text": texto.strip()})
    state["turnos"] = state.get("turnos", 0) + 1


def ultimos_n(state: dict, n: int) -> list[dict]:
    """
    Devuelve los mensajes de los últimos n TURNOS conversacionales
    (no los últimos n mensajes sueltos).

    Un turno = 1 mensaje de usuario + 1 de asistente = 2 entradas en
    "messages". config.py llama a este parámetro "max_turnos_historial"
    y el README pide "máx. 4 turnos en el prompt", así que n=4 debe
    devolver hasta 8 mensajes, no 4.
    """
    msgs = state.get("messages", [])
    return msgs[-(n * 2):] if n > 0 else []


# Nota: no existe gestión de "perfil de usuario derivado de mensajes"
# en el diseño actual. El perfil del empleado (perfil_empleado) viene
# siempre de empleados_demo.json a través de logic.py, no se infiere
# de lo que escribe en el chat.
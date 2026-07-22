
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
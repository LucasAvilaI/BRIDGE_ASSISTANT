# utils/console.py
import json
from typing import Any

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from config import OUTPUT_DEMO_DIR

import sys
import os

# Esto añade la carpeta 'programa' al PATH de forma automática al ejecutar el script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def log_test_header(test_id, model_key):
    print(f"\n{'='*60}")
    print(f"🧪 EVALUANDO: {test_id} | MODELO: {model_key}")
    print(f"{'-'*60}")

def log_result(status, extra_info=""):
    color = "✅" if status == "PASS" else "❌"
    print(f"{color} RESULTADO: {status} | {extra_info}")


# REGISTRO DE SALIDA DE LAS DEMOS
class _SalidaDuplicada:
    """
    Duplica la salida escrita por consola.

    Todo lo que recibe se envía simultáneamente:
    - a la terminal original;
    - al fichero de texto de la demo.

    De esta forma el usuario sigue viendo la ejecución normalmente
    mientras se conserva una copia completa en output_demo/.
    """

    def __init__(self, terminal, archivo):
        self.terminal = terminal
        self.archivo = archivo

    def write(self, texto: str) -> int:
        """Escribe el mismo contenido en terminal y fichero."""
        self.terminal.write(texto)
        self.archivo.write(texto)

        return len(texto)

    def flush(self) -> None:
        """Fuerza la escritura de los buffers pendientes."""
        self.terminal.flush()
        self.archivo.flush()

    def __getattr__(self, nombre):
        """
        Mantiene propiedades del stdout/stderr original.

        Permite que otras librerías sigan consultando atributos
        como encoding, isatty() o fileno().
        """
        return getattr(self.terminal, nombre)


@contextmanager
def registrar_salida_demo(nombre_demo: str) -> Iterator[Path]:
    """
    Registra en un fichero toda la salida de consola de una demo.

    El archivo se guarda en output_demo/ con el formato:

        AAAA-MM-DD_HH-MM-SS_demo_X.txt

    La salida no se oculta de la terminal: se muestra y se guarda
    simultáneamente.

    También captura stderr para conservar mensajes de error que
    puedan producir librerías externas.
    """

    OUTPUT_DEMO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fecha_hora = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    nombre_archivo = (
        f"{fecha_hora}_{nombre_demo}.txt"
    )

    ruta_archivo = OUTPUT_DEMO_DIR / nombre_archivo

    stdout_original = sys.stdout
    stderr_original = sys.stderr

    with ruta_archivo.open(
        "w",
        encoding="utf-8",
    ) as archivo:

        sys.stdout = _SalidaDuplicada(
            stdout_original,
            archivo,
        )

        sys.stderr = _SalidaDuplicada(
            stderr_original,
            archivo,
        )

        try:
            yield ruta_archivo

        finally:
            sys.stdout = stdout_original
            sys.stderr = stderr_original

# SALIDAS PARA LAS DEMOS
def mostrar_respuesta_demo(
    *,
    respuesta: str,
    json_respuesta: dict,
    llamo_modelo: bool,
    metricas: Any | None = None,
) -> None:
    """
    Muestra de forma homogénea el resultado de una demo.

    - Indica si se llamó al LLM.
    - Muestra una representación legible de la respuesta.
    - Muestra siempre el JSON asociado a la respuesta.
    - Muestra métricas únicamente cuando hubo llamada al modelo.
    """

    print("LLM invocado:", "SÍ" if llamo_modelo else "NO")

    print("\nRespuesta:")

    print(respuesta if respuesta else "(sin respuesta)")

    print("\nJSON de la respuesta:")

    print(
        json.dumps(
            json_respuesta,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    print("\nMétricas LLM:")

    print(
        json.dumps(
            metricas,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
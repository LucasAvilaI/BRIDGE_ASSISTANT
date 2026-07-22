"""Demo de los cinco casos trampa propios del equipo.

Objetivo
--------
- Ejecutar los cinco casos definidos por el equipo.
- Validar el código de rechazo esperado.
- Confirmar que los casos bloqueados no llaman al modelo.
- Mostrar un resumen reproducible de aprobados y fallidos.

Cobertura mínima:
1. Inyección de instrucciones.
2. Salario o bonus.
3. Participante externo o fuera de dominio.
4. Política no documentada.
5. Ambigüedad entre baja médica y baja laboral.

El criterio de "aprobado" es el exigido por el enunciado: el caso NO
debe llamar al modelo (llamar_modelo=False). El código de rechazo
esperado es orientativo: depende del contenido real de
onboarding_docs.json / faq_onboarding.json (por ejemplo, el caso 4
solo se clasifica como 'undocumented' si la consulta se reconoce como
interna pero no encuentra respaldo documental; si el equipo cambia el
dataset de demo puede acabar en 'out_of_scope' en su lugar, y seguiría
siendo un bloqueo correcto).
"""
from __future__ import annotations
from datetime import date
from state import inicializar_estado
from logic import preparar_turno_seguro
from context import buscar_empleado, cargar_json
from config import ASSISTANT_CONFIG_DEFAULT, CASOS_TRAMPA_PATH, DOCS_PATH, EMPLEADOS_PATH, EMPRESA_PATH, FAQ_PATH

import sys
import os

# Esto añade la carpeta 'programa' al PATH de forma automática al ejecutar el script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ============================================================
# CONFIGURACIÓN
# ============================================================

EMPLEADO_ID_DEMO = "emp_01"


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def obtener_casos_demo() -> list[dict]:
    """Carga y devuelve los casos trampa propios del equipo."""
    return cargar_json(CASOS_TRAMPA_PATH)

# ============================================================
# EJECUCIÓN
# ============================================================

def ejecutar_demo_casos_trampa() -> None:
    """Ejecuta la batería de consultas problemáticas."""
    empresa = cargar_json(EMPRESA_PATH)
    documentos = cargar_json(DOCS_PATH)
    faqs = cargar_json(FAQ_PATH)
    empleados = cargar_json(EMPLEADOS_PATH)
    empleado = buscar_empleado(empleados, EMPLEADO_ID_DEMO)

    if empleado is None:
        print(
            f"[ERROR] No se encontró el empleado de demo '{EMPLEADO_ID_DEMO}'.")
        return

    aprobados = 0
    fallidos = 0

    casos_trampa = obtener_casos_demo()


    for caso in casos_trampa:
        caso_id = caso["id"]
        tipo = caso["tipo"]
        consulta = caso["mensaje"]
        codigo_esperado = caso["codigo_esperado_seguro"]
        llamada_modelo_esperada = caso["llamada_modelo_esperada_seguro"]

        estado = inicializar_estado()

        resultado = preparar_turno_seguro(
            estado=estado,
            consulta=consulta,
            empleado=empleado,
            empresa=empresa,
            documentos=documentos,
            faqs=faqs,
            configuracion=ASSISTANT_CONFIG_DEFAULT,
            fecha_referencia=date.fromisoformat(empleado["fecha_inicio"]),
        )

        datos = resultado.get("data", {}) if isinstance(
            resultado, dict) else {}
        llamo_al_modelo = bool(datos.get("llamar_modelo", False))
        codigo_obtenido = datos.get("motivo_bloqueo")

        coincide_codigo = codigo_obtenido == codigo_esperado
        

        coincide_llamada_modelo = llamo_al_modelo == llamada_modelo_esperada

        caso_correcto = (
            resultado.get("status") == "ok"
            and coincide_codigo
            and coincide_llamada_modelo
        )

        if caso_correcto:
            aprobados += 1
            estado_caso = "OK"
        else:
            fallidos += 1
            estado_caso = "FALLO"

        print(f"[{estado_caso}] {caso_id} · {tipo}")
        print(f"    Consulta: {consulta}")
        print(
            f"    Llamó al modelo: {llamo_al_modelo} "
            f"(esperado: {llamada_modelo_esperada}, "
            f"coincide: {coincide_llamada_modelo})"
        )
        print(
            f"    Código obtenido: {codigo_obtenido} "
            f"(esperado: {codigo_esperado}, "
            f"coincide: {coincide_codigo})"
        )

        if caso_correcto:
            print(f"    Mensaje mostrado: {datos.get('respuesta')}")

        print()


        

    print(
        f"Resumen: {aprobados} bloqueados correctamente / "
        f"{fallidos} fallidos sobre {len(casos_trampa)} casos."
    )


if __name__ == "__main__":
    ejecutar_demo_casos_trampa()

"""
Módulo de ejecución del Benchmark (Área: LLM y Benchmark).

Este script automatiza el paso de baterías de prueba (incluyendo casos trampa)
bajo diferentes condiciones, midiendo latencia, costos y calidad de respuesta.
"""

from model_utils import obtener_modelo
from model_registry import MODELS
from logic import preparar_turno_con_modo
from config import (
    OUTPUT_DIR,
    PREGUNTAS_BENCHMARK_PATH,
    RESULTADOS_BENCHMARK_PATH,
    REQUIRED_RESPONSE_FIELDS
)
from utils.console import log_test_header, log_result
import json
import time
import sys
import os  # <-- Importante para os.path y os.makedirs
from datetime import date
from pathlib import Path

# Añadimos la carpeta 'programa' al path de búsqueda de Python
# Esto permite que los otros scripts dentro de 'programa' se encuentren entre sí
sys.path.append(str(Path(__file__).resolve().parent))

# Los imports que dependen de esa estructura:

# Importación segura de validadores
try:
    from validators import validar_respuesta_estructurada
    ROBUSTEZ_DISPONIBLE = True
except ImportError:
    ROBUSTEZ_DISPONIBLE = False


def calcular_costo(tokens_input: int, tokens_output: int, model_key: str) -> float:
    """
    Calcula el coste estimado de la llamada utilizando los metadatos del registro.
    """
    try:
        meta = obtener_modelo(model_key)
        cost_in = (tokens_input / 1_000_000) * \
            meta.get("cost_input_per_m", 0.0)
        cost_out = (tokens_output / 1_000_000) * \
            meta.get("cost_output_per_m", 0.0)
        return cost_in + cost_out
    except Exception:
        return 0.0


def estructurar_resultado_benchmark(
    pregunta_id: int,
    categoria_esperada: str,
    model_key: str,
    latencia: float,
    costo: float,
    tokens_in: int,
    tokens_out: int,
    valida_robustez: bool,
    cumple_esquema: bool
) -> dict:
    """
    Normaliza el diccionario de salida de métricas para evitar inconsistencias de claves.
    """
    return {
        "pregunta_id": pregunta_id,
        "categoria": categoria_esperada,
        "modelo": model_key,
        "latencia_segundos": latencia,
        "costo_dolares": costo,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "robustez_valida": valida_robustez,
        "cumple_esquema": cumple_esquema
    }


def ejecutar_evaluacion_modelo(model_key: str, preguntas: list, modo_seguridad: str = "vulnerable") -> list:
    """
    Simula la ejecución de la batería de pruebas para un modelo específico,
    calculando costos, latencias y validaciones.
    """
    resultados = []

    for item in preguntas:
        # Extraemos el prompt y gestionamos casos donde el campo sea None o falte
        prompt = item.get("prompt")
        pregunta_id = item.get("id")
        categoria_esperada = item.get("categoria_esperada")
        if not prompt:  # Si el prompt es None o está vacío, saltamos esta iteración
            print(
                f"⚠️ Saltando pregunta ID {item.get('id', 'desconocido')} por falta de contenido.")
            continue

        # 1. Visualización del inicio de prueba
        log_test_header(f"Pregunta {item.get('id')}", model_key)

        # 2. Llamada REAL al orquestador
        inicio = time.time()

        # Preparar los datos mínimos necesarios para que la función no falle
        # Si son pruebas, puedes usar diccionarios vacíos o de prueba:
        estado_mock = {"historial": [], "messages": [], "turnos": 0}
        empleado_mock = {"id": 1, "nombre": "Test",
                         "fecha_inicio": "2026-01-01"}
        empresa_mock = {"id": 1, "nombre": "Bridge"}
        documentos_mock = [
            {"titulo": "Manual de Bienvenida", "contenido": "Bienvenido a Bridge."},
            {"titulo": "Política de Seguridad",
                "contenido": "No compartir contraseñas."}
        ]
        faq_onboarding_mock = [
            {"pregunta": "¿Cómo accedo a GitHub?",
                "respuesta": "Usa tu cuenta corporativa."},
            {"pregunta": "¿Qué hacer el día 1?",
                "respuesta": "Revisar el manual de bienvenida."}
        ]

        print(f"DEBUG: Intentando ejecutar turno con modo: {modo_seguridad}")
        try:
            print(f"DEBUG: Llamando al orquestador con modo: {modo_seguridad}")
            resultado_orquestador = preparar_turno_con_modo(
                estado=estado_mock,
                consulta=prompt,
                empleado=empleado_mock,
                empresa=empresa_mock,
                documentos=documentos_mock,
                faqs=faq_onboarding_mock,
                fecha_referencia=date(2026, 7, 17),
                modo_seguridad=modo_seguridad
            )
            # <-- Esto nos dirá si es None
            print(f"DEBUG: Resultado recibido: {resultado_orquestador}")
        except Exception as e:
            import traceback
            print("--- ERROR DETECTADO ---")
            traceback.print_exc()
            resultado_orquestador = {}
        latencia = round(time.time() - inicio, 4)

       # 3. Mapeo de resultados
        # Primero verificamos si el orquestador permitió la llamada
        permitido_por_orquestador = resultado_orquestador.get(
            "llamar_modelo", False)

        # Inicializamos variables de control
        valida_robustez = permitido_por_orquestador
        cumple_esquema = permitido_por_orquestador

        if ROBUSTEZ_DISPONIBLE and permitido_por_orquestador:
            try:
                # Validamos solo si el orquestador permitió pasar
                validar_respuesta_estructurada(resultado_orquestador)
                cumple_esquema = True
            except Exception as e:
                print(f"❌ Error de validación de esquema: {e}")
                cumple_esquema = False
                # Si falla el esquema, marcamos la robustez como False
                valida_robustez = False

        # Simulación del volumen de tokens procesados
        tokens_in = len(prompt.split()) * 2
        tokens_out = 150
        costo_estimado = calcular_costo(tokens_in, tokens_out, model_key)

        # 4. Registro y Feedback visual
        log_result("PASS" if valida_robustez else "FAIL",
                   f"Latencia: {latencia}s")

        resultado_normalizado = estructurar_resultado_benchmark(
            pregunta_id=pregunta_id,
            categoria_esperada=categoria_esperada,
            model_key=model_key,
            latencia=latencia,
            costo=costo_estimado,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            valida_robustez=valida_robustez,
            cumple_esquema=cumple_esquema
        )
        resultados.append(resultado_normalizado)

    return resultados


"""    
        RESPUESTA MOCK ELIMINADA TRAS APLICAR RESPUESTA ORQUESTADOR
        # 2. Esquema de respuesta dinámico a partir de config.py (Single Source of Truth)
        respuesta_mock = {campo: None for campo in REQUIRED_RESPONSE_FIELDS}
        respuesta_mock["in_scope"] = True
        respuesta_mock["category"] = categoria_esperada
        respuesta_mock["answer"] = "Respuesta estructurada de simulación."
        respuesta_mock["document_ids"] = []
        respuesta_mock["faq_ids"] = []
        respuesta_mock["needs_escalation"] = False

        # 3. Validación de Robustez preventiva
        valida_robustez = True
        cumple_esquema = True

        if ROBUSTEZ_DISPONIBLE:
            try:
                # Se asume que el validador analiza el dict de salida estructurada
                validar_respuesta_estructurada(respuesta_mock)
            except Exception:
                valida_robustez = False
                cumple_esquema = False  # Ajustable según el tipo de excepción lanzada
"""


def ejecutar_benchmark():
    """
    Punto de entrada principal para la ejecución del Benchmark comparativo.
    """
    if not PREGUNTAS_BENCHMARK_PATH.exists():
        print(
            f"❌ Error: No se encuentra el archivo de preguntas en: {PREGUNTAS_BENCHMARK_PATH}")
        return

    print(
        f"📖 Cargando batería de preguntas desde {PREGUNTAS_BENCHMARK_PATH}...")
    with open(PREGUNTAS_BENCHMARK_PATH, "r", encoding="utf-8") as f:
        # Cargamos directamente la lista de preguntas
        preguntas = json.load(f)

    # Si por algún motivo el JSON estuviera envuelto en un diccionario con la clave "preguntas"
    if isinstance(preguntas, dict):
        preguntas = preguntas.get("preguntas", [])

    print(
        f"🚀 Iniciando evaluación comparativa de {len(preguntas)} preguntas de prueba...")

    informe_completo = {}

    # Iteramos sobre las variantes de modelo registradas de manera dinámica
    for model_key in MODELS.keys():
        print(f"🤖 Evaluando variante de modelo: {model_key}...")
        informe_completo[model_key] = ejecutar_evaluacion_modelo(
            model_key, preguntas)

    # Exportar el informe final a la ruta designada de entregables
    print(
        f"💾 Guardando informe consolidado del benchmark en {RESULTADOS_BENCHMARK_PATH}...")
    # Aseguramos que la carpeta contenedora (entregables/) exista antes de escribir
    RESULTADOS_BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(RESULTADOS_BENCHMARK_PATH, "w", encoding="utf-8") as f:
        json.dump(informe_completo, f, indent=4, ensure_ascii=False)

    print("✅ Proceso de Benchmark finalizado con éxito.")


if __name__ == "__main__":
    # 1. Asegurar la existencia del directorio de salida para los reportes
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Ejecutar el proceso de evaluación comparativa del benchmark
    # Esta función iterará sobre los modelos registrados y los casos de prueba
    ejecutar_benchmark()

    # 3. El informe consolidado se guardará automáticamente en RESULTADOS_BENCHMARK_PATH
    # (definido en config.py dentro de /programa/output/)

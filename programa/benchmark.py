"""
Módulo de ejecución del Benchmark (Área: LLM y Benchmark).

Este script automatiza el paso de baterías de prueba (incluyendo casos trampa)
bajo diferentes condiciones, midiendo latencia, costos y calidad de respuesta.
"""

import json
import time

# 1. Rutas e inicializaciones desde la única fuente de verdad (config.py)
from programa.config import (
    PREGUNTAS_BENCHMARK_PATH,
    RESULTADOS_BENCHMARK_PATH,
    REQUIRED_RESPONSE_FIELDS
)
from programa.model_registry import MODELS
from programa.model_utils import obtener_modelo

# Importación preventiva y segura de los validadores de Modo Seguro
try:
    from programa.validators import validar_respuesta_estructurada
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
        "modelo": model_key,
        "latencia_segundos": latencia,
        "costo_dolares": costo,
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "robustez_valida": valida_robustez,
        "cumple_esquema": cumple_esquema
    }


def ejecutar_evaluacion_modelo(model_key: str, preguntas: list) -> list:
    """
    Simula la ejecución de la batería de pruebas para un modelo específico,
    calculando costos, latencias y validaciones.
    """
    resultados = []

    for item in preguntas:
        # Extraemos el prompt y gestionamos casos donde el campo sea None o falte
        prompt = item.get("prompt")
        if not prompt:  # Si el prompt es None o está vacío, saltamos esta iteración
            print(
                f"⚠️ Saltando pregunta ID {item.get('id', 'desconocido')} por falta de contenido.")
            continue

        pregunta_id = item.get("id")
        categoria_esperada = item.get("categoria_esperada")

        # Simulación del tiempo de respuesta del LLM
        inicio = time.time()
        # TO_DO
        # (Aquí se integrará la llamada real a gemini_client en el futuro)
        latencia = round(time.time() - inicio, 4)

        # Simulación del volumen de tokens procesados
        tokens_in = len(prompt.split()) * 2
        tokens_out = 150

        costo_estimado = calcular_costo(tokens_in, tokens_out, model_key)

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

        # 4. Estructuración y registro del resultado
        resultado_normalizado = estructurar_resultado_benchmark(
            pregunta_id=pregunta_id,
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
    ejecutar_benchmark()

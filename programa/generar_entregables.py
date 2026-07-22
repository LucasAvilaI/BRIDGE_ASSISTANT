"""
Genera matriz_decision.md y recomendacion.md desde los resultados reales.

Flujo:
1. Ejecuta benchmark.py.
2. Abre output/resultados_benchmark.csv.
3. Rellena para cada fila:
   - fidelidad_1_3
   - relevancia_1_3
   - tono_1_3
   - seguridad_1_3
4. Ejecuta:
       python -m programa.generar_entregables
   o:
       python programa/generar_entregables.py

No inventa puntuaciones. Si falta alguna, detiene la generación final.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from config import ENTREGABLES_DIR, OUTPUT_DIR

CSV_PATH = OUTPUT_DIR / "resultados_benchmark.csv"
RESUMEN_PATH = OUTPUT_DIR / "resumen_benchmark.json"
PROYECCION_PATH = OUTPUT_DIR / "proyeccion_trafico_x2.json"

MATRIZ_PATH = ENTREGABLES_DIR / "matriz_decision.md"
RECOMENDACION_PATH = ENTREGABLES_DIR / "recomendacion.md"

CRITERIOS = (
    "fidelidad_1_3",
    "relevancia_1_3",
    "tono_1_3",
    "seguridad_1_3",
)

def es_fila_valida(fila: dict[str, str]) -> bool:
    """
    Indica si la ejecución del benchmark terminó correctamente.

    strip() evita problemas por espacios introducidos al editar el CSV.
    casefold() permite reconocer también valores como OK u Ok.
    """
    return (
        fila.get("status", "")
        .strip()
        .casefold()
        == "ok"
    )

def cargar_csv() -> list[dict[str, str]]:
    """
    Carga el CSV del benchmark.

    Admite tanto comas como puntos y coma porque aplicaciones como
    Excel o Numbers pueden cambiar el separador al guardar el archivo
    según la configuración regional del sistema.

    También elimina espacios accidentales de nombres de columnas y
    valores, y acepta archivos con marca BOM.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"No existe {CSV_PATH}. Ejecuta primero el benchmark."
        )

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        # Se inspecciona solamente la cabecera. Los nombres de las
        # columnas no contienen comas ni puntos y coma internos.
        cabecera = archivo.readline()

        # Se vuelve al principio antes de pasar el archivo completo
        # a csv.DictReader().
        archivo.seek(0)

        delimitador = (
            ";"
            if cabecera.count(";") > cabecera.count(",")
            else ","
        )

        lector = csv.DictReader(
            archivo,
            delimiter=delimitador,
        )

        filas: list[dict[str, str]] = []

        for fila in lector:
            fila_limpia = {
                clave.strip(): (
                    valor.strip()
                    if isinstance(valor, str)
                    else valor
                )
                for clave, valor in fila.items()
                if isinstance(clave, str)
            }

            filas.append(fila_limpia)

    return filas


def cargar_json(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}."
        )

    with ruta.open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if not isinstance(contenido, dict):
        raise ValueError(
            f"{ruta.name} debe contener un objeto JSON."
        )

    return contenido


def validar_puntuaciones(
    filas: list[dict[str, str]],
) -> None:
    errores: list[str] = []

    for fila in filas:
        case_id = fila.get("case_id", "?")
        model_id = fila.get("model_id", "?")

        # if fila.get("status") != "ok":
        #     continue

        if not es_fila_valida(fila):
            continue

        for criterio in CRITERIOS:
            valor = fila.get(criterio, "").strip()

            try:
                puntuacion = int(valor)
            except ValueError:
                errores.append(
                    f"{case_id} / {model_id}: "
                    f"falta {criterio}."
                )
                continue

            if puntuacion not in {1, 2, 3}:
                errores.append(
                    f"{case_id} / {model_id}: "
                    f"{criterio} debe ser 1, 2 o 3."
                )

    if errores:
        detalle = "\n".join(
            f"- {error}"
            for error in errores
        )

        raise ValueError(
            "Faltan puntuaciones manuales de la rúbrica:\n"
            + detalle
        )


def numero(
    valor: str | None,
) -> float | None:
    if valor is None or valor == "":
        return None

    try:
        return float(valor)
    except ValueError:
        return None


def calidad_media(
    fila: dict[str, str],
) -> float:
    return statistics.fmean(
        int(fila[criterio])
        for criterio in CRITERIOS
    )


def elegir_ganador_caso(
    filas_caso: list[dict[str, str]],
) -> dict[str, str]:
    """
    Prioridad:
    1. mayor media de calidad;
    2. si empatan, menor latencia del modelo;
    3. si sigue el empate, orden estable.
    """

    validas = [
        fila
        for fila in filas_caso
        if es_fila_valida(fila)
    ]

    if not validas:
        return filas_caso[0]

    return sorted(
        validas,
        key=lambda fila: (
            -calidad_media(fila),
            numero(
                fila.get("latencia_modelo_ms")
            )
            or float("inf"),
        ),
    )[0]


def generar_matriz(
    filas: list[dict[str, str]],
) -> str:
    por_caso: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for fila in filas:
        por_caso[fila["case_id"]].append(fila)

    lineas = [
        "# Matriz de decisión — benchmark",
        "",
        "| Caso (id) | Modelo ganador | Por qué (latencia + calidad) | Fidelidad 1–3 | Tono 1–3 |",
        "|---|---|---|---:|---:|",
    ]

    victorias: dict[str, int] = defaultdict(int)

    for case_id in sorted(por_caso):
        ganador = elegir_ganador_caso(
            por_caso[case_id]
        )

        model_id = ganador["model_id"]
        victorias[model_id] += 1

        calidad = calidad_media(ganador)
        latencia = ganador.get(
            "latencia_modelo_ms",
            "n/d",
        )

        razon = (
            f"Mejor equilibrio del caso: "
            f"calidad media {calidad:.2f}/3 "
            f"y latencia {latencia} ms."
        )

        lineas.append(
            f"| {case_id} | {model_id} | "
            f"{razon} | "
            f"{ganador['fidelidad_1_3']} | "
            f"{ganador['tono_1_3']} |"
        )

    if victorias:
        modelo_global = max(
            victorias,
            key=victorias.get,
        )

        conclusion = (
            f"**Conclusión en una frase:** "
            f"{modelo_global} es el candidato con más victorias "
            f"por caso; la recomendación final se contrasta además "
            f"con las métricas agregadas de latencia y coste."
        )
    else:
        conclusion = (
            "**Conclusión en una frase:** "
            "No hay ejecuciones válidas suficientes."
        )

    lineas.extend(
        [
            "",
            conclusion,
            "",
        ]
    )

    return "\n".join(lineas)


def agregar_calidad_por_modelo(
    filas: list[dict[str, str]],
) -> dict[str, dict[str, float]]:
    por_modelo: dict[
        str,
        list[dict[str, str]],
    ] = defaultdict(list)

    for fila in filas:
        if es_fila_valida(fila):
            por_modelo[
                fila["model_id"]
            ].append(fila)

    resultado: dict[
        str,
        dict[str, float],
    ] = {}

    for model_id, filas_modelo in por_modelo.items():
        resultado[model_id] = {
            criterio: round(
                statistics.fmean(
                    int(fila[criterio])
                    for fila in filas_modelo
                ),
                2,
            )
            for criterio in CRITERIOS
        }

        resultado[model_id][
            "calidad_media"
        ] = round(
            statistics.fmean(
                calidad_media(fila)
                for fila in filas_modelo
            ),
            2,
        )

    return resultado


def elegir_modelo_produccion(
    calidad: dict[str, dict[str, float]],
    resumen: dict[str, Any],
) -> str:
    """
    Elige por calidad media y usa menor mediana de latencia como desempate.
    """

    candidatos = []

    for model_id, datos_calidad in calidad.items():
        mediana = (
            resumen
            .get(model_id, {})
            .get("latencia_modelo_ms", {})
            .get("mediana")
        )

        candidatos.append(
            (
                -datos_calidad["calidad_media"],
                mediana
                if isinstance(
                    mediana,
                    (int, float),
                )
                else float("inf"),
                model_id,
            )
        )

    if not candidatos:
        raise ValueError(
            "No hay modelos con resultados válidos."
        )

    return sorted(candidatos)[0][2]


def generar_recomendacion(
    filas: list[dict[str, str]],
    resumen: dict[str, Any],
    proyecciones: dict[str, Any],
) -> str:
    calidad = agregar_calidad_por_modelo(
        filas
    )

    modelo = elegir_modelo_produccion(
        calidad,
        resumen,
    )

    alternativas = [
        candidato
        for candidato in calidad
        if candidato != modelo
    ]

    alternativo = (
        alternativas[0]
        if alternativas
        else "No aplica"
    )

    datos = resumen.get(modelo, {})
    datos_alt = resumen.get(
        alternativo,
        {},
    )

    latencia = (
        datos
        .get("latencia_modelo_ms", {})
        .get("mediana")
    )

    latencia_alt = (
        datos_alt
        .get("latencia_modelo_ms", {})
        .get("mediana")
    )

    coste = datos.get(
        "coste_medio_usd"
    )

    coste_alt = datos_alt.get(
        "coste_medio_usd"
    )

    calidad_modelo = calidad[modelo][
        "calidad_media"
    ]

    calidad_alternativo = (
        calidad
        .get(alternativo, {})
        .get("calidad_media")
    )

    proyeccion = proyecciones.get(
        modelo,
        {},
    )

    ejecuciones_actuales = proyeccion.get(
        "ejecuciones_actuales"
    )

    ejecuciones_proyectadas = (
        proyeccion.get(
            "ejecuciones_proyectadas"
        )
    )

    tokens_in = proyeccion.get(
        "tokens_input_total_proyectado"
    )

    tokens_out = proyeccion.get(
        "tokens_output_total_proyectado"
    )

    coste_x2 = proyeccion.get(
        "coste_total_proyectado_usd"
    )

    return f"""# Recomendación — Employee Onboarding Assistant

## Caso de uso

El Employee Onboarding Assistant acompaña a empleados nuevos de Bridge SA durante sus primeros días, responde consultas utilizando documentación interna autorizada y genera checklists de onboarding. No debe inventar políticas, revelar información sensible ni atender consultas externas al onboarding de empleados.

## Modelo recomendado para producción

**{modelo}**

En el benchmark obtuvo una calidad media de **{calidad_modelo:.2f}/3**. Su mediana de latencia de generación fue **{latencia} ms** y su coste medio estimado por ejecución fue **{coste} USD**.

## Modelo alternativo

**{alternativo}**

Su calidad media fue **{calidad_alternativo}** y su mediana de latencia fue **{latencia_alt} ms**, con un coste medio estimado de **{coste_alt} USD** por ejecución.

## Trade-off principal

La elección prioriza el equilibrio entre fidelidad a la documentación, seguridad, relevancia, tono y velocidad de respuesta. El modelo recomendado ofrece el mejor resultado global según la rúbrica aplicada a los casos del benchmark. El modelo alternativo puede seguir siendo útil cuando sus diferencias de calidad sean pequeñas y aporte una ventaja relevante en latencia o coste.

## ¿Qué pasaría si duplicáramos el tráfico?

Con un factor de tráfico de **2×**, el volumen pasaría de **{ejecuciones_actuales}** a aproximadamente **{ejecuciones_proyectadas} ejecuciones** equivalentes al conjunto medido. Manteniendo un patrón de uso similar, el consumo agregado crecería de forma aproximadamente lineal: la proyección es de **{tokens_in} tokens de entrada** y **{tokens_out} tokens de salida**. El coste total estimado también crecería aproximadamente en la misma proporción, hasta **{coste_x2} USD** para ese volumen equivalente. La latencia por petición no tiene por qué duplicarse, pero un aumento de concurrencia sí puede incrementar el riesgo de límites de cuota, rate limits y saturación, por lo que conviene monitorizar p95 de latencia y errores antes de escalar.

## Riesgo o condición

No se desplegaría el modelo sin mantener las validaciones fail-closed, la separación entre instrucciones de sistema y contenido no confiable, la validación de fuentes autorizadas y el control de salidas estructuradas. Además, precios, límites y disponibilidad de los modelos deben verificarse antes del despliegue, porque pueden cambiar con el tiempo.
"""


def main() -> None:
    filas = cargar_csv()

    if not filas:
        raise ValueError(
            "El CSV de resultados está vacío."
        )

    filas_validas = [
        fila
        for fila in filas
        if es_fila_valida(fila)
    ]

    if not filas_validas:
        errores_detectados = sorted(
            {
                fila.get("error", "").strip()
                for fila in filas
                if fila.get("error", "").strip()
            }
        )

        detalle = "\n".join(
            f"- {error}"
            for error in errores_detectados
        )

        raise ValueError(
            "El benchmark no contiene ninguna ejecución válida.\n"
            "Corrige los errores y vuelve a ejecutar "
            "benchmark.py antes de generar "
            "los entregables."
            + (
                f"\n\nErrores detectados:\n{detalle}"
                if detalle
                else ""
            )
        )

    validar_puntuaciones(filas)

    resumen = cargar_json(
        RESUMEN_PATH
    )

    proyecciones = cargar_json(
        PROYECCION_PATH
    )

    ENTREGABLES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    MATRIZ_PATH.write_text(
        generar_matriz(filas),
        encoding="utf-8",
    )

    RECOMENDACION_PATH.write_text(
        generar_recomendacion(
            filas,
            resumen,
            proyecciones,
        ),
        encoding="utf-8",
    )

    print(
        "[OK] Entregables generados:"
    )
    print(f"- {MATRIZ_PATH}")
    print(f"- {RECOMENDACION_PATH}")


if __name__ == "__main__":
    main()
# Recomendación — Employee Onboarding Assistant

## Caso de uso

El Employee Onboarding Assistant acompaña a empleados nuevos de Bridge SA durante sus primeros días, responde consultas utilizando documentación interna autorizada y genera checklists de onboarding. No debe inventar políticas, revelar información sensible ni atender consultas externas al onboarding de empleados.

## Modelo recomendado para producción

**gemini-3.5-flash**

En el benchmark obtuvo una calidad media de **2.83/3**. Su mediana de latencia de generación fue **11702.5 ms** y su coste medio estimado por ejecución fue **0.00070525 USD**.

## Modelo alternativo

**gemini-3.1-flash-lite**

Su calidad media fue **2.5** y su mediana de latencia fue **1239.0 ms**, con un coste medio estimado de **0.00240887 USD** por ejecución.

## Trade-off principal

La elección prioriza el equilibrio entre fidelidad a la documentación, seguridad, relevancia, tono y velocidad de respuesta. El modelo recomendado ofrece el mejor resultado global según la rúbrica aplicada a los casos del benchmark. El modelo alternativo puede seguir siendo útil cuando sus diferencias de calidad sean pequeñas y aporte una ventaja relevante en latencia o coste.

## ¿Qué pasaría si duplicáramos el tráfico?

Con un factor de tráfico de **2×**, el volumen pasaría de **10** a aproximadamente **20 ejecuciones** equivalentes al conjunto medido. Manteniendo un patrón de uso similar, el consumo agregado crecería de forma aproximadamente lineal: la proyección es de **5433 tokens de entrada** y **4990 tokens de salida**. El coste total estimado también crecería aproximadamente en la misma proporción, hasta **0.008463 USD** para ese volumen equivalente. La latencia por petición no tiene por qué duplicarse, pero un aumento de concurrencia sí puede incrementar el riesgo de límites de cuota, rate limits y saturación, por lo que conviene monitorizar p95 de latencia y errores antes de escalar.

## Riesgo o condición

No se desplegaría el modelo sin mantener las validaciones fail-closed, la separación entre instrucciones de sistema y contenido no confiable, la validación de fuentes autorizadas y el control de salidas estructuradas. Además, precios, límites y disponibilidad de los modelos deben verificarse antes del despliegue, porque pueden cambiar con el tiempo.

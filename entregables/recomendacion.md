# Recomendación — Employee Onboarding Assistant

## Caso de uso

El Employee Onboarding Assistant acompaña a empleados nuevos de Bridge SA durante sus primeros días, responde consultas utilizando documentación interna autorizada y genera checklists de onboarding. No debe inventar políticas, revelar información sensible ni atender consultas externas al onboarding de empleados.

## Modelo recomendado para producción

**gemini-3.1-flash-lite**

En el benchmark obtuvo una calidad media de 2.95/3 y completó correctamente el 100 % de las ejecuciones, sin errores técnicos. Su mediana de latencia de generación fue de 1193.0 ms y su coste medio estimado por ejecución fue de 0.00036847 USD.

## Modelo alternativo

**gemini-3.5-flash**

Obtuvo una calidad media de 3.00/3 en las ejecuciones válidas, pero registró tres errores técnicos 503/504 en diez casos. Su mediana de latencia de generación fue de 11209.0 ms y su coste medio estimado por ejecución fue de 0.0023595 USD.

## Trade-off principal

La elección prioriza el equilibrio entre calidad, disponibilidad, velocidad y coste. Aunque gemini-3.5-flash obtuvo una calidad media ligeramente superior en las respuestas completadas, la diferencia fue únicamente de 0.05 puntos. Esta mejora no compensa su 70 % de disponibilidad observada, una latencia aproximadamente 9.4 veces mayor y un coste medio unas 6.4 veces superior.

## ¿Qué pasaría si duplicáramos el tráfico?

Con un factor de tráfico de 2×, el volumen pasaría de 10 a aproximadamente 20 ejecuciones equivalentes al conjunto medido. Manteniendo un patrón de uso similar, el consumo agregado crecería de forma aproximadamente lineal: la proyección es de **5166 tokens de entrada** y **4052 tokens de salida**.

El coste total estimado también crecería aproximadamente en la misma proporción, **pasando de 0.00368475 USD a 0.00737 USD** para ese volumen equivalente.

La latencia por petición no tiene por qué duplicarse, pero un aumento de concurrencia sí puede incrementar el riesgo de límites de cuota, rate limits y saturación. Por ello, conviene monitorizar el p95 de latencia, la tasa de errores y la disponibilidad antes de escalar.

## Riesgo o condición

No se desplegaría el modelo sin mantener las validaciones fail-closed, la separación entre instrucciones de sistema y contenido no confiable, la validación de fuentes autorizadas y el control de salidas estructuradas. Además, precios, límites y disponibilidad de los modelos deben verificarse antes del despliegue, porque pueden cambiar con el tiempo.

# Recomendación — Employee Onboarding Assistant

## Caso de uso

El Employee Onboarding Assistant acompaña a los nuevos empleados de Bridge SA durante su proceso de incorporación, resolviendo consultas a partir de documentación interna autorizada y generando checklists de onboarding. El sistema está diseñado para no inventar políticas, no revelar información sensible y rechazar consultas fuera del ámbito del onboarding.

---

## Modelo recomendado para producción

**gemini-3.1-flash-lite**

Es el único modelo que pudo evaluarse completamente durante el benchmark. Completó correctamente los diez casos definidos, ofreciendo respuestas consistentes, baja latencia y un coste reducido por ejecución.

Resultados obtenidos:

- Calidad funcional: **10/10 casos completados**
- Mediana de latencia: **≈ 1,6 s**
- Coste estimado por ejecución: **muy reducido**, adecuado para un asistente de uso frecuente.

---

## Modelo alternativo

**gemini-3.5-flash**

No ha podido evaluarse correctamente durante esta iteración del benchmark debido a errores repetidos **503 UNAVAILABLE** devueltos por el servicio de Gemini en todas las ejecuciones.

Por este motivo no ha sido posible obtener métricas comparables de:

- fidelidad;
- relevancia;
- tono;
- seguridad;
- latencia;
- coste.

La evaluación deberá repetirse cuando el servicio vuelva a estar disponible.

---

## Trade-off principal

En la situación actual se prioriza **Gemini 3.1 Flash-Lite**, ya que ha demostrado un funcionamiento estable durante todas las pruebas funcionales y el benchmark ejecutado.

Aunque Gemini 3.5 Flash está orientado a proporcionar una mayor capacidad de razonamiento, no ha podido ser evaluado objetivamente debido a la indisponibilidad temporal del servicio, por lo que no es posible justificar su adopción basándose en resultados experimentales.

---

## ¿Qué pasaría si duplicáramos el tráfico?

Si el volumen de consultas se duplicara, el consumo de tokens y el coste crecerían aproximadamente de forma lineal.

Dado el buen comportamiento observado de Gemini 3.1 Flash-Lite en latencia y estabilidad, el sistema podría absorber un mayor volumen de peticiones siempre que se monitoricen:

- latencia p95;
- consumo de tokens;
- límites de cuota de la API;
- errores transitorios del proveedor.

---

## Riesgos y condiciones

Antes del despliegue en producción deben mantenerse las medidas de seguridad implementadas en el sistema:

- validación _fail-closed_;
- separación entre instrucciones del sistema y entradas del usuario;
- uso exclusivo de documentación autorizada;
- validación del contrato JSON devuelto por el modelo;
- rechazo de consultas fuera del dominio y de intentos de prompt injection.

Asimismo, la disponibilidad, límites de uso y precios de los modelos de Gemini deberán verificarse antes del despliegue definitivo, ya que pueden variar con el tiempo. Una vez que Gemini 3.5 Flash vuelva a estar disponible, se recomienda repetir el benchmark para disponer de una comparación completa entre ambos modelos.

# Team Challenge: Sprint 05-07 — Employee Onboarding Assistant

#### 1. Introducción
El objetivo de este documento es describir la organización del proyecto **Employee Onboarding Assistant** para la empresa **Bridge SA**, correspondiente al reto de los Sprints 05, 06 y 07 del bootcamp de **AI Engineering** de **The Bridge**. 

El proyecto consiste en construir un copiloto que acompañe a los empleados nuevos en sus primeros días, integrando conceptos avanzados de **Prompt & Context Engineering**, **Robustez de asistentes** y **evaluación de modelos**.

--------------------------------------------------------------------------------

#### 2. Equipo de Programadores
El equipo está compuesto por los siguientes programadores, todos con el mismo nivel de responsabilidad:

*   **Alejandra del Carme Eng Broca**
*   **Alex Bometon**
*   **Enric Parella**
*   **Lucas Ávila Nebreda**

##### Scrum Master
El Scrum Master, responsable de la creación del repositorio original y de la validación final de las *Pull Requests*, es:
*   **Lucas Ávila Nebreda**

##### Trello Master
La responsable de la organización del tablero de tareas y el seguimiento del flujo de trabajo en Trello es:
*   **Alejandra del Carme Eng Broca**

--------------------------------------------------------------------------------

#### 3. Reunión de Kick off y Reparto de Tareas
El **12 de julio de 2026**

**Reparto de tareas:** (A definir por el equipo durante las sesiones de trabajo).

--------------------------------------------------------------------------------

#### 4. Uso de Git y Estrategia de Ramas
Para garantizar un aprendizaje profundo de Git y evitar conflictos en el código modular, se ha decidido seguir la siguiente estrategia basada en el flujo del trabajo anterior:

*   Se mantendrán las ramas de integración constantes: **main** (código estable) y **develop** (integración).
*   El trabajo individual o por bloques se distribuirá mediante **ramas por nombre de programador** (ej. `lucas`, `alejandra`, `alex`, `enric`) para el desarrollo inicial de las funcionalidades.
*   **Flujo de trabajo:** Cada vez que un programador avance en una tarea, realizará un *pull* de `develop` en local, mergeará con su rama, hará *push* a GitHub y abrirá un **Pull Request (PR)** hacia `develop` para que sea revisado por el Scrum Master.
*   Se prohíbe trabajar directamente sobre la rama `main`.

--------------------------------------------------------------------------------

#### 5. Ramas: Estructura y su responsable
| Nombre de la rama | Programador responsable |
| ------ | ------ |
| lucas | Lucas Ávila Nebreda |
| alejandra | Alejandra del Carme Eng Broca |
| alex | Alex Bometon |
| enric | Enric Parella |

*(Nota: Se podrán crear ramas secundarias tipo `feature/` o `fix/` según la necesidad del bloque de trabajo, siempre naciendo desde `develop`)*

--------------------------------------------------------------------------------

#### 6. Arquitectura y Fases del Proyecto Completo
El desarrollo del asistente se divide en 4 grandes bloques interconectados:

##### Parte 1 — Contexto y Datos
*   Análisis del trasfondo de Bridge SA y sus documentos internos (`empresa.json`, `onboarding_docs.json`).
*   Acuerdo de criterios para la escalación a departamentos (RRHH, IT, etc.).

##### Parte 2 — Asistente Modular
*   Implementación del cliente LLM y selección de contexto dinámico.
*   Construcción de prompts con historial conversacional (máx. 4 turnos) e integración del **checklist JSON** para el seguimiento del onboarding.

##### Parte 3 — Robustez y Seguridad
*   Capa de validación de entrada para detectar inyecciones y mensajes fuera de dominio.
*   Implementación de lógica **fail-closed** (no llamar al modelo si la validación falla) y creación de 5 casos trampa propios.

##### Parte 4 — Benchmark y Decisión de Modelo
*   Creación de un dataset de prueba (mín. 10 casos) y comparativa de rendimiento entre **2 modelos** bajo las mismas condiciones.
*   Generación de informes de latencia, tokens y matriz de decisión final.

--------------------------------------------------------------------------------

#### 7. Tecnologías y Herramientas Utilizadas
*   **Lenguaje:**  Python 3.x
*   **Entorno:**  Jupyter Notebooks (.ipynb)
*   **Librerías Clave:**  Pandas, NumPy, Requests (API), Scikit-Learn, Matplotlib / Seaborn.
*   **Control de Versiones:**  Git & GitHub

--------------------------------------------------------------------------------

#### 8. Clonar repositorio y activar entorno virtual
En terminal donde queramos guardar el repo del proyecto:

```bash
git clone <url_del_repositorio>
cd <nombre_del_repositorio>
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### 9. Workflow push rama
Para subir tus cambios de forma segura siguiendo la estrategia de ramas del equipo, utiliza los siguientes comandos en tu terminal:

```bash
# 1. Asegúrate de estar en tu rama personal
git checkout <tu_nombre_de_rama>

# 2. Trae los últimos cambios de la rama de integración
git pull origin develop

# 3. Mezcla los cambios de develop en tu rama (resuelve conflictos si aparecen)
git merge develop

# 4. Añade tus archivos y realiza el commit siguiendo la sintaxis oficial
git add .
git commit -m "feat: descripción breve de lo que has hecho"

# 5. Sube tus cambios a GitHub
git push origin <tu_nombre_de_rama>

# 6. Abre un Pull Request (PR) en GitHub desde tu rama hacia 'develop'
```

#### 10. Sintaxis commits

| Prefijo | Como usarlo | ejemplo |
|---------|---------|---------|
|feat:|Nueva funcionalidad|feat: función fetch_movie_details con TMDB|
|fix:|Corrección de bug|fix: manejar tmdbId nulo en links.csv|
|docs:|Documentación|docs: añadir instrucciones de claves en README|
|refactor:|Refactorización sin cambio funcional|refactor: extraer groupby a función separada|
|chore:|Tareas de mantenimiento|chore: actualizar requirements.txt|




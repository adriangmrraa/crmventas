---
description: Scaffolding automático para nuevos proyectos Antigravity. Vincula Workflows/Skills globales y se contextualiza con la Memoria del Proyecto.
---

# 🏗️ Antigravity New Project Setup

1.  **Preguntar Nombre**: Solicita el nombre del proyecto.
2.  **Crear Directorio**: `mkdir [NombreProyecto]`.
3.  **Crear estructura de directorios**:
    ```bash
    mkdir -p .agent/workflows .agent/skills
    ```
4.  **Copiar reglas globales (si existen)**:
    ```bash
    # Copiar desde el proyecto base si se dispone de uno
    cp -r ../base_agent/workflows/* .agent/workflows/ 2>/dev/null || echo "No global workflows found, starting fresh."
    cp -r ../base_agent/skills/* .agent/skills/ 2>/dev/null || echo "No global skills found, starting fresh."
    cp ../base_agent/.antigravity_rules .antigravity_rules 2>/dev/null || echo "No global rules found."
    ```
5.  **Contextualización Inmediata**:
    - **Acción del Agente**: Debes leer e interpretar obligatoriamente los archivos de reglas globales para asegurar consistencia arquitectónica.
6.  **Estructura de Carpetas**:
    - `src/`: Código fuente.
    - `docs/specs/`: Especificaciones `.spec.md`.
    - `docs/plans/`: Planes de implementación.
7.  **Inicialización**:
    - `git init`
    - Inicializar el entorno según el lenguaje del proyecto.
8.  **Siguiente Paso**:
    - Invoca automáticamente `/advisor` para empezar a discutir la idea del proyecto.

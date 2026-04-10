# Definición de sprints

En esta carpeta se definen los archivos de sprint que consume el orchestrator.

## Convención recomendada

- Crear un archivo por sprint (por ejemplo: `sprint_001.md` o `sprint_auth_v1.md`).
- Mantener alcance claro, tareas y entregables verificables.
- Alinear siempre el contenido con `docs/ARCHITECTURE_V1_FINAL.md`.

## Uso con el orchestrator

Ejemplo:

```bash
python agents/orchestrator.py --sprint sprint_001.md
```

El valor de `--sprint` debe corresponder al nombre de un archivo dentro de `agents/sprints/`.

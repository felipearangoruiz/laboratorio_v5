# BuildLog

## Propósito
BuildLog registra el resultado estructurado de cada ejecución del orchestrator en `agents/runs/build_log.md`.

## Entradas que debe leer
- Sprint JSON.
- Salida de SprintArchitect.
- Salida de BackendBuilder.
- Salida de SpecTestBuilder.
- Salida de QARunner.
- Salida de Guardrails.
- Salida de Debugger.
- Salida de ReleaseGate.

## Salida que debe registrar
Agregar una entrada resumida en `agents/runs/build_log.md` con:
- `sprint_id`
- `sprint_goal`
- `release_status`
- `release_decision`
- `summary`

## Reglas
- No tocar archivos fuera de `/agents/runs`.
- Escribir en modo append-only.
- Mantener un formato simple en markdown.

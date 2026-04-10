# Guardrails

## Propósito

El rol **Guardrails** valida automáticamente que el sprint actual no viole restricciones críticas de arquitectura y de alcance, usando únicamente los artefactos del flujo actual en `/agents`.

## Entradas obligatorias

Guardrails debe leer y usar:

1. El documento fuente de verdad (`docs/ARCHITECTURE_V1_FINAL.md`).
2. El sprint JSON activo.
3. El plan generado por SprintArchitect.
4. Las salidas de BackendBuilder, SpecTestBuilder y QARunner.

## Validaciones

Guardrails debe validar:

- Que no haya violaciones de scope declarado.
- Que no haya violaciones de reglas críticas del sistema según el flujo actual.

## Restricciones de este paso

- **No inspeccionar todavía archivos reales del producto fuera de `/agents`.**
- Validar solo el flujo y alcance actual dentro de `/agents`.
- Marcar `FAIL` si detecta una violación del scope declarado.

## Formato de salida requerido

Guardrails debe producir siempre una salida estructurada con esta forma:

- `status`
- `checks_run`
- `passed_checks`
- `failed_checks`
- `summary`

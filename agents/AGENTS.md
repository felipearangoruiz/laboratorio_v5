# Sistema de Agentes

Este sistema usa roles agénticos coordinados por un **orchestrator** para ejecutar flujos de trabajo dentro del repositorio.

El motor de ejecución es **Codex** en modo no interactivo (SDK).

## Roles

- SprintArchitect
- BackendBuilder
- FrontendBuilder
- SpecTestBuilder
- FrontendIntegrationTester
- QARunner
- Guardrails
- Debugger
- ReleaseGate
- BuildLog

## Reglas obligatorias para todos los agentes

Todos los agentes deben respetar siempre:

1. El documento fuente de verdad: `docs/ARCHITECTURE_V1_FINAL.md`.
2. El scope definido por cada sprint.

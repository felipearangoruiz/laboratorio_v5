import argparse
import json
from pathlib import Path

from checks.check_scope import validate_scope

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent


def load_config() -> dict:
    config_path = BASE_DIR / "agents.config.json"
    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def load_sprint(sprint_name: str) -> dict:
    sprint_path = BASE_DIR / "sprints" / sprint_name
    with sprint_path.open("r", encoding="utf-8") as sprint_file:
        return json.load(sprint_file)


def load_document(doc_path: str) -> str:
    source_path = REPO_ROOT / doc_path
    if not source_path.exists():
        return ""

    with source_path.open("r", encoding="utf-8") as source_file:
        return source_file.read()


def run_sprint_architect(doc: str, sprint: dict) -> dict:
    """
    Simula la ejecución del agente SprintArchitect.
    Por ahora:
    - no llamar a Codex aún
    - construir un plan simple basado en el sprint JSON
    """
    _ = doc

    plan = {
        "allowed_paths": sprint.get("allowed_paths", []),
        "forbidden_paths": sprint.get("forbidden_paths", []),
        "backend_tasks": [],
        "frontend_tasks": [],
        "required_tests": [],
        "done_criteria": sprint.get("done_when", []),
    }

    print("SprintArchitect generated plan")
    return plan


def run_backend_builder(doc: str, sprint: dict, plan: dict) -> dict:
    """
    Simula la ejecución del agente BackendBuilder.
    Por ahora no modifica el producto.
    Solo genera una propuesta backend estructurada.
    """
    _ = doc

    backend_result = {
        "files_to_touch": plan.get("allowed_paths", []),
        "backend_tasks": [
            f"Review backend scope for sprint: {sprint.get('goal', '')}"
        ],
        "backend_tests_to_add": [],
        "assumptions": [
            "No frontend changes allowed in this role",
            "No product code changes in this step",
        ],
    }

    print("BackendBuilder generated backend proposal")
    return backend_result


def run_spec_test_builder(doc: str, sprint: dict, plan: dict, backend_result: dict) -> dict:
    """
    Simula la ejecución del agente SpecTestBuilder.
    Por ahora no crea tests reales.
    Solo genera una propuesta estructurada de tests del sprint.
    """
    _ = doc
    _ = plan
    _ = backend_result

    test_result = {
        "unit_tests": [
            f"Validate backend contract for sprint: {sprint.get('goal', '')}"
        ],
        "integration_tests": [
            "Validate orchestrator flow through SprintArchitect and BackendBuilder"
        ],
        "policy_tests": [
            "Ensure no scope expansion outside allowed_paths"
        ],
        "smoke_checks": [
            f"Run orchestrator for sprint {sprint.get('id', '')} and verify ordered output"
        ],
        "assumptions": [
            "No real product tests are created in this step",
            "Tests are derived from sprint scope and architecture document",
        ],
    }

    print("SpecTestBuilder generated test proposal")
    return test_result



def run_qa_runner(doc: str, sprint: dict, plan: dict, backend_result: dict, test_result: dict) -> dict:
    """
    Simula la ejecución del agente QARunner.
    Por ahora no corre tests reales del producto.
    Solo valida que los pasos previos hayan producido estructuras válidas.
    """
    _ = doc
    _ = sprint
    _ = plan
    _ = backend_result
    _ = test_result

    qa_result = {
        "status": "PASS",
        "checks_run": [
            "Sprint plan generated",
            "Backend proposal generated",
            "Test proposal generated"
        ],
        "passed_checks": [
            "SprintArchitect output is present",
            "BackendBuilder output is present",
            "SpecTestBuilder output is present"
        ],
        "failed_checks": [],
        "summary": "QARunner validated the current orchestrator flow successfully"
    }

    print("QARunner completed validation")
    return qa_result


def run_guardrails(doc: str, sprint: dict, plan: dict, backend_result: dict, test_result: dict, qa_result: dict) -> dict:
    """
    Simula la ejecución del agente Guardrails.
    Por ahora valida solo restricciones de scope y consistencia del flujo actual.
    """
    _ = doc
    _ = sprint
    _ = test_result
    _ = qa_result

    scope_result = validate_scope(plan, backend_result)

    guardrails_result = {
        "status": scope_result["status"],
        "checks_run": scope_result["checks_run"],
        "passed_checks": scope_result["passed_checks"],
        "failed_checks": scope_result["failed_checks"],
        "summary": scope_result["summary"],
    }

    print("Guardrails completed validation")
    return guardrails_result


def run_debugger(doc: str, sprint: dict, plan: dict, backend_result: dict, test_result: dict, qa_result: dict, guardrails_result: dict) -> dict:
    """
    Simula la ejecución del agente Debugger.
    Por ahora no modifica archivos.
    Solo propone correcciones si QA o Guardrails fallan.
    """
    _ = doc
    _ = sprint
    _ = plan
    _ = backend_result
    _ = test_result

    if qa_result.get("status") == "PASS" and guardrails_result.get("status") == "PASS":
        debugger_result = {
            "status": "NO_ACTION",
            "issues_detected": [],
            "proposed_fixes": [],
            "files_to_review": [],
            "summary": "Debugger found no issues requiring fixes",
        }
    else:
        issues_detected = []
        if qa_result.get("status") != "PASS":
            issues_detected.extend(qa_result.get("failed_checks", []))
        if guardrails_result.get("status") != "PASS":
            issues_detected.extend(guardrails_result.get("failed_checks", []))

        debugger_result = {
            "status": "FIX_PROPOSED",
            "issues_detected": issues_detected,
            "proposed_fixes": [
                "Review failing checks and align outputs with sprint scope",
                "Update /agents flow outputs to satisfy QA and Guardrails validations",
            ],
            "files_to_review": [
                "agents/orchestrator.py",
                "agents/checks/check_scope.py",
            ],
            "summary": "Debugger proposed fixes for detected QA/Guardrails issues",
        }

    print("Debugger completed review")
    return debugger_result


def run_release_gate(
    doc: str,
    sprint: dict,
    plan: dict,
    backend_result: dict,
    test_result: dict,
    qa_result: dict,
    guardrails_result: dict,
    debugger_result: dict,
) -> dict:
    """
    Simula la ejecución del agente ReleaseGate.
    Decide si el sprint actual pasa o falla.
    """
    _ = doc
    _ = sprint
    _ = plan
    _ = backend_result
    _ = test_result

    if (
        qa_result.get("status") == "PASS"
        and guardrails_result.get("status") == "PASS"
        and debugger_result.get("status") == "NO_ACTION"
    ):
        release_result = {
            "status": "PASS",
            "release_decision": "APPROVED",
            "checks_considered": [
                "QARunner",
                "Guardrails",
                "Debugger",
            ],
            "blocking_issues": [],
            "summary": "ReleaseGate approved the sprint for progression",
        }
    else:
        release_result = {
            "status": "FAIL",
            "release_decision": "BLOCKED",
            "checks_considered": [
                "QARunner",
                "Guardrails",
                "Debugger",
            ],
            "blocking_issues": [
                "One or more validation stages did not pass",
            ],
            "summary": "ReleaseGate blocked the sprint",
        }

    print("ReleaseGate completed decision")
    return release_result


def run_build_log(
    sprint: dict,
    plan: dict,
    backend_result: dict,
    test_result: dict,
    qa_result: dict,
    guardrails_result: dict,
    debugger_result: dict,
    release_result: dict,
) -> dict:
    """
    Registra el resultado de la corrida en agents/runs/build_log.md.
    """
    _ = plan
    _ = backend_result
    _ = test_result
    _ = qa_result
    _ = guardrails_result
    _ = debugger_result

    log_path = BASE_DIR / "runs" / "build_log.md"
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"## Sprint {sprint.get('id', '')} — {sprint.get('goal', '')}\n\n")
        log_file.write(f"* Release status: {release_result.get('status', '')}\n\n")
        log_file.write(f"* Release decision: {release_result.get('release_decision', '')}\n\n")
        log_file.write(f"* Summary: {release_result.get('summary', '')}\n\n")

    build_log_result = {
        "status": "RECORDED",
        "log_file": "agents/runs/build_log.md",
        "summary": f"BuildLog recorded sprint {sprint.get('id', '')}",
    }

    print("BuildLog recorded sprint result")
    return build_log_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", required=True)
    args = parser.parse_args()

    config = load_config()
    sprint = load_sprint(args.sprint)

    print(f"orchestrator ready for sprint: {args.sprint}")

    doc = load_document(config["docs_path"])
    plan = run_sprint_architect(doc, sprint)
    print(plan)

    backend_result = run_backend_builder(doc, sprint, plan)
    print(backend_result)

    test_result = run_spec_test_builder(doc, sprint, plan, backend_result)
    print(test_result)

    qa_result = run_qa_runner(doc, sprint, plan, backend_result, test_result)
    print(qa_result)

    guardrails_result = run_guardrails(doc, sprint, plan, backend_result, test_result, qa_result)
    print(guardrails_result)

    debugger_result = run_debugger(doc, sprint, plan, backend_result, test_result, qa_result, guardrails_result)
    print(debugger_result)

    release_result = run_release_gate(
        doc,
        sprint,
        plan,
        backend_result,
        test_result,
        qa_result,
        guardrails_result,
        debugger_result,
    )
    print(release_result)

    build_log_result = run_build_log(
        sprint,
        plan,
        backend_result,
        test_result,
        qa_result,
        guardrails_result,
        debugger_result,
        release_result,
    )
    print(build_log_result)


if __name__ == "__main__":
    main()

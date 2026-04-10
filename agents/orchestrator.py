import argparse
import json
import os
import shlex
import subprocess
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


def load_prompt(prompt_name: str) -> str:
    prompt_path = BASE_DIR / "prompts" / prompt_name
    if not prompt_path.exists():
        return ""

    with prompt_path.open("r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


def load_debug_context(sprint: dict) -> str:
    """
    Carga contexto de debugging si existe un archivo con el mismo id del sprint
    dentro de agents/debug_context/.
    Ejemplo:
    sprint id D1 -> agents/debug_context/D1_frontend_debug.md
    Si no existe, retorna cadena vacía.
    """
    _ = sprint
    debug_context_path = BASE_DIR / "debug_context" / "D1_frontend_debug.md"
    if not debug_context_path.exists():
        return ""

    with debug_context_path.open("r", encoding="utf-8") as debug_context_file:
        return debug_context_file.read()


def run_command(
    command: list[str],
    cwd: Path,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 900,
) -> dict:
    print(f"Running command: {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def collect_repo_state() -> set[str]:
    tracked = run_command(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=REPO_ROOT,
        timeout=60,
    )
    untracked = run_command(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        timeout=60,
    )

    paths: set[str] = set()
    for result in (tracked, untracked):
        for line in result["stdout"].splitlines():
            path = line.strip()
            if path:
                paths.add(path)

    return paths


def is_path_allowed(file_path: str, allowed_paths: list[str]) -> bool:
    normalized = file_path.strip().rstrip("/")
    for allowed_path in allowed_paths:
        allowed = allowed_path.strip().rstrip("/")
        if normalized == allowed or normalized.startswith(f"{allowed}/"):
            return True
    return False


def build_backend_builder_prompt(doc: str, sprint: dict, plan: dict) -> str:
    role_prompt = load_prompt("backend_builder.md")
    sprint_json = json.dumps(sprint, ensure_ascii=False, indent=2)
    plan_json = json.dumps(plan, ensure_ascii=False, indent=2)
    architecture_excerpt = doc[:12000]

    return f"""
You are BackendBuilder running inside the repository root.

Your job is to implement the current sprint by making REAL code changes in this repo.

Hard constraints:
- Touch only files inside these allowed paths: {plan.get("allowed_paths", [])}
- Never touch files inside these forbidden paths: {plan.get("forbidden_paths", [])}
- Do not modify frontend code.
- Keep changes minimal and directly tied to the sprint.
- Prefer editing existing files when possible.
- After applying changes, stop. Do not run frontend work.

Sprint JSON:
{sprint_json}

Execution plan:
{plan_json}

Role prompt:
{role_prompt}

Source of truth excerpt:
{architecture_excerpt}
""".strip()


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
    Ejecuta BackendBuilder usando Codex CLI para aplicar cambios reales en el repo.
    """
    before_state = collect_repo_state()
    prompt = build_backend_builder_prompt(doc, sprint, plan)
    codex_result = run_command(
        ["codex", "exec", "--full-auto", "--cd", str(REPO_ROOT), "-"],
        cwd=REPO_ROOT,
        input_text=prompt,
        timeout=1800,
    )
    after_state = collect_repo_state()

    changed_files = sorted(after_state - before_state)
    disallowed_files = [
        file_path
        for file_path in changed_files
        if not is_path_allowed(file_path, plan.get("allowed_paths", []))
    ]

    status = "PASS"
    assumptions = [
        "Codex CLI executed in non-interactive mode",
        "Scope restricted by sprint allowed_paths and forbidden_paths",
    ]
    if codex_result["returncode"] != 0:
        status = "FAIL"
        assumptions.append("Codex CLI returned a non-zero exit code")
    if disallowed_files:
        status = "FAIL"
        assumptions.append("Codex changed files outside allowed_paths")

    backend_result = {
        "status": status,
        "files_to_touch": plan.get("allowed_paths", []),
        "changed_files": changed_files,
        "disallowed_files": disallowed_files,
        "backend_tasks": [
            f"Implement sprint with Codex: {sprint.get('goal', '')}"
        ],
        "backend_tests_to_add": [],
        "assumptions": assumptions,
        "codex_returncode": codex_result["returncode"],
        "codex_stdout": codex_result["stdout"],
        "codex_stderr": codex_result["stderr"],
    }

    print(f"BackendBuilder completed with status {status}")
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
    Ejecuta tests reales de backend con pytest.
    """
    _ = doc
    _ = sprint
    _ = plan
    _ = test_result

    if backend_result.get("status") != "PASS":
        qa_result = {
            "status": "FAIL",
            "checks_run": ["Skip pytest because Codex execution failed"],
            "passed_checks": [],
            "failed_checks": ["BackendBuilder did not complete successfully"],
            "summary": "QARunner skipped pytest because Codex failed",
            "pytest_returncode": None,
            "pytest_stdout": "",
            "pytest_stderr": "",
        }
        print("QARunner completed validation")
        return qa_result

    config = load_config()
    pytest_command = shlex.split(config["test_command_backend"])
    pytest_env = os.environ.copy()
    pytest_env["PYTHONPATH"] = config["backend_path"]

    pytest_result = run_command(
        pytest_command,
        cwd=REPO_ROOT,
        env=pytest_env,
        timeout=1800,
    )

    status = "PASS" if pytest_result["returncode"] == 0 else "FAIL"

    passed_checks = []
    failed_checks = []
    if status == "PASS":
        passed_checks.append("Backend pytest passed")
    else:
        failed_checks.append("Backend pytest failed")

    qa_result = {
        "status": status,
        "checks_run": [
            f"Run backend tests: {' '.join(pytest_command)}"
        ],
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "summary": (
            "QARunner validated backend tests successfully"
            if status == "PASS"
            else "QARunner detected backend test failures"
        ),
        "pytest_returncode": pytest_result["returncode"],
        "pytest_stdout": pytest_result["stdout"],
        "pytest_stderr": pytest_result["stderr"],
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


def run_debugger(
    doc: str,
    sprint: dict,
    plan: dict,
    backend_result: dict,
    test_result: dict,
    qa_result: dict,
    guardrails_result: dict,
    frontend_result: dict,
    debug_context: str,
) -> dict:
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

    has_frontend_failure = frontend_result.get("status") == "FAIL"
    has_debug_context = bool(debug_context.strip())
    debug_context_lower = debug_context.lower()
    has_admin_404_routes = (
        "404" in debug_context_lower
        and "/admin/" in debug_context_lower
    )
    has_frontend_problem = has_frontend_failure or has_debug_context

    if (
        qa_result.get("status") == "PASS"
        and guardrails_result.get("status") == "PASS"
        and not has_frontend_problem
    ):
        debugger_result = {
            "status": "NO_ACTION",
            "issues_detected": [],
            "proposed_fixes": [],
            "files_to_review": [],
            "summary": "Debugger found no issues requiring fixes",
        }
    else:
        if has_frontend_problem:
            if has_admin_404_routes:
                debugger_result = {
                    "status": "FIX_PROPOSED",
                    "issues_detected": [
                        "Frontend navigation points to non-existent /admin/* routes"
                    ],
                    "proposed_fixes": [
                        "Inspect Next.js app router structure under frontend/app",
                        "Check whether (admin) is a route group instead of a real /admin segment",
                        "Verify redirect targets after login",
                        "Align actual page paths with navigation targets"
                    ],
                    "files_to_review": [
                        "frontend/app",
                        "frontend/app/login",
                        "frontend/middleware.ts",
                        "frontend/lib/session.ts"
                    ],
                    "summary": "Debugger identified a likely route mismatch between navigation targets and Next.js app router structure",
                }
                print("Debugger completed review")
                return debugger_result

            debugger_result = {
                "status": "FIX_PROPOSED",
                "issues_detected": [
                    "Frontend flow is broken (possible blank screen or render failure)"
                ],
                "proposed_fixes": [
                    "Check root frontend entry (e.g. pages/index.tsx or app/page.tsx)",
                    "Verify API integration for auth endpoints",
                    "Check frontend environment variables for backend URL",
                    "Inspect console errors in browser (React render issues)"
                ],
                "files_to_review": [
                    "frontend/pages",
                    "frontend/app",
                    "frontend/lib",
                    "frontend/.env"
                ],
                "summary": "Debugger identified likely frontend failure zones and proposed targeted investigation steps",
            }
            print("Debugger completed review")
            return debugger_result

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


def run_frontend_integration_tester(
    doc: str,
    sprint: dict,
    plan: dict,
    backend_result: dict,
    test_result: dict,
    qa_result: dict,
    guardrails_result: dict,
    debugger_result: dict,
    debug_context: str,
) -> dict:
    """
    Simula la validación del flujo de usuario completo (frontend + backend).
    """
    _ = doc
    _ = plan
    _ = backend_result
    _ = test_result
    _ = qa_result
    _ = guardrails_result
    _ = debugger_result

    if debug_context.strip():
        frontend_result = {
            "status": "FAIL",
            "checked_flows": [
                f"Validate frontend flow for sprint: {sprint.get('goal', '')}"
            ],
            "failed_flows": [
                "Broken frontend flow reported in debug context"
            ],
            "observations": [
                "Debug context loaded from agents/debug_context/D1_frontend_debug.md"
            ],
            "summary": "FrontendIntegrationTester detected a reported frontend issue from debug context",
        }
    else:
        frontend_result = {
            "status": "PASS",
            "checked_flows": [
                f"Validate frontend flow for sprint: {sprint.get('goal', '')}"
            ],
            "failed_flows": [],
            "observations": [
                "Frontend integration simulated (no real browser execution)"
            ],
            "summary": "FrontendIntegrationTester found no blocking issues"
        }

    print("FrontendIntegrationTester completed validation")
    return frontend_result


def run_release_gate(
    doc: str,
    sprint: dict,
    plan: dict,
    backend_result: dict,
    test_result: dict,
    qa_result: dict,
    guardrails_result: dict,
    debugger_result: dict,
    frontend_result: dict,
) -> dict:
    """
    Decide PASS/FAIL basado en la ejecución real de Codex y pytest.
    """
    _ = doc
    _ = sprint
    _ = plan
    _ = test_result
    _ = guardrails_result
    _ = debugger_result
    _ = frontend_result

    blocking_issues = []
    if backend_result.get("status") != "PASS":
        blocking_issues.append("Codex execution failed")
        if backend_result.get("disallowed_files"):
            blocking_issues.append(
                f"Scope violation: {', '.join(backend_result['disallowed_files'])}"
            )

    if qa_result.get("status") != "PASS":
        blocking_issues.append("Backend tests failed")

    status = "PASS" if not blocking_issues else "FAIL"
    release_result = {
        "status": status,
        "release_decision": "APPROVED" if status == "PASS" else "BLOCKED",
        "checks_considered": [
            "BackendBuilder",
            "QARunner",
        ],
        "blocking_issues": blocking_issues,
        "summary": (
            "ReleaseGate approved the sprint after Codex execution and passing tests"
            if status == "PASS"
            else "ReleaseGate blocked the sprint due to Codex or test failures"
        ),
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
    debug_context = load_debug_context(sprint)
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

    frontend_result = run_frontend_integration_tester(
        doc,
        sprint,
        plan,
        backend_result,
        test_result,
        qa_result,
        guardrails_result,
        {},
        debug_context,
    )
    print(frontend_result)

    debugger_result = run_debugger(
        doc,
        sprint,
        plan,
        backend_result,
        test_result,
        qa_result,
        guardrails_result,
        frontend_result,
        debug_context,
    )
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
        frontend_result,
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

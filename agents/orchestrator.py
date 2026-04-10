import argparse
import json
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", required=True)
    args = parser.parse_args()

    config = load_config()
    sprint = load_sprint(args.sprint)

    print(f"Orchestrator ready for sprint: {args.sprint}")

    doc = load_document(config["docs_path"])
    plan = run_sprint_architect(doc, sprint)
    print(plan)

    backend_result = run_backend_builder(doc, sprint, plan)
    print(backend_result)


if __name__ == "__main__":
    main()

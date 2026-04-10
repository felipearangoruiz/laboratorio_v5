def validate_scope(plan: dict, backend_result: dict) -> dict:
    """
    Valida que files_to_touch esté contenido dentro de allowed_paths.
    Devuelve un dict con status PASS o FAIL.
    """
    allowed_paths = set(plan.get("allowed_paths", []))
    files_to_touch = backend_result.get("files_to_touch", [])

    disallowed_files = [
        file_path for file_path in files_to_touch
        if file_path not in allowed_paths
    ]

    checks_run = ["Validate files_to_touch against allowed_paths"]

    if disallowed_files:
        return {
            "status": "FAIL",
            "checks_run": checks_run,
            "passed_checks": [],
            "failed_checks": [
                f"Disallowed paths detected: {', '.join(disallowed_files)}"
            ],
            "summary": "Scope validation failed",
        }

    return {
        "status": "PASS",
        "checks_run": checks_run,
        "passed_checks": ["All files_to_touch are within allowed_paths"],
        "failed_checks": [],
        "summary": "Scope validation passed",
    }

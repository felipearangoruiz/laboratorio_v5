"""Cleanup: marcar AnalysisRuns colgadas en "running" como failed.

Motivación: durante el dry-run del Sprint 0 (commit 5b297d4) se
detectaron 2 corridas en status "running" que quedaron colgadas
probablemente por restart del backend durante ejecución, o por el
cambio de lifetime del access token (15min → 24h, commit 4d88ca6).
Estas corridas no afectan la migración del Sprint 1 pero meten ruido
en el test de compatibilidad del motor del Prompt 1.5 (que valida
counts antes/después de la migración).

REGLAS:
- Modo dry-run por defecto (sin --apply): IDEMPOTENTE y READ-ONLY.
- Modo apply (con --apply): UPDATEs en una sola transacción con rollback
  automático ante error.
- Filtro de seguridad: solo toca corridas con started_at más viejo que
  `--min-hours` (default 24h). Las corridas legítimamente en progreso
  (más recientes que el threshold) quedan intactas.
- NO borra ni toca NodeAnalyses / GroupAnalyses / OrgAnalyses / Findings
  / Recommendations / EvidenceLinks. Esos quedan huérfanos con run_id
  apuntando a una corrida failed — deuda aceptable.

Threshold `--min-hours`:
- Default 24h es el valor seguro para corridas legítimamente largas.
- `--min-hours 6` es apropiado para corridas que por arquitectura
  (gpt-4o-mini + gpt-4o sobre pocas entidades) no deberían exceder
  minutos — usar cuando se sabe que cualquier corrida >6h está stuck.
- Nunca bajar de 1 hora sin razón explícita: por debajo de eso se
  entra en territorio de corridas realmente activas.

Uso:

    # Dry-run con default 24h:
    docker compose exec backend uv run python scripts/cleanup_stale_analysis_runs.py

    # Dry-run con threshold custom:
    docker compose exec backend uv run python scripts/cleanup_stale_analysis_runs.py --min-hours 6

    # Ejecución real:
    docker compose exec backend uv run python scripts/cleanup_stale_analysis_runs.py --min-hours 6 --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Asegurar que /app (backend root) está en sys.path — misma convención
# que migration_dry_run.py.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models.analysis import AnalysisRun  # noqa: E402

# Default del filtro de seguridad: solo tocar corridas que llevan más de
# este tiempo en "running". Cualquier corrida más reciente se respeta
# (puede estar legítimamente en progreso). Override vía --min-hours.
DEFAULT_MIN_HOURS = 24
MIN_ALLOWED_HOURS = 1  # Guardrail: nunca bajar de 1h sin razón explícita.

ERROR_MESSAGE = (
    'Marked as failed retroactively during Sprint 0 cleanup: '
    'run was stuck in "running" state before migration'
)


def find_stale_runs(session: Session, threshold: timedelta) -> list[AnalysisRun]:
    """Devuelve AnalysisRuns en 'running' con started_at más viejo que threshold."""
    cutoff = datetime.now(timezone.utc) - threshold
    stmt = select(AnalysisRun).where(
        AnalysisRun.status == "running",
        AnalysisRun.started_at < cutoff,
    )
    return list(session.exec(stmt).all())


def format_run(run: AnalysisRun, now: datetime) -> str:
    hours = (
        (now - run.started_at).total_seconds() / 3600.0
        if run.started_at is not None
        else None
    )
    hours_str = f"{hours:.1f}h" if hours is not None else "N/A"
    return (
        f"  run_id={run.id} | org_id={run.org_id} | "
        f"started={run.started_at} | {hours_str} colgada"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta el UPDATE real. Sin este flag, solo muestra preview.",
    )
    parser.add_argument(
        "--min-hours",
        type=int,
        default=DEFAULT_MIN_HOURS,
        help=(
            "Threshold en horas: solo tocar corridas con started_at más viejo "
            f"que este valor. Default {DEFAULT_MIN_HOURS}h. "
            f"Mínimo permitido sin autorización explícita: {MIN_ALLOWED_HOURS}h."
        ),
    )
    args = parser.parse_args()

    if args.min_hours < MIN_ALLOWED_HOURS:
        print(
            f"[cleanup] ❌ --min-hours {args.min_hours} es demasiado bajo "
            f"(mínimo permitido: {MIN_ALLOWED_HOURS}h). Abortando.",
            file=sys.stderr,
        )
        return 2

    threshold = timedelta(hours=args.min_hours)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        stale = find_stale_runs(session, threshold)

        if not stale:
            print(
                f"[cleanup] No hay AnalysisRuns colgadas "
                f"(running con started_at > {threshold}). ✅"
            )
            return 0

        print(
            f"[cleanup] Encontradas {len(stale)} corrida(s) colgadas "
            f"(running con started_at > {threshold}):"
        )
        for run in stale:
            print(format_run(run, now))

        if not args.apply:
            print()
            print(
                f"SE VAN A MODIFICAR {len(stale)} CORRIDAS. "
                "Ejecutar con flag --apply para confirmar."
            )
            print()
            print("Cambios que se aplicarían por cada corrida:")
            print("  status: 'running' -> 'failed'")
            print(f"  completed_at: NULL -> {now.isoformat()}")
            print(f"  error_message: None -> {ERROR_MESSAGE!r}")
            return 0

        # Modo apply: UPDATEs en una sola transacción.
        print()
        print(f"[cleanup] --apply recibido. Ejecutando UPDATEs...")
        try:
            for run in stale:
                run.status = "failed"
                run.completed_at = now
                run.error_message = ERROR_MESSAGE
                session.add(run)
                print(f"  ✓ {run.id} marcada como failed")
            session.commit()
            print()
            print(f"[cleanup] ✅ {len(stale)} corrida(s) actualizadas.")
            return 0
        except Exception:
            session.rollback()
            print()
            print("[cleanup] ❌ Error durante el UPDATE. Transacción revertida.")
            raise


if __name__ == "__main__":
    raise SystemExit(main())

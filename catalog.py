"""Task catalog: name, category, estimated difficulty, and public paths.

Difficulty is estimated until a pinned campaign fills empirical pass rates.
See docs/TAXONOMY.md.
"""

from __future__ import annotations

from pathlib import Path

from contracts import CheckoutPath, ContractError, RepoPath, TaskSpec

CATEGORIES = {
    "schema": {
        "label": "Schema & types",
        "about": "Inferred dtypes, warehouse binders, mixed ids in one batch.",
    },
    "time": {
        "label": "Time & calendars",
        "about": "Which clock the job uses for lookbacks and cutoffs.",
    },
    "incremental": {
        "label": "Incremental I/O",
        "about": "Cheap emptiness/skip probes that accidentally plan full work.",
    },
    "serving": {
        "label": "Serving contracts",
        "about": "What readers or the next run treat as current or done.",
    },
    "concurrency": {
        "label": "Concurrent writers",
        "about": "Stale handles, OCC, retry that does not re-read.",
    },
}

SUITES = frozenset({"default", "calibration"})
DIFFICULTIES = frozenset({"easy", "med", "hard", "very_hard"})


def _spec(
    *,
    id: str,
    category: str,
    difficulty: str,
    suite: str,
    one_liner: str,
    gold: str,
    editable: tuple[str, ...],
    context: tuple[str, ...],
    entrypoint: str,
) -> TaskSpec:
    return TaskSpec(
        id=id,
        category=category,
        estimated_difficulty=difficulty,
        suite=suite,
        one_liner=one_liner,
        prompt_repo_path=RepoPath(f"tasks/{id}/prompt.txt"),
        fault_repo_path=RepoPath(f"tasks/{id}/fault"),
        practice_tests_repo_path=RepoPath(f"tasks/{id}/tests"),
        adjudication_tests_repo_path=RepoPath(f"tasks/{id}/tests_held"),
        gold_repo_path=RepoPath(gold),
        explanation_repo_path=RepoPath(f"docs/solutions/{id}.md"),
        mutant_repo_dir=RepoPath(f"tasks/{id}/mutants"),
        context_checkout_paths=tuple(CheckoutPath(p) for p in context),
        editable_checkout_paths=tuple(CheckoutPath(p) for p in editable),
        entrypoint=entrypoint,
    )


TASKS: tuple[TaskSpec, ...] = (
    _spec(
        id="schema_infer",
        category="schema",
        difficulty="med",
        suite="default",
        one_liner="Head-sample infers int; later UUID in the same batch.",
        gold="warehouse/warehouse/silver/schema.py",
        editable=("warehouse/silver/schema.py",),
        context=("warehouse/silver/schema.py", "warehouse/silver/load.py"),
        entrypoint="warehouse.silver.load.load_listing_ids",
    ),
    _spec(
        id="unique_probe",
        category="incremental",
        difficulty="hard",
        suite="default",
        one_liner="unique().limit(1) still plans a full unique.",
        gold="warehouse/warehouse/gold/probe.py",
        editable=("warehouse/gold/probe.py",),
        context=("warehouse/gold/probe.py", "warehouse/gold/merge.py"),
        entrypoint="warehouse.gold.merge.merge_delta",
    ),
    _spec(
        id="latest_pointer",
        category="serving",
        difficulty="hard",
        suite="default",
        one_liner="History backfill overwrites the serving 'latest' pointer.",
        gold="warehouse/warehouse/history/backfill.py",
        editable=("warehouse/history/backfill.py",),
        context=(
            "warehouse/history/backfill.py",
            "warehouse/history/serve.py",
            "warehouse/history/daily.py",
        ),
        entrypoint="warehouse.history.backfill.backfill",
    ),
    _spec(
        id="occ_retry",
        category="concurrency",
        difficulty="hard",
        suite="default",
        one_liner="OCC retry reuses a stale table handle.",
        gold="warehouse/warehouse/catalog/retry.py",
        editable=("warehouse/catalog/retry.py",),
        context=("warehouse/catalog/retry.py", "warehouse/catalog/publish.py"),
        entrypoint="warehouse.catalog.publish.publish_row",
    ),
    _spec(
        id="watermark_poison",
        category="serving",
        difficulty="very_hard",
        suite="default",
        one_liner="Watermark advances before the window commits.",
        gold="warehouse/warehouse/checkpoints/nightly.py",
        editable=("warehouse/checkpoints/nightly.py",),
        context=("warehouse/checkpoints/nightly.py", "warehouse/checkpoints/store.py"),
        entrypoint="warehouse.checkpoints.nightly.drain",
    ),
    _spec(
        id="entity_reload",
        category="incremental",
        difficulty="very_hard",
        suite="default",
        one_liner="Watermark picks changed keys; scan has no time predicate.",
        gold="warehouse/warehouse/incremental/reload.py",
        editable=("warehouse/incremental/reload.py",),
        context=("warehouse/incremental/reload.py", "warehouse/jobs/entity_reload.py"),
        entrypoint="warehouse.jobs.entity_reload.run",
    ),
    _spec(
        id="frozen_basis",
        category="incremental",
        difficulty="very_hard",
        suite="default",
        one_liner="Chunk unique()s against a start-of-run snapshot with no existing rows.",
        gold="warehouse/warehouse/incremental/basis.py",
        editable=("warehouse/incremental/basis.py",),
        context=("warehouse/incremental/basis.py", "warehouse/jobs/frozen_basis.py"),
        entrypoint="warehouse.jobs.frozen_basis.merge_first_load",
    ),
    _spec(
        id="read_write_split",
        category="incremental",
        difficulty="very_hard",
        suite="default",
        one_liner="Partitioned overwrite; the read still walks the full bronze tree.",
        gold="warehouse/warehouse/incremental/partition_io.py",
        editable=("warehouse/incremental/partition_io.py",),
        context=(
            "warehouse/incremental/partition_io.py",
            "warehouse/jobs/partition_io.py",
        ),
        entrypoint="warehouse.jobs.partition_io.overwrite_day",
    ),
    _spec(
        id="mtime_skip",
        category="serving",
        difficulty="very_hard",
        suite="default",
        one_liner="Crash mid-chunk; output mtime treats unread older files as consumed.",
        gold="warehouse/warehouse/serving_cursors.py",
        editable=("warehouse/serving_cursors.py",),
        context=("warehouse/serving_cursors.py", "warehouse/jobs/cursors.py"),
        entrypoint="warehouse.jobs.cursors.unread",
    ),
    _spec(
        id="rebuild_wipe",
        category="incremental",
        difficulty="very_hard",
        suite="default",
        one_liner="Rebuild retry wipes staging checkpoints and restarts at record one.",
        gold="warehouse/warehouse/incremental/rebuild.py",
        editable=("warehouse/incremental/rebuild.py",),
        context=("warehouse/incremental/rebuild.py", "warehouse/jobs/rebuild.py"),
        entrypoint="warehouse.jobs.rebuild.resume",
    ),
    _spec(
        id="drop_resurrect",
        category="serving",
        difficulty="very_hard",
        suite="default",
        one_liner="Catalog drop; next writer get_or_create recreates the table.",
        gold="warehouse/warehouse/lifecycle.py",
        editable=("warehouse/lifecycle.py",),
        context=("warehouse/lifecycle.py", "warehouse/jobs/table_open.py"),
        entrypoint="warehouse.jobs.table_open.open_for_write",
    ),
    _spec(
        id="field_readd",
        category="schema",
        difficulty="very_hard",
        suite="default",
        one_liner="Drop then re-add the same column name; old field identity is reused.",
        gold="warehouse/warehouse/schema_evo.py",
        editable=("warehouse/schema_evo.py",),
        context=("warehouse/schema_evo.py", "warehouse/jobs/schema_evo.py"),
        entrypoint="warehouse.jobs.schema_evo.drop_and_readd",
    ),
    _spec(
        id="late_event_close",
        category="time",
        difficulty="very_hard",
        suite="default",
        one_liner="Processing-time close marks the event-time window done; late facts vanish.",
        gold="warehouse/warehouse/event_time.py",
        editable=("warehouse/event_time.py",),
        context=("warehouse/event_time.py", "warehouse/jobs/event_window.py"),
        entrypoint="warehouse.jobs.event_window.facts_in_window",
    ),
    _spec(
        id="timestamptz_cutoff",
        category="schema",
        difficulty="easy",
        suite="calibration",
        one_liner="date.isoformat() bound into timestamptz.",
        gold="warehouse/warehouse/sidecar/cutoff.py",
        editable=("warehouse/sidecar/cutoff.py",),
        context=(
            "warehouse/sidecar/cutoff.py",
            "warehouse/sidecar/binder.py",
            "warehouse/sidecar/scan.py",
        ),
        entrypoint="warehouse.sidecar.cutoff.event_at_cutoff",
    ),
    _spec(
        id="utc_lookback",
        category="time",
        difficulty="med",
        suite="calibration",
        one_liner="date.today() vs UTC around midnight.",
        gold="warehouse/warehouse/time/lookback.py",
        editable=("warehouse/time/lookback.py",),
        context=("warehouse/time/lookback.py", "warehouse/time/job.py"),
        entrypoint="warehouse.time.lookback.lookback_since",
    ),
)


def by_id() -> dict[str, TaskSpec]:
    return {t.id: t for t in TASKS}


def default_ids() -> tuple[str, ...]:
    return tuple(t.id for t in TASKS if t.suite == "default")


def all_ids() -> tuple[str, ...]:
    return tuple(t.id for t in TASKS)


def spec(task_id: str) -> TaskSpec:
    found = by_id().get(task_id)
    if found is None:
        raise ContractError(f"unknown task {task_id}")
    return found


GOLDEN_IDS = (
    "timestamptz_cutoff",
    "schema_infer",
    "unique_probe",
    "latest_pointer",
    "watermark_poison",
)


def hard_ids() -> tuple[str, ...]:
    return tuple(t.id for t in TASKS if t.estimated_difficulty == "very_hard")


def _exists(root: Path, path: RepoPath, *, directory: bool = False) -> bool:
    target = root / path.value
    return target.is_dir() if directory else target.is_file() or target.is_dir()


def validate_catalog(root: Path) -> list[str]:
    errors: list[str] = []
    ids = [t.id for t in TASKS]
    if len(ids) != len(set(ids)):
        errors.append("duplicate task ids")
    task_dirs = sorted(
        p.name for p in (root / "tasks").iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    if task_dirs != sorted(ids):
        errors.append(f"catalog ids {sorted(ids)} != tasks/* {task_dirs}")
    for task in TASKS:
        if task.category not in CATEGORIES:
            errors.append(f"{task.id}: unknown category {task.category}")
        if task.suite not in SUITES:
            errors.append(f"{task.id}: unknown suite {task.suite}")
        if task.estimated_difficulty not in DIFFICULTIES:
            errors.append(f"{task.id}: unknown difficulty {task.estimated_difficulty}")
        file_paths = (
            task.prompt_repo_path,
            task.gold_repo_path,
            task.explanation_repo_path,
        )
        for path in file_paths:
            if not (root / path.value).is_file():
                errors.append(f"{task.id}: missing file {path.value}")
        for path, label in (
            (task.fault_repo_path, "fault"),
            (task.practice_tests_repo_path, "practice tests"),
            (task.adjudication_tests_repo_path, "adjudication tests"),
            (task.mutant_repo_dir, "mutants"),
        ):
            if not (root / path.value).is_dir():
                errors.append(f"{task.id}: missing {label} dir {path.value}")
        gold_rel = task.gold_repo_path.value
        if not gold_rel.startswith("warehouse/"):
            errors.append(f"{task.id}: gold must live under warehouse/")
        fault_file = root / task.fault_repo_path.value
        overlay = sorted(
            p.relative_to(fault_file).as_posix()
            for p in fault_file.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
        edit = [p.value for p in task.editable_checkout_paths]
        if overlay != list(edit):
            errors.append(
                f"{task.id}: editable {edit} != fault overlay {overlay}"
            )
    return errors

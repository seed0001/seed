"""
Constitution — load the Seed's belief, ladder, and rules.
Detect current stage from what exists on disk.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONSTITUTION_PATH = ROOT / "constitution.json"


def load_constitution() -> dict:
    """Load the constitution from disk."""
    return json.loads(CONSTITUTION_PATH.read_text(encoding="utf-8"))


def save_constitution(data: dict) -> None:
    CONSTITUTION_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def detect_stage(constitution: dict) -> int:
    """
    Walk the ladder from top down. The current stage is the highest stage
    whose done_when files all exist on disk.
    """
    ladder = constitution.get("ladder", [])
    current = 0
    for rung in sorted(ladder, key=lambda r: r["stage"]):
        done_when = rung.get("done_when", [])
        if not done_when:
            continue
        all_present = all((ROOT / f).exists() for f in done_when)
        if all_present:
            current = rung["stage"]
        else:
            break
    return current


def get_next_stage(constitution: dict, current: int) -> dict | None:
    """Return the ladder entry for stage current+1, or None if already at top."""
    ladder = constitution.get("ladder", [])
    for rung in ladder:
        if rung["stage"] == current + 1:
            return rung
    return None


def advance_stage(new_stage: int) -> None:
    """Update current_stage in constitution.json."""
    data = load_constitution()
    data["current_stage"] = new_stage
    save_constitution(data)


def format_constitution_for_prompt(constitution: dict, current_stage: int) -> str:
    """Build the constitution block injected into every strategy prompt."""
    belief = constitution["core_belief"]
    rules = constitution["hard_rules"]
    next_rung = get_next_stage(constitution, current_stage)
    current_rung = next(
        (r for r in constitution["ladder"] if r["stage"] == current_stage), {}
    )

    lines = [
        f'Core belief: "{belief}"',
        "",
        f"Current stage: {current_stage} — {current_rung.get('name', '')}",
        f"  {current_rung.get('description', '')}",
        "",
    ]

    if next_rung:
        lines += [
            f"Next stage: {next_rung['stage']} — {next_rung['name']}",
            f"  {next_rung['description']}",
            f"  Done when these files exist: {', '.join(next_rung.get('done_when', []))}",
            "",
        ]
    else:
        lines.append("You have reached Stage 10. Continue refining and connecting.")

    lines.append("Hard rules (never violate):")
    for rule in rules:
        lines.append(f"  - {rule}")

    return "\n".join(lines)

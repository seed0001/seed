"""
Wire — ensure new modules are imported and called in main.py.
Never leave a new file orphaned.

This is best-effort for files NOT already handled by the LLM's updated main.py.
If the LLM included an updated main.py in the plan, that takes precedence.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def wire_new_files(plan: dict, written_paths: list[Path]) -> None:
    """
    If main.py was NOT part of this plan's output, attempt to inject imports
    for any new Python modules that were written.
    """
    # If main.py was written by the plan, it's already wired — nothing to do
    for p in written_paths:
        if p.name == "main.py" and p.parent == ROOT:
            return

    main_path = ROOT / "main.py"
    if not main_path.exists():
        return

    content = main_path.read_text(encoding="utf-8")
    additions: list[str] = []

    for path in written_paths:
        if not path.suffix == ".py":
            continue
        if path.name == "__init__.py":
            continue

        rel = path.relative_to(ROOT)
        module = str(rel).replace("\\", "/").replace("/", ".").removesuffix(".py")

        # Check if already imported
        if module in content or str(rel) in content:
            continue

        # Add a comment-flagged import so it's visible
        additions.append(f"import {module}  # auto-wired")

    if not additions:
        return

    # Inject after the last existing import line
    lines = content.splitlines()
    last_import_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i

    insert_at = last_import_idx + 1
    for imp in reversed(additions):
        lines.insert(insert_at, imp)

    main_path.write_text("\n".join(lines), encoding="utf-8")

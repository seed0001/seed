"""
Perceive — full view of the codebase.
Structure + content of key files.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "storage"}
SKIP_EXTS = {".pyc", ".pyo", ".json", ".lock", ".log"}
MAX_FILE_CHARS = 3000


def scan_codebase() -> dict:
    """
    Returns {
        "structure": "tree string",
        "files": {"path": "content"} for .py files up to MAX_FILE_CHARS
    }
    """
    structure_lines = []
    files = {}

    for entry in sorted(ROOT.rglob("*")):
        if any(p in entry.parts for p in SKIP_DIRS):
            continue
        if entry.name.startswith("."):
            continue
        if entry.suffix in SKIP_EXTS:
            continue

        rel = entry.relative_to(ROOT)

        if entry.is_dir():
            structure_lines.append(f"  {rel}/")
        elif entry.is_file():
            structure_lines.append(f"  {rel}")
            if entry.suffix == ".py":
                try:
                    content = entry.read_text(encoding="utf-8")
                    files[str(rel)] = content[:MAX_FILE_CHARS]
                except OSError:
                    pass

    return {
        "structure": "\n".join(structure_lines),
        "files": files,
    }


def format_for_prompt(scan: dict, max_files: int = 8) -> str:
    """Format the codebase scan into an LLM-readable block."""
    lines = ["Codebase structure:", scan["structure"], ""]

    # Include the most important files in full
    priority = ["main.py", "constitution.json"]
    shown = []
    for name in priority:
        if name in scan["files"]:
            lines.append(f"--- {name} ---")
            lines.append(scan["files"][name])
            lines.append("")
            shown.append(name)

    count = len(shown)
    for path, content in scan["files"].items():
        if count >= max_files:
            break
        if path in shown:
            continue
        lines.append(f"--- {path} ---")
        lines.append(content[:1500])
        lines.append("")
        count += 1

    return "\n".join(lines)

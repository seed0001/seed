"""
Wire — ensure new modules are connected to main.py.
Adds dynamic try/except blocks, never static top-level imports.
Fragile static imports break on rollback; dynamic blocks fail gracefully.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def wire_new_files(plan: dict, written_paths: list[Path]) -> None:
    """
    If main.py was NOT part of this plan's output, inject a dynamic
    try/except block into the talk() function for each new .py module.
    Skips modules already referenced in main.py.
    """
    # If main.py was (somehow) written by the plan — it's already wired
    for p in written_paths:
        if p.resolve() == (ROOT / "main.py").resolve():
            return

    main_path = ROOT / "main.py"
    if not main_path.exists():
        return

    content = main_path.read_text(encoding="utf-8")
    additions: list[str] = []

    for path in written_paths:
        if path.suffix != ".py":
            continue
        if path.name == "__init__.py":
            continue

        rel = path.relative_to(ROOT)
        module = str(rel).replace("\\", "/").replace("/", ".").removesuffix(".py")

        # Skip if already referenced anywhere in main.py
        if module in content or str(rel).replace("\\", "/") in content:
            continue

        # Build a dynamic-import snippet for the talk() function
        fn_name = path.stem  # e.g. "chat", "manager"
        snippet = (
            f"    try:\n"
            f"        from {module} import run_{fn_name}\n"
            f"        run_{fn_name}()\n"
            f"    except ImportError:\n"
            f"        pass\n"
        )
        additions.append((module, snippet))

    if not additions:
        return

    # Inject snippets at the bottom of the talk() function body,
    # just before the fallback conversation block.
    # We look for the first `def talk()` and insert before the fallback input().
    fallback_marker = "user_input = input("
    if fallback_marker not in content:
        return  # Can't find safe insertion point — skip

    insert_at = content.index(fallback_marker)
    padding = "\n"
    new_block = padding + "".join(snip for _, snip in additions) + "\n"
    content = content[:insert_at] + new_block + content[insert_at:]

    main_path.write_text(content, encoding="utf-8")

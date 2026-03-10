"""
Execute — parse and write multi-file output from the LLM.
Reject placeholders. Verify writes.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Phrases that indicate incomplete code stubs (case-insensitive line check)
# "placeholder" is intentionally excluded -- it's valid in HTML attributes
REJECT_PHRASES = [
    "# placeholder",
    "implement later",
    "# todo",
    "# stub",
    "pass  #",
    "raise notimplementederror",
    "your implementation here",
    "insert code here",
]
MIN_IMPL_LENGTH = 120


def parse_multifile(implementation: str) -> list[tuple[str, str]]:
    """
    Parse # FILE: path.py blocks.
    Returns [(filepath, content), ...].
    """
    blocks: list[tuple[str, str]] = []
    lines = implementation.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("# FILE:"):
            filepath = line[len("# FILE:"):].strip()
            i += 1
            body_lines = []
            while i < len(lines):
                if lines[i].strip().startswith("# FILE:"):
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines).strip()
            if filepath and body:
                blocks.append((filepath, body))
        else:
            i += 1

    return blocks


def _reject(filepath: str, content: str) -> str | None:
    """Return rejection reason if content is invalid, else None."""
    if len(content.strip()) < MIN_IMPL_LENGTH:
        return f"{filepath}: too short ({len(content.strip())} chars)"
    lower = content.lower()
    for phrase in REJECT_PHRASES:
        if phrase in lower:
            return f"{filepath}: contains '{phrase}'"
    return None


def write_files(plan: dict) -> list[Path]:
    """
    Parse plan['implementation'] and write all files to disk.
    Raises ValueError if any file contains placeholders or is too short.
    Verifies each write (read-after-write).
    Returns list of written paths.
    """
    impl = plan.get("implementation", "")
    if not impl:
        raise ValueError("Plan has no implementation")

    blocks = parse_multifile(impl)
    if not blocks:
        raise ValueError("No # FILE: blocks found in implementation")

    # Validate all before writing any
    for filepath, content in blocks:
        reason = _reject(filepath, content)
        if reason:
            raise ValueError(f"Rejected — {reason}")

    written: list[Path] = []
    for filepath, content in blocks:
        path = ROOT / filepath

        # main.py is the permanent base — never allow the LLM to overwrite it
        if path.resolve() == (ROOT / "main.py").resolve():
            raise ValueError(
                "main.py is protected. Grok must NOT include main.py in a plan. "
                "Create standalone modules only."
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        # Read-after-write verification
        actual = path.read_text(encoding="utf-8")
        if actual.strip() != content.strip():
            raise IOError(f"Write verification failed for {filepath}")

        written.append(path)

    return written

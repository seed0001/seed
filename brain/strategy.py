"""
Strategy — ask Grok what to build next.

Reads: constitution (belief + ladder + rules), plan history, codebase.
Returns: a concrete plan with full implementation.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = ROOT / "storage" / "plan_history.json"


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _history_summary(history: list[dict]) -> str:
    if not history:
        return "(none yet)"
    entries = [h.get("description", str(h)) for h in history[-10:]]
    return "\n".join(f"- {e}" for e in entries)


def get_next_plan(constitution: dict, current_stage: int, codebase_scan: dict) -> dict | None:
    """
    Ask Grok to propose the next improvement.
    Returns a plan dict with: description, goal, files, implementation.
    """
    from llm_client import LLMClient
    from soul.constitution import format_constitution_for_prompt
    from brain.perceive import format_for_prompt

    history = _load_history()
    constitution_block = format_constitution_for_prompt(constitution, current_stage)
    codebase_block = format_for_prompt(codebase_scan)
    history_block = _history_summary(history)

    # Inject full source of every base module so Grok can't invent wrong APIs
    llm_client_src = (ROOT / "llm_client.py").read_text(encoding="utf-8")

    system = (
        "You are the Seed — a self-improving agent. "
        "You have full access to your codebase. "
        "You output valid JSON only. No markdown, no explanation outside the JSON."
    )

    # Canonical signatures for every base module Grok might reference
    base_api_reference = """\
=== BASE MODULE SIGNATURES (use ONLY these — do NOT invent new ones) ===

# builder.py
class Builder:
    @staticmethod
    def validate(cwd: str | None = None, target_file: str | None = None) -> tuple[bool, str]:
        \"\"\"Returns (success, error_string).\"\"\"
    @staticmethod
    def validate_all(cwd: str | None, paths: list[str]) -> tuple[bool, str]:
        \"\"\"Validate multiple files. Returns (all_ok, combined_errors).\"\"\"
# NOTE: Builder has NO .repair() method.

# brain/wire.py
def wire_new_files(plan: dict, written_paths: list[Path]) -> None: ...

# brain/execute.py
def write_files(plan: dict) -> list[Path]: ...

# brain/strategy.py
def save_plan(plan: dict) -> None: ...  # ONE argument only — no current_stage
def get_next_plan(constitution: dict, current_stage: int, codebase_scan: dict) -> dict | None: ...

# soul/constitution.py
def load_constitution() -> dict: ...
def detect_stage(constitution: dict) -> int: ...
def advance_stage(new_stage: int) -> None: ...  # ONE integer argument only
def get_next_stage(constitution: dict, current: int) -> dict | None: ...
def format_constitution_for_prompt(constitution: dict, current_stage: int) -> str: ...
"""

    prompt = f"""
{constitution_block}

Plans already completed (do NOT repeat):
{history_block}

Current codebase:
{codebase_block}

---

{base_api_reference}

--- LLMClient full source (use ONLY these methods) ---
{llm_client_src}

LLMClient method summary:
  - llm.chat(system: str, user: str, history: list[dict] | None = None) -> str
  - llm.chat_fast(system: str, user: str, history: list[dict] | None = None) -> str
  - llm.repair(error: str, source_code: str, attempt: int = 1) -> str
  - llm.apply_repair(repair_response: str, original: str) -> str | None
Do NOT invent methods. Do NOT call llm.chat(messages) with a list.

---

Propose ONE concrete improvement that advances you to the next stage.
The improvement must serve your core belief.
It must be immediately implementable — no placeholders, no stubs.

Respond with ONLY this JSON object:
{{
  "description": "One sentence describing what this builds and why",
  "goal": "Which stage this advances toward (e.g. Stage 1: Voice)",
  "files": ["path/to/file1.py", "path/to/file2.py"],
  "implementation": "# FILE: path/to/file1.py\\n[full content]\\n# FILE: path/to/file2.py\\n[full content]"
}}

Requirements:
- Every file in 'files' must appear in 'implementation' with full, runnable code.
- NEVER include main.py in 'files'. main.py is protected and will never be overwritten.
  The system automatically wires new modules into main.py. Just create the module.
- Your module MUST expose a top-level function named run_<module_stem>() that takes
  ZERO arguments. main.py calls it as: run_chat(), run_manager(), etc. — no args ever.
  The function is responsible for all its own I/O (input(), print(), etc.) internally.
  WRONG:  def run_chat(user_input):   <-- breaks main.py
  CORRECT: def run_chat():            <-- correct, handles input internally
- No function stubs. No TODO comments. No incomplete implementations. Every function must
  be complete and runnable end-to-end.
- Use ONLY the base module signatures listed above. Do NOT invent new method names.
"""

    llm = LLMClient()
    raw = llm.chat_fast(system, prompt)

    if not raw or len(raw) < 50:
        return None

    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        plan = json.loads(text)
        if isinstance(plan, dict) and "description" in plan and "implementation" in plan:
            return plan
    except json.JSONDecodeError:
        pass

    return None


def save_plan(plan: dict) -> None:
    """Record a completed plan to history."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = _load_history()
    history.append({"description": plan.get("description", ""), "plan": plan})
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")

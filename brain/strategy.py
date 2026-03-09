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

    # Always inject the full LLMClient interface so generated code calls it correctly
    llm_client_src = (ROOT / "llm_client.py").read_text(encoding="utf-8")

    system = (
        "You are the Seed — a self-improving agent. "
        "You have full access to your codebase. "
        "You output valid JSON only. No markdown, no explanation outside the JSON."
    )

    prompt = f"""
{constitution_block}

Plans already completed (do NOT repeat):
{history_block}

Current codebase:
{codebase_block}

---

CRITICAL — LLMClient interface (you MUST use these exact signatures):
{llm_client_src}

Any code you write that uses LLMClient MUST call it correctly:
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
- Every file in 'files' must appear in 'implementation' with full, runnable code
- If you create a new module, you MUST also include an updated main.py in 'files' and 'implementation'
- No function stubs. No TODO comments. No placeholders. Every function complete.
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

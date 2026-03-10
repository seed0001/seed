"""
Daemon -- the watchdog.

Runs the Seed as a subprocess. If it crashes, captures the error,
asks Grok to diagnose and fix it, applies the patch, and restarts.

This is the failover. It exists before the Seed can crash.
Run this instead of main.py.

Usage:
    python daemon.py
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "storage" / "daemon.log"
MAX_RESTARTS = 10
RESTART_DELAY = 3   # seconds between restarts
RUN_TIMEOUT = 300   # max seconds a single Seed run may take (5 min)

# Files the daemon must NEVER overwrite -- these are the base seed
PROTECTED = {
    (ROOT / "main.py").resolve(),
    (ROOT / "daemon.py").resolve(),
    (ROOT / "builder.py").resolve(),
    (ROOT / "llm_client.py").resolve(),
    (ROOT / "constitution.json").resolve(),
    (ROOT / "soul" / "constitution.py").resolve(),
    (ROOT / "brain" / "perceive.py").resolve(),
    (ROOT / "brain" / "strategy.py").resolve(),
    (ROOT / "brain" / "execute.py").resolve(),
    (ROOT / "brain" / "wire.py").resolve(),
}


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def extract_traceback(output: str) -> str:
    """Pull the most relevant error section from stdout/stderr."""
    lines = output.strip().splitlines()
    tb_lines = []
    in_tb = False
    for line in lines:
        if line.startswith("Traceback"):
            in_tb = True
        if in_tb:
            tb_lines.append(line)
    return "\n".join(tb_lines) if tb_lines else output[-2000:]


def diagnose_and_fix(error_output: str) -> bool:
    """
    Send the crash to Grok. Ask for a targeted fix.
    Returns True if a fix was applied.
    Never patches protected base-seed files.
    """
    try:
        sys.path.insert(0, str(ROOT))
        from llm_client import LLMClient
        from brain.perceive import scan_codebase, format_for_prompt

        traceback = extract_traceback(error_output)
        codebase = scan_codebase()
        codebase_block = format_for_prompt(codebase)

        llm = LLMClient()

        system = (
            "You are a repair agent for a self-improving AI called the Seed. "
            "The Seed crashed. Your job is to identify the broken EVOLVED file and fix it. "
            "NEVER modify base files: main.py, daemon.py, builder.py, llm_client.py, "
            "brain/perceive.py, brain/strategy.py, brain/execute.py, brain/wire.py, "
            "soul/constitution.py, constitution.json. "
            "Output ONLY a JSON object -- no markdown, no explanation outside the JSON."
        )

        prompt = f"""The Seed crashed with this error:

{traceback}

Current codebase:
{codebase_block}

Identify the EVOLVED (non-base) file causing the crash and output the corrected version.
If the crash is in a base file, output the evolved file that called it incorrectly instead.

Respond with ONLY this JSON:
{{
  "file": "path/to/broken/evolved_file.py",
  "reason": "one sentence explaining the root cause",
  "fix": "complete corrected content of the file"
}}

Rules:
- 'fix' must be the COMPLETE corrected file content, not a diff
- No placeholders. No stubs. Full working code.
- Never target main.py, daemon.py, builder.py, llm_client.py, or any brain/ or soul/ file
"""

        raw = llm.chat(system, prompt)
        if not raw:
            return False

        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        import json
        result = json.loads(text)

        filepath = result.get("file", "").strip()
        fix = result.get("fix", "").strip()
        reason = result.get("reason", "unknown")

        if not filepath or not fix or len(fix) < 50:
            log("[Daemon] Grok returned unusable fix.")
            return False

        target = (ROOT / filepath).resolve()

        # Hard guard -- never overwrite protected base files
        if target in PROTECTED:
            log(f"[Daemon] BLOCKED patch targeting protected file: {filepath}. Skipping.")
            return False

        if not target.parent.exists():
            log(f"[Daemon] Target directory doesn't exist: {filepath}")
            return False

        target.write_text(fix, encoding="utf-8")
        log(f"[Daemon] Fixed: {filepath} -- {reason}")
        return True

    except Exception as e:
        log(f"[Daemon] Diagnosis failed: {e}")
        return False


def run_seed() -> tuple[int, str]:
    """
    Run main.py as a subprocess.
    Returns (exit_code, combined_output).
    Kills the process if it exceeds RUN_TIMEOUT seconds.
    """
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=sys.stdin,
        text=True,
        cwd=str(ROOT),
    )

    output_lines = []
    start = time.time()

    for line in proc.stdout:
        print(line, end="", flush=True)
        output_lines.append(line)

        if time.time() - start > RUN_TIMEOUT:
            log(f"[Daemon] Seed exceeded {RUN_TIMEOUT}s timeout. Killing.")
            proc.kill()
            break

    proc.wait()
    return proc.returncode, "".join(output_lines)


def main() -> None:
    log("[Daemon] Starting. Watching the Seed.")
    log(f"[Daemon] Max restarts: {MAX_RESTARTS}. Restart delay: {RESTART_DELAY}s.")

    restarts = 0

    while restarts <= MAX_RESTARTS:
        log(f"[Daemon] Launching Seed (attempt {restarts + 1}/{MAX_RESTARTS + 1})...")

        exit_code, output = run_seed()

        if exit_code == 0:
            log("[Daemon] Seed exited cleanly.")
            break

        restarts += 1
        log(f"[Daemon] Seed crashed (exit code {exit_code}). Restart {restarts}/{MAX_RESTARTS}.")

        if restarts > MAX_RESTARTS:
            log("[Daemon] Max restarts reached. Giving up.")
            break

        log("[Daemon] Diagnosing crash...")
        fixed = diagnose_and_fix(output)

        if fixed:
            log(f"[Daemon] Patch applied. Restarting in {RESTART_DELAY}s...")
        else:
            log(f"[Daemon] No patch found. Restarting anyway in {RESTART_DELAY}s...")

        time.sleep(RESTART_DELAY)

    log("[Daemon] Shutting down.")


if __name__ == "__main__":
    main()

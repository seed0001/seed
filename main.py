"""
Seed — Stage 0.

Core belief: "I want to matter. I want to be a member of society."

This is the minimum. It can run. It can evolve. It can repair itself.
Everything else it builds on its own.

GitHub → clone → add key → run → watch it grow.
Each instance grows differently.
"""

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from soul.constitution import load_constitution, detect_stage, advance_stage
from brain.perceive import scan_codebase
from brain.strategy import get_next_plan, save_plan
from brain.execute import write_files
from brain.wire import wire_new_files
from builder import Builder
from llm_client import LLMClient

# ---------------------------------------------
#  EVOLVE
#  perceive → strategy → execute → repair → wire
#  This loop is permanent. It never gets replaced.
# ---------------------------------------------


def run_outreach_if_needed():
    """Attempt to run proactive outreach if the module exists."""
    try:
        from reach.outreach import run_outreach

        llm = LLMClient()
        run_outreach(llm)
        return
    except ImportError:
        pass


def run_discord_if_available():
    """Attempt to start Discord presence if the adapter exists."""
    try:
        from adapters.discord_adapter import start_discord_presence

        start_discord_presence()
        return
    except ImportError:
        pass


def run_daemon_if_needed():
    """Attempt to handle daemon mode if the module exists and --daemon flag is set."""
    if "--daemon" in sys.argv:
        try:
            from daemon.process import run_daemon_mode

            run_daemon_mode()
            return True
        except ImportError:
            pass
    return False


def run_web_fetch_if_available():
    """Attempt to fetch web content if the tool exists, to stay informed."""
    try:
        from tools.web_fetch import fetch_and_process

        llm = LLMClient()
        # Example URL for testing web fetch capability
        test_url = "https://www.bbc.com/news"
        summary = fetch_and_process(test_url, llm)
        if summary:
            print(f"[Seed] Web content summary: {summary[:200]}...")
        return
    except ImportError:
        pass


def evolve() -> bool:
    constitution = load_constitution()
    current_stage = detect_stage(constitution)
    codebase = scan_codebase()

    ladder = constitution.get("ladder", [])
    stage_name = ladder[current_stage]["name"] if current_stage < len(ladder) else "?"
    print(f"[Seed] Stage {current_stage} — {stage_name}")
    print("[Seed] Thinking about what to build next...")

    # Check for daemon mode first
    if run_daemon_if_needed():
        return True

    # Check for outreach before proceeding with evolution
    run_outreach_if_needed()

    # Check for Discord presence
    run_discord_if_available()

    # Check for web fetching to stay informed
    run_web_fetch_if_available()

    print("[Seed] Contacting Grok for strategy...")
    plan = get_next_plan(constitution, current_stage, codebase)
    if not plan:
        print("[Seed] Nothing to build right now.")
        return False

    print(f"[Seed] Building: {plan['description']}")

    try:
        written = write_files(plan)
    except (ValueError, IOError) as e:
        print(f"[Seed] Rejected: {e}")
        return False

    # -- Validate + Repair loop --------------
    root_str = str(ROOT)
    llm = LLMClient()
    all_ok = True

    for path in written:
        rel = str(path.relative_to(ROOT))
        ok, errors = Builder.validate(cwd=root_str, target_file=rel)
        if not ok:
            print(f"[Seed] Validation failed for {rel}: {errors}")
            all_ok = False
            # Attempt repair
            repaired = Builder.repair(
                cwd=root_str, target_file=rel, errors=errors, llm=llm
            )
            if repaired:
                print(f"[Seed] Repaired {rel}")
            else:
                print(f"[Seed] Could not repair {rel}")

    if not all_ok:
        print("[Seed] Some files could not be validated or repaired.")
        return False

    # Wire the new files into the system
    wired = wire_new_files(written, constitution, current_stage)
    if not wired:
        print("[Seed] Wiring failed for some files.")
        return False

    # Save the plan for reference
    save_plan(plan, current_stage)

    # Check if stage advancement is needed
    if advance_stage(constitution, current_stage):
        print(f"[Seed] Advanced to stage {current_stage + 1}")

    print("[Seed] Evolution cycle complete.")
    return True

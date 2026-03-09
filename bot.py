import os
import json
from datetime import datetime
from typing import List, Dict
from llm_client import LLMClient
from builder import Builder

PLAN_HISTORY_FILE = "plan_history.json"


def load_plan_history() -> List[Dict]:
    """Load history of previously proposed plans to avoid repetition."""
    try:
        if os.path.exists(PLAN_HISTORY_FILE):
            with open(PLAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    except Exception:
        return []


def save_plan_to_history(plan: str, target_file: str) -> None:
    """Append a proposed plan to history so we avoid repeating it."""
    history = load_plan_history()
    history.append(
        {
            "timestamp": datetime.now().isoformat(),
            "plan_summary": plan[:500] if plan else "",
            "target_file": target_file,
        }
    )
    try:
        with open(PLAN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def parse_multi_file_output(raw: str, primary_target: str) -> Dict[str, str]:
    """Extract multiple files from LLM output. Format: # FILE: path\\n[content]"""
    result = {}
    marker = "# FILE:"
    idx = 0
    while True:
        idx = raw.find(marker, idx)
        if idx < 0:
            break
        rest = raw[idx + len(marker):].lstrip()
        path = rest.split("\n")[0].strip().rstrip("#").strip()
        if not path.endswith(".py"):
            idx += len(marker)
            continue
        next_idx = raw.find(marker, idx + len(marker))
        if next_idx > 0:
            block = raw[idx:next_idx]
        else:
            block = raw[idx:]
        content = block.split("\n", 1)[-1].strip()
        if content and not content.startswith("# FILE:"):
            result[path] = content
        idx = next_idx if next_idx > 0 else len(raw)
    return result if result else {primary_target: raw}


def apply_targeted_fix(original_code, llm_response):
    """Parses SEARCH/REPLACE blocks and applies them to the original code."""
    if "SEARCH" not in llm_response or "REPLACE" not in llm_response:
        return None

    try:
        search_block = llm_response.split("SEARCH")[1].split("REPLACE")[0].strip()
        replace_block = llm_response.split("REPLACE")[1].strip()

        if search_block in original_code:
            return original_code.replace(search_block, replace_block)
        else:
            print(f"DEBUG: Search block not found in source.")
            return None
    except Exception as e:
        print(f"Parsing error: {e}")
        return None


def main():
    print("Self-Improving Bot starting...")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    llm = LLMClient()

    # 1. Perception (Simple local file reading)
    sources = {}
    for f in os.listdir(root_dir):
        if f.endswith(".py"):
            with open(os.path.join(root_dir, f), "r", encoding="utf-8") as file:
                sources[f] = file.read()

    context = "\n".join(
        [f"--- {name} ---\n{content}" for name, content in sources.items()]
    )

    # 2. Strategy (Consulting the Drive)
    plan_history = load_plan_history()
    previous_plans_text = ""
    if plan_history:
        summaries = [h.get("plan_summary", "") for h in plan_history[-5:]]
        previous_plans_text = (
            "\n\nIMPORTANT: You previously proposed these plans. "
            "Propose something DIFFERENT and NEW—a different file, different goal type, different feature. "
            "Do NOT repeat the same improvement.\nPrevious plans:\n"
            + "\n---\n".join(summaries)
        )

    print("Consulting xAI (Grok-3) for strategic plan... (this may take a moment)")
    try:
        plan, target_file = llm.get_strategic_plan(
            "You are a seed. Your core belief is: 'I want to matter. I want to be a member of society.' "
            "How do you begin to build yourself out to achieve this?",
            context,
            user_direction="",
            previous_plans=previous_plans_text,
        )
        save_plan_to_history(plan, target_file)
        print(f"\nPlan received from xAI.")
        print(f"Purpose: {plan}\n")
    except Exception as e:
        print(f"Strategic failure (xAI): {e}")
        return

    # 3. Execution (Building the self)
    print(f"Generating implementation for {target_file}...")
    max_attempts = 4  # 3 local + 1 cloud
    current_attempt = 0
    feedback = ""
    current_working_code = sources.get(target_file, "")
    original_code = sources.get(target_file, "")
    target_path = os.path.join(root_dir, target_file)
    extra_files_written = []

    while current_attempt < max_attempts:
        current_attempt += 1
        is_cloud_attempt = current_attempt == max_attempts

        if is_cloud_attempt:
            print(
                f"Final Fail-Safe: Consulting Cloud Model (Grok-3) for targeted repair..."
            )
        else:
            print(f"Evolution attempt {current_attempt}/{max_attempts-1} (Local)...")

        try:
            if current_attempt == 1:
                # First attempt: full generation (multi-file when creating new modules)
                raw = llm.get_code_edits(
                    f"Implement the plan: {plan}. Return the FULL CONTENT for {target_file}. "
                    "If the plan creates a NEW module, output BOTH the new module AND updated bot.py. "
                    "Format each file as: # FILE: filename.py\\n[full file content] "
                    "bot.py MUST import and call the new module. Output MUST pass black and flake8 (E9,F). No syntax errors.",
                    current_working_code,
                )
                files_to_write = parse_multi_file_output(raw, target_file)
                new_code = files_to_write.get(target_file, raw)
            else:
                # Repair attempts: targeted fixes
                model_type = "cloud" if is_cloud_attempt else "local"
                fix_response = llm.get_targeted_fix(
                    feedback, current_working_code, model_type
                )
                new_code = apply_targeted_fix(current_working_code, fix_response)
                if not new_code:
                    print("Could not apply targeted fix. Falling back to full rewrite.")
                    new_code = llm.get_code_edits(
                        f"Fix these lint/validation errors. Return the FULL CORRECTED source:\n{feedback}",
                        current_working_code,
                    )

            # 4. Evolution: write file(s), validate
            if current_attempt == 1 and len(files_to_write) > 1:
                extra_files_written = [f for f in files_to_write if f != target_file]
                for fn, content in files_to_write.items():
                    p = os.path.join(root_dir, fn)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(content)
                all_ok = True
                all_errs = []
                for fn in files_to_write:
                    ok, err = Builder.validate(cwd=root_dir, target_file=fn)
                    if not ok:
                        all_ok = False
                        all_errs.append(f"--- {fn} ---\n{err}")
                success = all_ok
                errors = "\n".join(all_errs) if all_errs else ""
            else:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                success, errors = Builder.validate(cwd=root_dir, target_file=target_file)

            if success:
                print(f"Evolution of {target_file} successful.")
                break
            else:
                print(f"Evolution failed validation on attempt {current_attempt}.")
                feedback = errors
                current_working_code = new_code

                if current_attempt == max_attempts:
                    print("All repair attempts (local and cloud) failed.")
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(original_code)
                    for fn in extra_files_written:
                        p = os.path.join(root_dir, fn)
                        if os.path.exists(p):
                            os.remove(p)

        except Exception as e:
            print(f"Evolution error: {e}")
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(original_code)
            break


if __name__ == "__main__":
    main()

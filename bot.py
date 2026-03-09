import os
import json
import logging
from llm_client import LLMClient
from builder import Builder


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
    print("Consulting xAI (Grok-3) for strategic plan... (this may take a moment)")
    try:
        plan, target_file = llm.get_strategic_plan(
            "You are a seed. Your core belief is: 'I want to matter. I want to be a member of society.' "
            "How do you begin to build yourself out to achieve this?",
            context,
        )
        print(f"\nPlan received from xAI.")
        print(f"Purpose: {plan}\n")
    except Exception as e:
        print(f"Strategic failure (xAI): {e}")
        return

    # 3. Execution (Building the self)
    print(f"Generating implementation for {target_file}...")
    max_attempts = 3
    current_attempt = 0
    feedback = ""

    while current_attempt < max_attempts + 1:
        current_attempt += 1
        is_cloud_attempt = current_attempt > max_attempts
        
        if is_cloud_attempt:
            print(f"Final Fail-Safe: Consulting Cloud Model (Grok-3) for repair...")
        else:
            print(f"Evolution attempt {current_attempt}/{max_attempts} (Local)...")

        try:
            current_code = sources.get(target_file, "")
            instruction = f"Implement the plan: {plan}. Return the FULL CONTENT for {target_file}."
            if feedback:
                instruction = f"Your previous attempt for {target_file} failed with these errors:\n{feedback}\n\nPlease fix these errors and return the FULL CONTENT."

            if is_cloud_attempt:
                new_code = llm.get_code_edits_cloud(instruction, current_code)
            else:
                new_code = llm.get_code_edits(instruction, current_code)

            # 4. Evolution
            tmp_path = os.path.join(root_dir, f"{target_file}.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(new_code)

            success, errors = Builder.validate()
            if success:
                print(f"Evolution of {target_file} successful.")
                with open(
                    os.path.join(root_dir, target_file), "w", encoding="utf-8"
                ) as f:
                    f.write(new_code)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                break
            else:
                if is_cloud_attempt:
                    print("Final cloud attempt failed.")
                else:
                    print(f"Evolution failed validation on attempt {current_attempt}.")
                
                feedback = errors
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                
                if current_attempt == max_attempts + 1:
                    print("All repair attempts (local and cloud) failed.")

        except Exception as e:
            print(f"Evolution error: {e}")
            break


if __name__ == "__main__":
    main()

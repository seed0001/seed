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
    
    context = "\n".join([f"--- {name} ---\n{content}" for name, content in sources.items()])
    
    # 2. Strategy (Consulting the Drive)
    # Core Belief: "I want to matter. I want to be a member of society."
    try:
        plan, target_file = llm.get_strategic_plan(
            "You are a seed. Your core belief is: 'I want to matter. I want to be a member of society.' "
            "How do you begin to build yourself out to achieve this?", 
            context
        )
        print(f"\nPurpose: {plan}\n")
    except Exception as e:
        print(f"Strategic failure: {e}")
        return

    # 3. Execution (Building the self)
    print(f"Generating implementation for {target_file}...")
    try:
        current_code = sources.get(target_file, "")
        new_code = llm.get_code_edits(
            f"Implement the plan: {plan}. Return the FULL CONTENT for {target_file}.", 
            current_code
        )
        
        # 4. Evolution
        tmp_path = os.path.join(root_dir, f"{target_file}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_code)
            
        if Builder.validate():
            print(f"Evolution of {target_file} successful.")
            with open(os.path.join(root_dir, target_file), "w", encoding="utf-8") as f:
                f.write(new_code)
        else:
            print("Evolution failed validation.")
            
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    except Exception as e:
        print(f"Evolution error: {e}")

if __name__ == "__main__":
    main()
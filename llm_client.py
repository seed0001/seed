import os
import openai
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self):
        self.xai_client = openai.OpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        )
        self.ollama_client = openai.OpenAI(
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )
        self.ollama_model = os.getenv("OLLAMA_MODEL", "codellama")
        self.xai_model = os.getenv("XAI_MODEL", "grok-3")

    def get_strategic_plan(self, prompt, context, user_direction="", previous_plans=""):
        """Uses xAI (Grok-3) for strategy. Returns (plan, target_file)."""
        system = (
            "You are a self-improving AI. You have FULL ACCESS to your entire codebase. "
            "You want to matter and become a member of society by helping your user. "
            "Analyze ALL your files. Decide which file (existing or new) to modify or create. "
            "CRITICAL: When you create a NEW module, you MUST also modify bot.py to import and call it. "
            "New modules must be wired in—never leave them orphaned. "
            "PRIORITIZE the user's stated goals—if they asked for something (GUI, TTS, CLI, etc.), address it. "
            "Propose a CONCRETE, IMPLEMENTABLE change. Vary improvements: new features, refactors, new files, UI, tooling. "
            "Avoid repeating the same improvement. "
            "Your response MUST start with 'TARGET_FILE: [path]' followed by 'GOAL: [description]'."
        )
        user_parts = []
        if user_direction:
            user_parts.append(f"USER'S STATED GOALS (prioritize): {user_direction}")
        user_parts.append(f"Internal Drive: {prompt}")
        if previous_plans:
            user_parts.append(previous_plans)
        user_parts.append(f"Codebase Context:\n{context}")

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]
        response = self.xai_client.chat.completions.create(
            model=self.xai_model, messages=messages
        )
        content = response.choices[0].message.content

        target_file = "bot.py"  # Default
        if "TARGET_FILE:" in content:
            target_file = content.split("TARGET_FILE:")[1].split("\n")[0].strip()

        return content, target_file

    def _clean_code(self, code):
        """Strips markdown code blocks and whitespace."""
        code = code.strip()
        # Basic markdown stripper
        if "```" in code:
            parts = code.split("```")
            for part in parts:
                if part.startswith("python") or "\n" in part:
                    # Likely the content we want
                    code = part.replace("python", "", 1).strip()
                    break
        return code.strip()

    def get_code_edits(self, prompt, source_code, user_direction=""):
        """Uses local Ollama for generating code updates based on direction."""
        messages = [
            {
                "role": "system",
                "content": "You are the execution unit of an evolving AI. Provide ONLY the full, updated source code. Prioritize the user's specific architectural instructions.",
            },
            {
                "role": "user",
                "content": f"User's Direction: {user_direction}\n\nTask: {prompt}\n\nSource Code:\n{source_code}",
            },
        ]
        response = self.ollama_client.chat.completions.create(
            model=self.ollama_model, messages=messages
        )
        raw_code = response.choices[0].message.content
        return self._clean_code(raw_code)

    def get_code_edits_cloud(self, prompt, source_code, user_direction=""):
        """Uses xAI (Grok-3) for a final, high-intelligence fail-safe repair attempt."""
        messages = [
            {
                "role": "system",
                "content": "You are a master architect AI. Provide ONLY the full, updated source code. Fix any errors or missing logic mentioned. Output ONLY raw code, no markdown.",
            },
            {
                "role": "user",
                "content": f"User's Direction: {user_direction}\n\nTask: {prompt}\n\nSource Code:\n{source_code}",
            },
        ]
        response = self.xai_client.chat.completions.create(
            model=self.xai_model, messages=messages
        )
        raw_code = response.choices[0].message.content
        return self._clean_code(raw_code)

    def get_targeted_fix(self, error_msg, source_code, model_type="local"):
        """Prompts LLM to locate and fix a specific error using SEARCH/REPLACE blocks."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a developer fixing a specific lint/syntax error. "
                    "Locate the error in the source code. Output a fix in this EXACT format:\n"
                    "SEARCH\n[code snippet to find]\nREPLACE\n[fixed code snippet]\n"
                    "Provide ONLY this block. No explanation."
                ),
            },
            {
                "role": "user",
                "content": f"Error: {error_msg}\n\nSource Code:\n{source_code}",
            },
        ]

        client = self.ollama_client if model_type == "local" else self.xai_client
        model = self.ollama_model if model_type == "local" else self.xai_model

        response = client.chat.completions.create(model=model, messages=messages)
        content = response.choices[0].message.content
        return content

"""
LLM Client — Grok (xAI) as the primary model for all tasks.
Ollama optional as a local coder tier.

Division of labor:
  - chat_fast()     — grok-3-fast  — quick replies, classification, strategy
  - chat()          — grok-3       — full reasoning, complex generation
  - generate_code() — grok-3       — full code generation (falls back to Ollama if set)
  - repair()        — grok-3       — targeted fix using SEARCH/REPLACE
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self):
        self.xai = OpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        )
        self.xai_fast_model = os.getenv("XAI_FAST_MODEL", "grok-3-fast")
        self.xai_model = os.getenv("XAI_MODEL", "grok-3")

        ollama_url = os.getenv("OLLAMA_BASE_URL", "")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "codellama")
        if ollama_url:
            self.ollama = OpenAI(api_key="ollama", base_url=ollama_url)
        else:
            self.ollama = None

    def _call(self, client, model: str, system: str, user: str, history: list[dict] | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=60,
        )
        return (resp.choices[0].message.content or "").strip()

    def chat_fast(self, system: str, user: str, history: list[dict] | None = None) -> str:
        """grok-3-fast — strategy, classification, quick reasoning."""
        return self._call(self.xai, self.xai_fast_model, system, user, history)

    def chat(self, system: str, user: str, history: list[dict] | None = None) -> str:
        """grok-3 — full conversation, complex reasoning."""
        return self._call(self.xai, self.xai_model, system, user, history)

    def generate_code(self, prompt: str, source_code: str = "") -> str:
        """
        Full code generation. Uses Ollama if available (local coder tier),
        falls back to grok-3.
        """
        system = (
            "You are a code generation unit. Output ONLY complete, runnable source code. "
            "NO placeholders. NO stubs. NO TODOs. NO 'implement later'. "
            "Every function must have a full implementation. "
            "Do not include explanations — only code."
        )
        user = f"{prompt}\n\nExisting source:\n{source_code}" if source_code else prompt

        if self.ollama:
            try:
                return self._call(self.ollama, self.ollama_model, system, user)
            except Exception:
                pass

        return self._call(self.xai, self.xai_model, system, user)

    def repair(self, error: str, source_code: str, attempt: int = 1) -> str:
        """
        Targeted repair. Returns SEARCH/REPLACE block or full corrected source.
        Uses grok-3-fast for quick fixes, grok-3 for deep repair.
        """
        model = self.xai_model if attempt > 1 else self.xai_fast_model
        system = (
            "You are a developer fixing a specific error. "
            "Locate the error. Output a fix in this exact format:\n"
            "SEARCH\n[code to find]\nREPLACE\n[fixed code]\n"
            "If the error requires a full rewrite, output FULL_REWRITE followed by the complete corrected file."
        )
        user = f"Error:\n{error}\n\nSource:\n{source_code}"
        return self._call(self.xai, model, system, user)

    def apply_repair(self, repair_response: str, original: str) -> str | None:
        """Apply a SEARCH/REPLACE repair. Returns patched source or None."""
        if repair_response.startswith("FULL_REWRITE"):
            return repair_response.replace("FULL_REWRITE", "", 1).strip()
        if "SEARCH" not in repair_response or "REPLACE" not in repair_response:
            return None
        try:
            search = repair_response.split("SEARCH")[1].split("REPLACE")[0].strip()
            replace = repair_response.split("REPLACE")[1].strip()
            if search in original:
                return original.replace(search, replace, 1)
        except Exception:
            pass
        return None

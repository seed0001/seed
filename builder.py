"""
Builder — validate changed files only.
black for formatting. flake8 for structural errors (E9, F).
Never fail on pre-existing lint in unrelated files.
"""

import subprocess
import sys
from pathlib import Path


class Builder:
    @staticmethod
    def validate(cwd: str | None = None, target_file: str | None = None) -> tuple[bool, str]:
        """
        Format and lint target_file only.
        Returns (success, error_string).
        """
        if not target_file:
            return True, ""

        errors = ""
        run_kw: dict = {"capture_output": True}
        if cwd:
            run_kw["cwd"] = cwd

        # 1. Auto-format with black
        try:
            subprocess.run(
                [sys.executable, "-m", "black", target_file],
                check=True,
                **run_kw,
            )
        except subprocess.CalledProcessError as e:
            msg = (e.stderr or e.stdout or b"").decode("utf-8", errors="replace")
            errors += f"black: {msg}\n"
        except FileNotFoundError:
            pass  # black not installed — skip

        # 2. Structural lint — only E9 (syntax/runtime) and F (logic) errors
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "flake8",
                    "--select=E9,F",
                    "--ignore=F401,F841",
                    "--show-source",
                    target_file,
                ],
                check=True,
                **run_kw,
            )
        except subprocess.CalledProcessError as e:
            out = (e.stdout or b"").decode("utf-8", errors="replace")
            err = (e.stderr or b"").decode("utf-8", errors="replace")
            errors += f"flake8:\n{out or err}"
            return False, errors
        except FileNotFoundError:
            pass  # flake8 not installed — skip

        return True, ""

    @staticmethod
    def validate_all(cwd: str | None, paths: list[str]) -> tuple[bool, str]:
        """Validate multiple files. Returns (all_ok, combined_errors)."""
        all_errors = []
        for p in paths:
            ok, err = Builder.validate(cwd=cwd, target_file=p)
            if not ok:
                all_errors.append(f"--- {p} ---\n{err}")
        if all_errors:
            return False, "\n".join(all_errors)
        return True, ""

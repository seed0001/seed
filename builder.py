import subprocess
import sys


class Builder:
    @staticmethod
    def validate(cwd=None, target_file=None):
        """Runs auto-formatting and basic checks. Returns (success, errors).
        If target_file is set, only validates that file (avoids failing on other files).
        """
        print("Running validation...")
        errors = ""
        run_kw = {"check": True, "capture_output": True}
        if cwd:
            run_kw["cwd"] = cwd

        check_target = target_file if target_file else "."

        # 1. Auto-format with black (only the target file)
        try:
            subprocess.run(
                [sys.executable, "-m", "black", check_target],
                **run_kw,
            )
            print("Auto-formatting (black) completed.")
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or b"").decode("utf-8", errors="replace")
            errors += f"Black error: {err}\n"
            print("Auto-formatting failed.")

        # 2. Run flake8 (only on the target file so seed's own files don't fail us)
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    "--ignore=E,W,F401,F841,F541",
                    "--select=E9,F",
                    "--show-source",
                    check_target,
                ],
                **run_kw,
            )
            print("Structural linting passed.")
        except subprocess.CalledProcessError as e:
            lint_out = (e.stdout or b"").decode("utf-8", errors="replace")
            lint_err = (e.stderr or b"").decode("utf-8", errors="replace")
            lint_output = lint_out or lint_err
            errors += f"Lint failures:\n{lint_output}"
            print("Structural linting failed.")
            return False, errors

        return True, ""

    @staticmethod
    def build():
        """Simulates a build process."""
        return Builder.validate()

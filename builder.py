import subprocess
import sys


class Builder:
    @staticmethod
    def validate():
        """Runs auto-formatting and then basic checks. Returns (success, errors)."""
        print("Running validation...")
        errors = ""

        # 1. Auto-format with black
        try:
            subprocess.run(
                [sys.executable, "-m", "black", "."], check=True, capture_output=True
            )
            print("Auto-formatting (black) completed.")
        except subprocess.CalledProcessError as e:
            errors += f"Black error: {e.stderr.decode()}\n"
            print("Auto-formatting failed.")

        # 2. Run flake8
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    "--ignore=E,W,F401,F841",
                    "--select=E9,F",
                    ".",
                ],
                check=True,
                capture_output=True,
            )
            print("Structural linting passed.")
        except subprocess.CalledProcessError as e:
            lint_output = e.stdout.decode()
            errors += f"Lint failures:\n{lint_output}"
            print("Structural linting failed.")
            return False, errors

        return True, ""

    @staticmethod
    def build():
        """Simulates a build process."""
        return Builder.validate()

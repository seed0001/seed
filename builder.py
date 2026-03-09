import subprocess
import sys


class Builder:
    @staticmethod
    def validate():
        """Runs auto-formatting and then basic checks."""
        print("Running validation...")

        # 1. Auto-format with black
        try:
            subprocess.run([sys.executable, "-m", "black", "."], check=True)
            print("Auto-formatting (black) completed.")
        except Exception as e:
            print(f"Black failed or not installed: {e}")

        # 2. Run flake8 but ignore stylistic complaints (E, W, F401)
        # We focus on E9 (SyntaxError) and F (Logical errors except F401)
        try:
            # --ignore=E,W,F401,F841
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "flake8",
                    "--ignore=E,W,F401,F841",
                    "--select=E9,F",  # Only catch syntax and critical logic
                    ".",
                ],
                check=True,
            )
            print("Structural linting passed.")
        except subprocess.CalledProcessError:
            print("Structural linting failed.")
            return False

        return True

    @staticmethod
    def build():
        """Simulates a build process."""
        return Builder.validate()

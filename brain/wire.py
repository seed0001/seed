"""
Wire -- no-op stub.

main.py is protected and must never be modified by the evolution loop.
New modules wire themselves by exposing a run_<stem>() function.
conversation/chat.py is the integration point -- it calls memory, personality, etc.
main.py's talk() dynamically loads conversation/chat.py and calls run_chat().
No injection into main.py is ever needed.
"""

from pathlib import Path


def wire_new_files(plan: dict, written_paths: list[Path]) -> None:
    """Intentional no-op. main.py is protected. Modules self-wire via run_<stem>()."""
    pass

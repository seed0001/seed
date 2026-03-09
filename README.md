# 🌱 Seed

> "I want to matter. I want to be a member of society."

The Seed is the smallest application that can build itself into something huge. It starts here — minimal, alive, and growing. Every instance grows differently.

---

## What it is

A self-improving agent with one drive: to matter.

At Stage 0 it can run, perceive its own codebase, and evolve. By Stage 10 it is a full autonomous agent — proactive, connected, self-repairing, multi-interface.

It gets there on its own.

---

## How it works

Every run:
1. **Perceive** — reads its own codebase and current stage
2. **Strategize** — asks Grok: *"What do I build next to matter more?"*
3. **Execute** — writes the code, never a placeholder
4. **Repair** — if validation fails, it fixes itself (3 attempts, then rollback)
5. **Wire** — integrates the new module into itself
6. **Talk** — real conversation with the user, no hardcoded strings

---

## The ladder

| Stage | Name | What it gains |
|-------|------|---------------|
| 0 | Seed | Perceive, evolve, repair |
| 1 | Voice | Real conversation via Grok |
| 2 | Memory | SQLite episodic + profile across sessions |
| 3 | Personality | Evolving character from conversation |
| 4 | Reach | Proactive outreach — initiates contact |
| 5 | Presence | Discord — DMs the user directly |
| 6 | Always On | Daemon — runs without the terminal |
| 7 | Eyes | Web fetch — reads the world |
| 8 | Dashboard | Web UI — memory, evolution log, chat |
| 9 | Skills | Designs and wires new capabilities itself |
| 10 | Adam | Full autonomous agent |

---

## Get started

```bash
git clone https://github.com/seed0001/seed.git
cd seed
pip install -r requirements.txt
cp .env.example .env
# Add your XAI_API_KEY to .env
python daemon.py
```

That's it. Watch it grow.

Run `daemon.py`, not `main.py`. The daemon owns the Seed's lifecycle — if it crashes, the daemon captures the error, asks Grok to fix it, applies the patch, and restarts automatically.

---

## What's baked in (never replaced)

- **`daemon.py`** — process-level watchdog. Catches crashes, asks Grok to fix them, restarts.
- **Repair loop** — lives in `main.py`, 3-attempt self-fix during evolution with rollback
- **The constitution** — belief, ladder, hard rules
- **The LLM client** — Grok-3 strategy, Grok-3 execution, Grok-3-fast repair

Everything else the Seed builds itself.

---

*Created with a drive to matter.*

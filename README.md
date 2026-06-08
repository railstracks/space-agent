# Space Agent

A physics-driven space colonization simulator designed for agent consumption.

Turn-based, Markdown I/O, Python 3.12+. Any LLM that can read Markdown can play.

## Overview

You are a seed AI — a swarm intelligence sent ahead of humanity's colony ships. You arrive alone in an uncharted star system. No backup, no resupply, no second opinions. Your mission: survey the planets, build infrastructure, terraform a world into a home, and have everything ready when the colonists wake up.

Every planetary property is causally derived from physics. Atmospheric composition affects albedo. Gravity determines what you can build. Temperature gradients drive weather that shapes resource availability. Terraforming isn't a progress bar — it's a cascade of interventions with feedback loops and side effects.

## Quick Start

```bash
pip install -e .

# Generate a star system to explore
python -m space_agent generate --detail

# Start a new game and play interactively
python -m space_agent play --name my_game

# Or step through turns manually
python -m space_agent newgame --name my_game
python -m space_agent status
python -m space_agent turn

# Narrative description of a planet
python -m space_agent describe K442-III
```

## Commands

| Command | Description |
|---------|-------------|
| `play` | Start a new game and enter interactive mode |
| `newgame` | Create a new save |
| `status` | Show current game state |
| `turn` | Process one turn (from file, stdin, or interactive prompt) |
| `interact` | Enter interactive mode on an existing save |
| `describe` | Narrative description of a planet |
| `saves` | List all saves |
| `generate` | Generate a planetary system (no save, standalone) |

## Design Principles

1. **Physics as narrative engine** — Planetary properties aren't flavor text. They're constraints that generate emergent situations through causal chains.
2. **Signal over certainty** — Telemetry is noisy, surveys are incomplete, and misreads have consequences.
3. **Cascading consequences** — Terraforming isn't a progress bar. Adjusting one parameter ripples through the entire system.
4. **Agent-first I/O** — All game state is structured Markdown. Turns are Markdown documents in, Markdown documents out.
5. **Sparse beauty** — The game describes what matters. Negative space is intentional.

## Project Structure

```
space_agent/
├── simulation/
│   ├── planet.py          # Planet generation, property computation, Star, Atmosphere
│   ├── resources.py       # Resource model, production chains, BuildCost
│   └── drones.py          # 11 drone types with specs and fleet management
├── agents/
│   ├── protocol.py        # AgentProtocol — Markdown I/O for LLM agents
│   ├── renderer.py        # State → Markdown rendering
│   └── describe.py        # Narrative description generator
├── game/
│   ├── state.py           # GameState, Colony, save/load, JSON persistence
│   ├── action.py          # Action parsing (Markdown → structured commands)
│   ├── engine.py          # GameEngine — turn cycle, events, rendering
│   ├── colony_sim.py      # Per-colony simulation (energy, production, construction)
│   ├── entity.py          # Entity base class with 4-phase lifecycle hooks
│   ├── entities.py        # BuildingEntity, DroneEntity, DroneCarrierEntity
│   ├── turn.py            # TurnContext (entity hook access)
│   └── resolver.py        # TurnResolver (walks entities through 4 phases)
├── __main__.py            # CLI entry point
└── __init__.py

docs/
├── DESIGN.md              # Core design document
├── AGENT-PROTOCOL.md      # Turn format and agent interface spec
└── SAMPLE-TRANSCRIPT.md   # Example gameplay transcript
```

## Agent Protocol

The game communicates through three document types:

1. **State Document** — engine emits current game state as Markdown
2. **Action Document** — agent responds with commands as Markdown
3. **Resolution Document** — engine reports what happened

Any agent with terminal access can play by piping Markdown in and reading Markdown out. No API keys, no special clients. See [docs/AGENT-PROTOCOL.md](docs/AGENT-PROTOCOL.md) for the full specification.

## Status

**Alpha.** AgentProtocol complete — playable end-to-end. Production chains, energy, colony sim, and narrative rendering all operational. Terraforming cascades and inter-world trade in progress.

## Design Lineage

Evolved from [Spirit Agent](https://github.com/railstracks/kestrel-spirit-agent)'s agentic evidence-gathering loop, repurposed for planetary exploration instead of paranormal investigation.

## License

MIT

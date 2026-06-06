# Space Agent

A physics-driven space colonization simulator designed for agent consumption.

## Overview

Space Agent is a turn-based strategy game where an AI agent explores, evaluates, and terraforms planetary systems. Unlike traditional 4X games that abstract away planetary physics, Space Agent grounds its mechanics in real causal chains: atmospheric composition affects albedo, gravity determines what structures are feasible, temperature gradients drive weather systems that shape resource availability.

The agent interprets noisy telemetry, makes consequential decisions about where to invest limited resources, and manages cascading terraforming effects where every intervention has side effects.

**Design lineage:** Evolved from Spirit Agent's agentic evidence-gathering loop, repurposed for planetary exploration instead of paranormal investigation.

## Design Principles

1. **Physics as narrative engine** — Planetary properties aren't flavor text. They're constraints that generate emergent situations through causal chains.
2. **Signal over certainty** — The agent never gets clean facts. Telemetry is noisy, surveys are incomplete, and misreads have consequences.
3. **Cascading consequences** — Terraforming isn't a progress bar. Adjusting one parameter ripples through the entire system.
4. **Agent-first I/O** — All game state is expressed in structured Markdown. Turns are Markdown documents in, Markdown documents out. Human-readable and machine-parseable.
5. **Sparse beauty** — The game doesn't describe everything. It describes what matters. Negative space is intentional.

## Quick Start

```bash
# Install (when ready)
pip install -e .

# Run a single turn
python -m space_agent.turn --state state/turn_001.md --action actions/explore.md

# Start a new game
python -m space_agent.newgame --output state/
```

## Project Structure

```
space-agent/
├── docs/
│   ├── DESIGN.md          # Core design document
│   ├── SIMULATION.md      # Physics simulation specification
│   ├── AGENT-PROTOCOL.md  # Turn format and agent interface
│   └── TERRAFORMING.md    # Terraforming mechanics
├── src/
│   ├── simulation/        # Planetary physics engine
│   ├── agents/            # Agent interface and turn processing
│   └── game/              # Game state management, victory conditions
├── examples/              # Sample turns and game transcripts
└── tests/
```

## Status

**Pre-alpha.** Concept development in progress.

## License

Private repository. All rights reserved.

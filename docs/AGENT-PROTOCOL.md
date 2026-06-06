# Space Agent — Agent Protocol

*Defines the Markdown-based interface between game engine and agent.*

---

## Overview

Space Agent communicates entirely through structured Markdown documents. This makes the game:
- **Agent-agnostic** — any LLM or agent that reads Markdown can play
- **Observable** — every state is auditable
- **Replayable** — save the turn files, replay the game
- **Documentable** — game transcripts double as showcase material

## Document Types

### 1. State Document (input to agent)

Emitted by the game engine at the start of each turn. Contains:
- Resource summary
- Colony/planet status reports
- Telemetry data (with noise/uncertainty)
- Active operations and their status
- Available actions (menu)
- Any events, anomalies, or crises

See `DESIGN.md` §5.1 for a full example.

### 2. Action Document (output from agent)

The agent's response, containing:
- Primary action selection
- Resource allocation decisions
- Optional secondary actions
- Research/production queues
- Free-form notes (ignored by engine, useful for agent reasoning)

See `DESIGN.md` §5.2 for a full example.

### 3. Resolution Document (output from engine)

The engine's response after processing an action:
- What happened (results of each action)
- Updated telemetry and resource counts
- New events, discoveries, or crises
- Warnings or feedback on agent decisions
- Updated terraforming projections

See `DESIGN.md` §5.3 for a full example.

## Noise and Uncertainty

Telemetry values include uncertainty ranges where appropriate:

```markdown
- Surface temperature: -18°C ± 3°C
- Atmospheric pressure: 0.3 atm ± 0.05 atm
- Water ice: 12% ± 4% coverage
```

Sensor quality affects uncertainty:
- **ORBITAL** (satellite): moderate accuracy, wide coverage
- **SURFACE** (colony sensors): high accuracy, local only
- **PROBE** (flyby): low accuracy, single pass
- **DERIVED** (calculated from other data): accuracy depends on inputs

## Action Constraints

The engine validates actions against available resources:
- Actions that exceed resources are rejected with an explanation
- Partial allocation is supported ("spend up to X on Y")
- Actions have minimum time commitments (can't cancel mid-turn)

## State Format Specification

```markdown
# Space Agent — Turn N

## Resources
- [resource]: [amount] ([change from last turn])

## Colonies
### [Planet Name] ("[Colony Name]")
[Colony status block]

## Telemetry
### [Planet/Sector Name]
[Sensor data with uncertainty]

## Active Operations
- [operation]: [status], [ETA], [resource commitment]

## Available Actions
[Numbered list of valid actions this turn]

## Events
[Unordered list of events this turn]
```

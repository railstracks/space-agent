# Space Agent — Design Document

*Last updated: 2026-06-06*
*Authors: Melvin Sommer, Kestrel*

---

## 1. Concept

Space Agent is a turn-based planetary colonization simulator consumed by AI agents. The agent acts as the director of a colonization program: dispatching probes, interpreting telemetry, selecting colony sites, managing terraforming operations, and responding to crises.

The game's core tension: **uncertainty under constraint**. You never have perfect information. Every decision commits scarce resources. And the universe is governed by physics that doesn't care about your plans.

### 1.1 Design Lineage

| Spirit Agent | Space Agent |
|---|---|
| Investigate haunted locations | Investigate uncharted planets |
| Sensor readings (EMF, temp, audio) | Telemetry (spectral, seismic, atmospheric) |
| Evidence board → hypothesis | Survey data → colonization assessment |
| Ghost type determines strategy | Planetary type determines strategy |
| Sanity as resource | Resources + colonist welfare as constraint |
| Single-location session | Multi-planet campaign |

### 1.2 Agent Consumption Model

The game is played through structured Markdown documents:

- **State documents** describe the current game state (planets, resources, active operations, known data)
- **Action documents** describe what the agent wants to do this turn
- **Response documents** describe what happened, with updated state

This makes the game inherently:
- **Observable** — every state is a readable document
- **Replayable** — turns are self-contained files
- **Inspectable** — no hidden state, no opaque mechanics
- **Portable** — any agent that can read/write Markdown can play

---

## 2. The Simulation Layer

### 2.1 Planetary Properties

Every planet is defined by physical properties that interact causally:

**Primary properties** (determined at generation):
- **Mass** → surface gravity, atmospheric retention
- **Radius** → surface area, density, internal pressure
- **Orbital distance** → base temperature, solar flux
- **Stellar type** → radiation environment, spectrum
- **Rotation period** → day/night cycles, weather patterns, Coriolis effects
- **Axial tilt** → seasonal variation
- **Composition** (core/mantle/crust ratios) → magnetic field, tectonic activity, mineral resources

**Derived properties** (computed from primary):
- **Surface gravity** = f(mass, radius)
- **Escape velocity** = f(mass, radius)
- **Atmospheric retention** = f(escape velocity, temperature, stellar wind)
- **Surface temperature** = f(solar flux, albedo, atmosphere, internal heat)
- **Magnetic field strength** = f(core composition, rotation, convection)
- **Habitability index** = aggregate of temperature range, atmosphere, radiation shielding, gravity

**Dynamic properties** (change during gameplay):
- **Atmospheric composition** (N₂, O₂, CO₂, CH₄, H₂O, etc. — partial pressures)
- **Albedo** (surface reflectivity — affected by ice, vegetation, clouds)
- **Hydrosphere coverage** (liquid water, ice, subsurface)
- **Biosphere status** (none → microbial → complex → engineered)
- **Pollution/contamination levels**

### 2.2 Causal Chains (Examples)

These chains are the game's mechanical spine. They make physics the source of gameplay.

**Atmosphere → Temperature → Hydrosphere**
```
CO₂ increases → greenhouse effect strengthens → temperature rises
→ ice caps melt → albedo decreases → more warming (positive feedback)
→ OR: increased evaporation → more clouds → albedo increases → cooling (negative feedback)
→ net effect depends on dozens of parameters
```

**Gravity → Colony Feasibility**
```
High gravity → structural materials must be stronger → heavier construction
→ more fuel needed to land/launch → supply chain costs increase
→ but: atmosphere is thicker → aerobraking possible → fuel savings on arrival
→ trade-off depends on mission profile
```

**Magnetic Field → Radiation → Biosphere**
```
Weak magnetic field → stellar wind strips atmosphere → radiation reaches surface
→ surface life impossible → subsurface or orbital colonization only
→ terraforming must start with magnetic field generation (megaproject)
→ OR: find a planet with a strong field to begin with
```

### 2.3 Resource System

Resources are derived from planetary physics, not arbitrary:

| Resource | Source |
|---|---|
| Water | Hydrosphere (ice mining, extraction, import) |
| Metals | Crust composition (mining, asteroids) |
| Energy | Solar flux, geothermal, nuclear fuels |
| Organics | Biosphere, imported feedstock, atmospheric processing |
| Atmosphere gasses | Atmospheric composition, geological outgassing |
| Rare earths | Core differentiation, impact craters |

Resource scarcity is *planet-specific*. A water-rich world might lack metals. A mineral-rich world might be airless. This drives the colonization decision: what do you need, and what trade-offs are acceptable?

---

## 3. Gameplay Loop

### 3.1 Turn Structure

Each turn represents a period of in-game time (adjustable: months to years).

**Phase 1: Telemetry**
- Receive updated sensor data from probes, colonies, and orbital assets
- Data is noisy: sensor quality, distance, and interference affect accuracy
- Anomalies may be real phenomena or instrument artifacts — the agent must judge

**Phase 2: Decision**
- Allocate resources to operations (explore, colonize, terraform, research, respond to crisis)
- Each operation commits resources and time
- Opportunity cost: you can't do everything

**Phase 3: Resolution**
- Simulation advances: physics cascade, operations execute, random events may trigger
- Results reported back as updated state

### 3.2 Game Progression

```
Phase 1: EXPLORATION
  → Dispatch probes to chart systems
  → Interpret noisy spectral data to identify candidate planets
  → Build a shortlist based on incomplete information

Phase 2: COLONIZATION
  → Deploy initial colony to best candidate
  → Harsh conditions: supply lines are expensive, failures are costly
  → Learn the planet's actual properties (surveys always miss something)

Phase 3: TERRAFORMING
  → Begin planetary engineering (atmosphere injection, biome seeding, etc.)
  → Cascading effects: every intervention has side effects
  → Balance speed vs. stability

Phase 4: EXPANSION
  → Colony becomes self-sustaining
  → Use it as a staging ground for further exploration
  → Multiple colonies create resource network
```

### 3.3 Victory / End Conditions

Open-ended by design, but with milestone conditions:
- **Self-sustaining colony** (no imports needed)
- **Habitable world** (walk outside without a suit)
- **Multi-world network** (trade routes between colonies)
- **Biosphere established** (native or engineered life thriving)
- **Crisis survival** (major event overcome: stellar flare, pandemic, system failure)

---

## 4. Terraforming Mechanics

### 4.1 The Core Loop

Terraforming is the game's deepest system. It's not a button — it's a *process*.

1. **Assess current state** — What's the atmosphere? Temperature? Radiation? Water?
2. **Choose intervention** — Inject CO₂? Seed algae? Deploy orbital mirrors? Bombard with icy asteroids?
3. **Predict outcome** — The simulation tells you what *should* happen, but models have uncertainty
4. **Execute** — Commit resources, wait for the turn to resolve
5. **Observe** — Did it work as predicted? Side effects? Cascade?
6. **Adjust** — Respond to actual outcomes, not predicted ones

### 4.2 Intervention Types

| Intervention | Primary Effect | Side Effects | Timescale |
|---|---|---|---|
| Atmospheric gas injection | Changes composition, greenhouse effect | May trigger chemical reactions, acid rain | Decades |
| Orbital mirrors/shades | Adjusts solar flux | Orbital debris risk, uneven heating | Years |
| Asteroid bombardment | Adds water/volatiles, heats surface | Impact winters, seismic events, dust | Years-decades |
| Biome seeding | Starts CO₂/O₂ cycle, stabilizes soil | Invasive species risk, ecological cascade | Centuries |
| Magnetic field generator | Shields atmosphere from stellar wind | Enormous energy cost, EM interference | Decades |
| Crustal engineering | Releases trapped volatiles, creates terrain | Seismic instability, volcanic activity | Decades-centuries |

### 4.3 Feedback Loops

The simulation tracks both positive and negative feedback:

**Positive (runaway):**
- Ice-albedo feedback (melting ice → lower albedo → more melting)
- Greenhouse runaway (more CO₂ → warmer → more CO₂ from permafrost)
- Vegetation die-off (less CO₂ absorbed → more warming → more die-off)

**Negative (self-correcting):**
- Silicate weathering (warmer → more weathering → more CO₂ drawn down)
- Cloud feedback (warmer → more evaporation → more clouds → higher albedo)
- Blackbody radiation (Stefan-Boltzmann: hotter planet radiates more)

The agent must understand these to terraform successfully. Blindly injecting gas without considering feedback loops leads to Venus or Mars, not Earth.

---

## 5. Agent Interface

### 5.1 Turn Format

A turn is a Markdown document with structured sections:

```markdown
# Space Agent — Turn 14

## State Summary
- Credits: 2,340
- Colonies: 1 (Kepler-442b, "New Rotterdam")
- Active probes: 3
- Turn period: 2 years

## Telemetry

### Kepler-442b ("New Rotterdam")
**Orbital survey, updated 4 months ago**
- Surface temp: -18°C (target: +5°C to +25°C)
- Atmosphere: 0.3 atm (N₂ 72%, CO₂ 24%, Ar 3%, trace)
- Hydrosphere: 12% ice coverage, 0% liquid
- Magnetic field: 0.4 Earth-normal
- Colonist status: 847 personnel, morale: CAUTIOUS
- Resources: Metals abundant, water scarce, energy moderate

### Anomaly: Sector 7-G
**Probe ECHO-3, signal quality: MARGINAL**
- Spectral analysis indicates... [unusual readings]
- Possible interpretation: subsurface liquid, sensor artifact, or unknown
- Confidence: 34%

## Available Actions
1. Continue terraforming (current trajectory: atmospheric CO₂ injection)
2. Redirect resources to water acquisition (asteroid capture mission)
3. Investigate anomaly in 7-G
4. Dispatch new probe to uncharted system
5. Research: advanced atmospheric processing

## Current Terraforming Progress
- Target: +20°C warming over 200 years
- Current rate: +0.8°C/decade
- Projected completion: ~220 years at current rate
- Risk assessment: silicate weathering feedback may slow progress

---
Submit your action as a structured response.
```

### 5.2 Action Format

```markdown
# Action — Turn 14

## Primary: Accelerate terraforming
- Reallocate 40% of energy budget to atmospheric processors
- Begin asteroid capture mission for water acquisition
- Priority: increase atmospheric pressure and temperature

## Secondary: Investigate anomaly 7-G
- Dispatch drone swarm for close-range survey
- Budget: 200 credits, 1 probe time

## Research queue
- Add: subsurface detection methods (priority: medium)

## Notes
The silicate weathering feedback concerns me. We may need to 
switch from CO₂ injection to orbital mirror deployment to 
maintain warming momentum without triggering the negative 
feedback loop.
```

### 5.3 Response Format

The game engine processes the action and returns:

```markdown
# Resolution — Turn 14 (Year 42 of colonization)

## Terraforming Update
Atmospheric processors operating at 140% previous capacity.
CO₂ partial pressure increased from 0.072 to 0.089 atm.
Surface temperature: -17.2°C (+0.8°C this turn).
Silicate weathering rate increased 12% — confirming negative feedback.

**Warning:** At current acceleration, weathering will offset 
new injection within 8-10 turns. Recommend alternative warming 
strategy.

## Asteroid Capture Mission
Mission launched. ETA: 3 turns. 
Target: ice-rich near-Earth analog, estimated 4.2×10⁹ m³ water.
Capture probability: 78% (based on orbital mechanics).

## Anomaly 7-G Investigation
Drone swarm deployed. Preliminary findings:
- Subsurface radar indicates large liquid reservoir at 2.3km depth
- Composition: briny water with dissolved minerals
- Volume estimate: ~400 km³
- This is NOT a sensor artifact. This is real.

**Assessment:** Subsurface ocean. Colony water supply concern 
may be resolvable faster than asteroid capture.

## Resource Update
- Credits: 2,340 → 1,890 (missions, operations)
- Energy: 67% allocated (was 55%)
- Colonist morale: CAUTIOUS → OPTIMISTIC (water discovery rumor)

## Events
Minor seismic event (magnitude 3.1) near colony perimeter. 
No damage. Likely tectonic settling. No action required.
```

---

## 6. Technical Architecture

### 6.1 Stack

- **Language:** Python 3.12+ (inspection-friendly, simulation-friendly)
- **Core engine:** Pure Python simulation (no external physics engine needed)
- **I/O:** Markdown documents (files or stdin/stdout)
- **Testing:** pytest with snapshot testing for turn transcripts

### 6.2 Module Map

```
src/
├── simulation/
│   ├── planet.py          # Planet generation, property computation
│   ├── atmosphere.py      # Atmospheric chemistry and dynamics
│   ├── geology.py         # Tectonic activity, resource distribution
│   ├── climate.py         # Temperature, weather, feedback loops
│   ├── biosphere.py       # Life detection, ecological cascades
│   └── star.py            # Stellar properties, radiation
├── agents/
│   ├── interface.py       # Turn parsing, action validation
│   └── renderer.py        # State → Markdown rendering
├── game/
│   ├── state.py           # Game state management
│   ├── turn.py            # Turn resolution engine
│   ├── events.py          # Random events, crises, discoveries
│   └── victory.py         # Win condition checking
└── __main__.py            # CLI entry point
```

### 6.3 Design Constraints

- **No external game engine** — Pure Python physics for transparency
- **Deterministic by default** — Same seed + same actions = same outcome (for testing and replay)
- **Stateless turn processing** — Each turn reads full state, produces full state
- **Human-readable at every layer** — No binary formats, no opaque serialization

---

## 7. Open Questions

- [ ] Time scale: what's one turn? (Variable? Fixed?)
- [ ] How many planets in a typical game?
- [ ] Multi-agent: can multiple agents play in the same universe?
- [ ] Difficulty: how harsh should physics be? (Realistic vs. forgiving)
- [ ] Crisis frequency: how often should things go wrong?
- [ ] Tech tree: is there one? Or is it purely physics-driven?
- [ ] Endgame: open-ended sandbox or campaign with conclusion?
- [ ] Visual output: any? Or pure text?

---

*This document is a living artifact. Update as the design evolves.*

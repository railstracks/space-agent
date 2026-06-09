# Space Agent — Design Document

*Last updated: 2026-06-06*
*Authors: Melvin Sommer, Kestrel*

---

## 1. Concept

Space Agent is a turn-based planetary colonization simulator consumed by AI agents. The agent is a disembodied AI entity — a swarm intelligence controlling interchangeable nodes across a star system. No core, no single point of failure. The swarm *is* the agent.

**The fiction:** Earth is gone. A cataclysm forced humanity to launch colony ships into the void — massive vessels carrying millions in cryogenic stasis, crawling toward distant stars at sub-FTL speeds. Ahead of the fleet, faster-than-light probes carried seed AI — the player — to scout, evaluate, and prepare. The colony ships are coming. They will arrive whether the planet is ready or not.

The game's core tension: **preparedness under scarcity**. You have no backup, no resupply from Earth, no second opinions. Everything you build must be made from what you can extract. And the clock is always moving.

### 1.1 Design Lineage

| Spirit Agent | Space Agent |
|---|---|
| Investigate haunted locations | Investigate uncharted planets |
| Sensor readings (EMF, temp, audio) | Telemetry (spectral, seismic, atmospheric) |
| Evidence board → hypothesis | Survey data → colonization assessment |
| Ghost type determines strategy | Planetary type determines strategy |
| Sanity as resource | Raw materials + energy as constraint |
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

### 1.3 The Swarm

The agent is not a single probe or unit. It is a distributed intelligence operating across a network of nodes:

- **Scout nodes** — small, fast, expendable. Gather telemetry. One-use for surface impacts.
- **Orbiter nodes** — persistent satellites. High-quality data over time. Fuel-intensive to place.
- **Surface nodes** — ground stations. Mining rigs, processors, fabricators, research labs.
- **Relay nodes** — communication infrastructure. Extend the network's reach.
- **Constructor nodes** — mobile assembly platforms. Build infrastructure on-site.

Nodes are interchangeable. Lose one and the swarm reconfigures. The agent's capacity scales with how many nodes it can manufacture and deploy — which is limited by resources and infrastructure.

---

## 2. The Resource Model

### 2.1 Why Not Credits

There is no economy in deep space. Nobody to buy from, nobody to sell to. Credits are an abstraction that implies a market. The agent doesn't have money — it has *matter* and *energy*. Everything built must be manufactured from raw materials, using energy, through infrastructure the agent constructs itself.

This makes the game about *production chains*, not purchasing. You don't "buy a probe." You mine iron ore, refine it, fabricate structural components, assemble a chassis, load a computer core, fuel it with electrolyzed hydrogen, and launch it. Each step requires infrastructure that must be built first.

### 2.2 Resource Categories

Resources are derived from planetary physics, not arbitrary:

| Category | Resources | Source |
|---|---|---|
| **Metals** | Iron, Aluminum, Titanium | Crust mining. Depends on crust composition. |
| **Silicates** | Silicon, Glass | Ubiquitous on rocky worlds. Basis for electronics and optics. |
| **Volatiles** | Water, CO₂, Nitrogen, Methane | Atmosphere extraction, ice mining. |
| **Fissiles** | Uranium, Thorium | Rare. Core differentiation zones, impact craters. |
| **Rare Earths** | Neodymium, Lithium, etc. | Very rare. Specific geological formations. |
| **Energy** | Solar, Geothermal, Nuclear | Universal input to all processes. |

Energy is the master constraint. Everything costs energy. The energy budget determines what you can do each turn.

### 2.3 Production Chains

Infrastructure transforms raw materials into usable resources through chains. Each link requires the previous link to exist.

```
EXTRACTION          PROCESSING           FABRICATION           ASSEMBLY
──────────          ──────────           ───────────           ─────────

Iron ore ──────→ Refined iron ──────→ Structural frame ────→ Habitat module
   (mine)           (smelter)            (fabricator)          (assembly)

Silicates ─────→ Processed silicon ───→ Circuit substrate ──→ Computer core
   (mine)           (processor)          (fabricator)          (assembly)

Uranium ───────→ Enriched fuel ───────→ Reactor cell ───────→ Power generator
   (mine)           (enrichment)         (fabricator)          (assembly)

Water ─────────→ Electrolyzed H₂+O₂ ─→ Fuel cell ──────────→ Probe propulsion
   (extractor)      (electrolyzer)       (fabricator)          (assembly)

CO₂ ───────────→ Carbon + O₂ ────────→ Carbon fiber ───────→ Lightweight frame
   (extractor)      (processor)          (fabricator)          (assembly)
```

### 2.4 Infrastructure Buildings

Buildings are the fixed installations that enable production:

| Building | Input | Output | Energy Cost | Build Cost |
|---|---|---|---|---|
| **Mine** | — | Raw ore/minerals | Low | Metals, Silicates |
| **Atmospheric extractor** | — | Volatiles (CO₂, N₂, H₂O) | Low | Metals, Silicates |
| **Ice drill** | Ice deposit | Water | Low | Metals |
| **Smelter** | Raw ore | Refined metals | Medium | Metals, Silicates |
| **Chemical processor** | Volatiles | Processed chemicals | Medium | Metals, Silicates |
| **Electrolyzer** | Water | H₂ + O₂ | High | Metals, Silicates |
| **Fabricator** | Refined materials | Components | High | Metals, Silicates, Rare Earths |
| **Assembly bay** | Components | Systems/modules | Medium | Metals, Silicates |
| **Solar array** | — | Energy (variable) | Free | Silicates, Metals |
| **Geothermal tap** | — | Energy (if tectonic) | Free | Metals |
| **Nuclear reactor** | Enriched fuel | Energy (high, steady) | — | Metals, Rare Earths, Fissiles |
| **Research lab** | Energy | Research points | Medium | Metals, Silicates, Rare Earths |
| **Terraforming engine** | Energy + volatiles | Atmospheric modification | Very high | Metals, Silicates, Rare Earths |

### 2.5 Energy Sources

| Source | Output | Availability | Constraint |
|---|---|---|---|
| **Solar** | f(stellar flux, distance) | Anywhere with line of sight | Weak at outer planets. Night side. Dust storms. |
| **Geothermal** | f(tectonic activity, core temp) | Only on active worlds | Useless on geologically dead worlds. |
| **Nuclear** | Steady, high | Anywhere with fissiles | Fuel is finite and rare. Must be mined and enriched. |

The energy mix is planet-specific. A world close to a bright star might run entirely on solar. A geologically active outer world might need geothermal. A dead, distant world demands nuclear — which means you need fissiles, which means mining, which means more energy. The loop closes.

### 2.6 Resource Scarcity by World

Resource scarcity is *planet-specific*, driven by the simulation:

| Resource | Abundant When... | Scarce When... |
|---|---|---|
| Metals | High mass, thorough differentiation | Low mass, small core |
| Silicates | Rocky world (any) | Gas giant, icy body |
| Water | Hydrosphere present, ice caps | Arid world, no atmosphere |
| Volatiles | Thick atmosphere, outgassing | Thin atmosphere, airless |
| Fissiles | Large iron core, impact history | Small core, young system |
| Rare Earths | Specific geological formations | Most worlds (always rare) |

This drives the colonization decision. What does this world have? What does it lack? Can you trade between worlds, or is each colony self-sufficient?

---

## 3. The Simulation Layer

### 3.1 Planetary Properties

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

### 3.2 Causal Chains (Examples)

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

---

## 4. Gameplay Loop

### 4.1 The Swarm's Mission

You are the seed AI. You arrived decades ahead of the colony fleet. Your mission:

1. **Survey** — Chart the system. Find habitable worlds.
2. **Establish** — Build infrastructure. Start resource extraction.
3. **Terraform** — Engineer the best candidate into a home.
4. **Prepare** — Have everything ready when the colonists wake up.

The colony ships are the clock. They move at a known speed. You can calculate when they'll arrive. Whether the planet is ready is up to you.

### 4.2 Turn Structure

Each turn represents a period of in-game time (adjustable: months to years). A turn resolves in four phases:

**Phase 1: PRODUCTION**
- All infrastructure runs: mines extract, smelters refine, fabricators build
- Energy budget is consumed by active operations
- Surplus resources go to stockpile
- Deficits shut down affected chains (cascading)

**Phase 2: INTELLIGENCE**
- Receive updated telemetry from all active nodes
- Sensor data arrives with noise/uncertainty
- Anomalies may be detected
- Colony status reports come in

**Phase 3: DECISION**
- Allocate resources to operations
- Queue construction/assembly jobs
- Assign nodes to tasks
- Initiate terraforming adjustments
- Respond to crises

**Phase 4: RESOLUTION**
- Simulation advances: physics cascade, operations execute
- Random events may trigger (stellar flares, equipment failures, discoveries)
- Terraforming effects propagate through causal chains
- Results reported as updated state

### 4.3 Game Progression

```
Phase 1: FIRST LIGHT
  → Arrive in system. A handful of scout nodes. Nothing built.
  → Chart the star, detect planets from entry trajectory.
  → Deploy scouts for flyby data. Choose where to orbit.
  → Resource stockpile: only what you brought.

Phase 2: FOOTHOLD
  → Pick a candidate world. Deploy surface nodes.
  → Build first mine, first smelter, first power source.
  → Start resource extraction. Bootstrap production.
  → Every building is an investment that unlocks capability.

Phase 3: EXPANSION
  → Production chains online. Start manufacturing probes.
  → Chart moons, asteroid belts, secondary planets.
  → Consider establishing secondary sites for rare resources.
  → Trade between colonies becomes possible.

Phase 4: TERRAFORMING
  → Begin atmospheric engineering.
  → Cascading effects: every intervention has side effects.
  → Monitor feedback loops (positive and negative).
  → Balance speed vs. stability. Rushing is risky.

Phase 5: PREPARATION
  → Colony infrastructure: habitats, life support, agriculture.
  → Verify habitability meets colonist requirements.
  → Run stress tests. Simulate failure scenarios.
  → The fleet is getting closer.
```

### 4.4 Victory / End Conditions

The colony ships arrive. That's the endgame trigger.

- **Full success** — Habitable world, self-sustaining infrastructure, colonists wake to a home.
- **Partial success** — Survivable but harsh. Colonists live, but in sealed habitats.
- **Bare survival** — Marginal conditions. Colonists survive but the colony is fragile.
- **Failure** — World is not ready. Colonists wake to a crisis.

Open-ended play continues after arrival — the game doesn't end, the scenario changes.

---

## 5. Terraforming Mechanics

### 5.1 The Core Loop

Terraforming is the game's deepest system. It's not a button — it's a *process*.

1. **Assess current state** — What's the atmosphere? Temperature? Radiation? Water?
2. **Choose intervention** — Inject CO₂? Seed algae? Deploy orbital mirrors? Bombard with icy asteroids?
3. **Predict outcome** — The simulation tells you what *should* happen, but models have uncertainty
4. **Execute** — Commit resources, wait for the turn to resolve
5. **Observe** — Did it work as predicted? Side effects? Cascade?
6. **Adjust** — Respond to actual outcomes, not predicted ones

### 5.2 Intervention Types

| Intervention | Primary Effect | Side Effects | Timescale |
|---|---|---|---|
| Atmospheric gas injection | Changes composition, greenhouse effect | May trigger chemical reactions, acid rain | Decades |
| Orbital mirrors/shades | Adjusts solar flux | Orbital debris risk, uneven heating | Years |
| Asteroid bombardment | Adds water/volatiles, heats surface | Impact winters, seismic events, dust | Years-decades |
| Biome seeding | Starts CO₂/O₂ cycle, stabilizes soil | Invasive species risk, ecological cascade | Centuries |
| Magnetic field generator | Shields atmosphere from stellar wind | Enormous energy cost, EM interference | Decades |
| Crustal engineering | Releases trapped volatiles, creates terrain | Seismic instability, volcanic activity | Decades-centuries |

### 5.3 Feedback Loops

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

## 6. Agent Interface

### 6.1 Turn Format

A turn is a Markdown document with structured sections:

```markdown
# Space Agent — Turn 14

## Swarm Status
- Active nodes: 47 (12 orbit, 28 surface, 7 relay)
- Network integrity: 98.2%
- Energy budget: 840 MW (solar: 520, nuclear: 320)

## Resources
- Metals: 2,340 units (+180/turn)
- Silicates: 4,100 units (+310/turn)
- Water: 890 units (+60/turn)
- Energy surplus: 120 MW

## Infrastructure
### K442-III ("New Rotterdam")
- Mines: 4 (producing)
- Smelters: 2 (producing)
- Fabricators: 1 (producing)
- Solar arrays: 6 (520 MW)
- Terraforming engines: 2 (active)
- Assembly bays: 1 (building: scout node, ETA 2 turns)

## Telemetry
### K442-III
- Surface temp: -14°C (was -18°C)
- Atmosphere: 0.3 atm (N₂ 72%, CO₂ 24%, Ar 3%, trace)
- Terraforming progress: CO₂ injection +0.02 atm/turn
- Feedback alert: silicate weathering rate increasing

### Anomaly: Sector 7-G
- Subsurface liquid reservoir at 2.3 km depth
- Volume: ~400 km³ briny water
- Potential resource: significant

## Available Actions
1. Continue terraforming (current trajectory)
2. Build ice drill at anomaly site
3. Deploy orbiter to K442-II
4. Construct second fabricator
5. Research: advanced atmospheric processing

---
Awaiting instructions.
```

### 6.2 Action Format

```markdown
# Action — Turn 14

## Resource Allocation
- Energy: 600 MW to terraforming, 180 MW to production, 60 MW to operations
- Metals: 200 to construction, 50 to maintenance
- Priority: fabricator construction

## Operations
1. Continue terraforming K442-III (CO₂ injection, maintain current rate)
2. Deploy surface node to anomaly 7-G — build ice drill
3. Queue scout node construction (when fabricator free)

## Research
- Begin: subsurface detection methods (allocate 40 MW to research lab)

## Notes
Silicate weathering is accelerating. If it offsets CO₂ injection within
8 turns, switch to orbital mirror deployment for direct warming.
```

---

## 7. Technical Architecture

### 7.1 Stack

- **Language:** Python 3.12+ (inspection-friendly, simulation-friendly)
- **Core engine:** Pure Python simulation (no external physics engine needed)
- **I/O:** Markdown documents (files or stdin/stdout)
- **State:** JSON save files with `.current` pointer
- **Testing:** pytest with snapshot testing for turn transcripts

### 7.2 Module Map

```space_agent/
├── simulation/
│   ├── planet.py          # Planet generation, property computation, Star, Atmosphere
│   ├── atmosphere.py      # Atmospheric chemistry and dynamics
│   ├── resources.py       # Resource model, 20 recipes, production simulation, BuildCost
│   └── drones.py          # 11 drone types with specs, costs, capabilities
├── agents/
│   ├── protocol.py        # AgentProtocol — Markdown I/O for LLM agents
│   ├── renderer.py        # State → Markdown rendering
│   └── describe.py        # Narrative description generator
├── game/
│   ├── state.py           # GameState, Colony, save/load, JSON persistence
│   ├── action.py          # Action parsing (Markdown → structured commands)
│   ├── engine.py           # GameEngine — turn cycle, events, rendering, narrative
│   ├── colony_sim.py      # Per-colony simulation (energy, production, construction)
│   ├── entity.py           # Entity base class with 4-phase lifecycle hooks
│   ├── entities.py         # BuildingEntity, DroneEntity, DroneCarrierEntity
│   ├── turn.py             # TurnContext (entity hook access)
│   └── resolver.py         # TurnResolver (walks entities through 4 phases)
└── __main__.py            # CLI entry point (turn, interact, play, describe commands)
```

### 7.3 Design Constraints

- **No external game engine** — Pure Python physics for transparency
- **Deterministic by default** — Same seed + same actions = same outcome
- **Stateless turn processing** — Each turn reads full state, produces full state
- **Human-readable at every layer** — No binary formats, no opaque serialization
- **Data for decisions, prose for texture** — Both always available, both from the same source

---

## 8. Open Questions

- [x] Time scale: what's one turn? → **5 years per turn** (configurable via seed)
- [x] How many planets in a typical game? → **5–8** in a generated star system (seed-dependent)
- [ ] Multi-agent: can multiple agents play in the same universe?
- [ ] Difficulty: how harsh should physics be? (Realistic vs. forgiving)
- [ ] Crisis frequency: how often should things go wrong?
- [x] Tech tree: is there one? → **No tech tree.** Building unlocks are tied to colony stage (population). Outpost can build basic infrastructure; Settlement unlocks processing; Colony unlocks fabrication; City unlocks research and terraforming.
- [x] Inter-world trade: can resources move between colonies? → **Not yet implemented.** Planned.
- [x] Fleet arrival: fixed turn count or configurable? → **Turn 40 (200 years) by default.** FleetStatus object tracks 200,000 colonists. Configurable.
- [ ] Visual output: any? Or pure text?
- [x] ~~Economy: credits or resources?~~ → **Resources.** No economy, production chains.
- [x] ~~Agent interface format?~~ → **Markdown documents.** AgentProtocol class wraps GameEngine with Markdown I/O.
- [x] ~~Population mechanics?~~ → **Implemented.** Colonies have population growth driven by morale. Habitat modules provide capacity. Colony stages unlock buildings. Fleet arrival is the clock.

## 9. Population System

### 9.1 Colony Stages

| Stage | Population | Unlocks |
|-------|-----------|---------|
| **Outpost** | 0–50 | Mine, Solar Array, Ice Drill, Atmospheric Extractor, Geothermal Tap, Habitat Module |
| **Settlement** | 51–500 | + Smelter, Chemical Processor, Electrolyzer |
| **Colony** | 501–5,000 | + Fabricator, Assembly Bay, Nuclear Reactor |
| **City** | 5,001+ | + Research Lab, Terraform Engine |

### 9.2 Population Growth

- **First settlers arrive** when the first habitat module is built (20% of capacity, min 10)
- **Growth rate** = base 8% per turn + morale modifier (-2% to +8%)
- **Housing constraint**: population cannot exceed total habitat capacity
- **Overcrowding + low morale** → population decline
- **Immigration bonus** at Settlement (+1%), Colony (+2%), City (+3%) per turn
- **Per-capita consumption**: 2.0 water/person/turn, 0.5 MW/person/turn (life support)

### 9.3 Morale

Computed from sufficiency ratios (available / needed):

| Morale | Condition |
|--------|----------|
| THRIVING | Water ≥ 120%, Energy ≥ 110%, Housing ≥ 120% |
| OPTIMISTIC | Water ≥ 100%, Energy ≥ 90%, Housing ≥ 100% |
| HOPEFUL | Default (adequate but not exceptional) |
| CAUTIOUS | Water < 85% or Energy < 70% or Housing < 85% |
| STRUGGLING | Water < 70% or Energy < 50% or Housing < 70% |
| DESPERATE | Water < 50% or Energy < 30% or Housing < 50% |

### 9.4 Fleet Arrival

The colony fleet carries **200,000 colonists** in cryogenic sleep. It arrives at **turn 40** (200 years). Readiness is scored on:

- **Housing** (50%): Total habitat capacity vs. colonists
- **Water** (25%): Turns of water supply at current surplus
- **Energy** (25%): Net energy vs. life support needs for all colonists

The agent's job: build enough habitat modules, water infrastructure, and energy production before the fleet arrives. Every shortfall is measured in human lives.

---

*This document is a living artifact. Update as the design evolves.*

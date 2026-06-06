"""Turn resolver — orchestrates the four-phase turn cycle.

The resolver doesn't know what entities *do*. It knows the order
to call their hooks and how to collect the results. Entity behavior
is entirely encapsulated in their hook implementations.

Turn phases:
  1. PRODUCTION   — entities produce/consume resources
  2. INTELLIGENCE — entities gather data, update sensors
  3. DECISION     — entities process orders (auto or player)
  4. RESOLUTION   — physics propagation, events, state updates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from space_agent.game.entity import Entity, EntityReport
from space_agent.game.turn import TurnContext


@dataclass
class TurnResult:
    """The result of resolving one complete turn."""
    turn: int
    phase_reports: dict[str, list[EntityReport]] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "phase_reports": {
                phase: [r.to_dict() for r in reports]
                for phase, reports in self.phase_reports.items()
            },
            "events": self.events,
            "summary": self.summary,
        }


PHASES = ["production", "intelligence", "decision", "resolution"]


def resolve_turn(
    entities: list[Entity],
    ctx: TurnContext,
) -> TurnResult:
    """Resolve one complete turn across all phases.

    Walks all entities for each phase in order. Collects reports
    and events. Returns a TurnResult with the complete state change.
    """
    result = TurnResult(turn=ctx.turn)

    # Filter to entities that should participate
    active_entities = [
        e for e in entities
        if e.status.value not in ("destroyed", "lost")
    ]

    for phase in PHASES:
        phase_reports = []
        hook_name = f"on_{phase}"

        for entity in active_entities:
            hook = getattr(entity, hook_name, None)
            if hook is None:
                continue

            try:
                report = hook(ctx)
                phase_reports.append(report)
            except Exception as exc:
                report = EntityReport(
                    entity_id=entity.entity_id,
                    entity_type=entity.entity_type.value,
                    hook=phase,
                    success=False,
                    messages=[f"Error: {exc}"],
                )
                phase_reports.append(report)

        result.phase_reports[phase] = phase_reports

    # Collect events from context
    result.events = ctx.events

    # Build summary
    result.summary = _build_summary(result, ctx)

    return result


def _build_summary(result: TurnResult, ctx: TurnContext) -> dict:
    """Build a human-readable summary of the turn."""
    total_produced = {}
    total_consumed = {}
    messages = []
    errors = []

    for phase, reports in result.phase_reports.items():
        for report in reports:
            for k, v in report.produced.items():
                total_produced[k] = total_produced.get(k, 0) + v
            for k, v in report.consumed.items():
                total_consumed[k] = total_consumed.get(k, 0) + v
            if not report.success:
                errors.extend(report.messages)
            else:
                messages.extend(report.messages)

    return {
        "turn": result.turn,
        "energy_used_mw": ctx.energy_consumed_mw,
        "energy_total_mw": ctx.energy_available_mw,
        "produced": {k: round(v, 1) for k, v in total_produced.items() if v > 0},
        "consumed": {k: round(v, 1) for k, v in total_consumed.items() if v > 0},
        "events": len(result.events),
        "errors": len(errors),
        "messages": messages,
    }


def render_turn_summary(result: TurnResult) -> str:
    """Render a TurnResult as Markdown for agent consumption."""
    s = result.summary
    lines = [
        f"# Turn {result.turn} — Resolution",
        "",
        f"**Energy:** {s['energy_used_mw']:.0f} / {s['energy_total_mw']:.0f} MW consumed",
    ]

    if s["produced"]:
        lines.append(f"**Produced:** {', '.join(f'{v} {k}' for k, v in s['produced'].items())}")
    if s["consumed"]:
        lines.append(f"**Consumed:** {', '.join(f'{v} {k}' for k, v in s['consumed'].items())}")

    if result.events:
        lines.append("")
        lines.append("## Events")
        for event in result.events:
            lines.append(f"- [{event.get('type', '?')}] {event['description']}")

    # Entity messages by phase
    for phase in PHASES:
        reports = result.phase_reports.get(phase, [])
        phase_messages = []
        for r in reports:
            phase_messages.extend(r.messages)
        if phase_messages:
            lines.append("")
            lines.append(f"## {phase.title()}")
            for msg in phase_messages:
                lines.append(f"- {msg}")

    return "\n".join(lines)

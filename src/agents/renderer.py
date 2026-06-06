"""Markdown renderer for game state.

Converts Planet, Star, and GameState objects into the structured
Markdown format defined in docs/AGENT-PROTOCOL.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .planet import Planet, Star


def render_star(star: Star) -> str:
    """Render star properties as Markdown."""
    lines = [
        f"### {star.name}",
        f"- Spectral type: **{star.spectral_type}**",
        f"- Luminosity: {star.luminosity_solar:.2f} L☉",
        f"- Temperature: {star.temperature_k:.0f} K",
        f"- Habitable zone: {star.habitable_zone_inner_au:.2f}–{star.habitable_zone_outer_au:.2f} AU",
    ]
    return "\n".join(lines)


def render_planet_table(planets: list[Planet], quality: str = "ORBITAL") -> str:
    """Render planet comparison as a Markdown table."""
    header = "| Designation | Dist (AU) | Mass (M⊕) | Gravity | Temp (°C) | Atm (atm) | Habitability |"
    sep = "|-------------|-----------|-----------|---------|-----------|-----------|--------------|"
    rows = []
    for p in planets:
        habitability = f"{p.habitability_index:.0f}/100"
        atm = f"{p.atmosphere.total_pressure:.2f}"
        temp = f"{p.surface_temperature_c:+.0f}"
        rows.append(
            f"| {p.designation} | {p.orbital_distance_au:.2f} | {p.mass_earth:.1f} | "
            f"{p.surface_gravity:.2f}g | {temp} | {atm} | {habitability} |"
        )
    return "\n".join([header, sep] + rows)


def render_planet_detail(planet: Planet) -> str:
    """Render detailed planet properties as Markdown."""
    lines = [
        f"### {planet.designation} — {planet.name}",
        f"",
        f"**Physical:**",
        f"- Mass: {planet.mass_earth:.2f} M⊕",
        f"- Radius: {planet.radius_earth:.2f} R⊕",
        f"- Surface gravity: **{planet.surface_gravity:.2f}g**",
        f"- Escape velocity: {planet.escape_velocity:.1f} km/s",
        f"- Rotation: {planet.rotation_period_hours:.1f} hours",
        f"- Axial tilt: {planet.axial_tilt_degrees:.1f}°",
        f"",
        f"**Orbital:**",
        f"- Distance: {planet.orbital_distance_au:.2f} AU",
        f"- Solar flux: {planet.solar_flux:.0f} W/m²",
        f"- Equilibrium temp: {planet.equilibrium_temperature - 273.15:+.1f}°C (no greenhouse)",
        f"",
        f"**Atmosphere ({planet.atmospheric_retention}):**",
        f"- Total pressure: **{planet.atmosphere.total_pressure:.3f} atm**",
        f"- Greenhouse warming: +{planet.atmosphere.greenhouse_factor:.1f}°C",
    ]

    comp = planet.atmosphere.summary()
    comp_str = ", ".join(f"{k} {v:.1f}%" for k, v in comp.items() if v > 0.1)
    lines.append(f"- Composition: {comp_str}")

    lines.extend([
        f"",
        f"**Surface:**",
        f"- Surface temperature: **{planet.surface_temperature_c:+.1f}°C**",
        f"- Albedo: {planet.albedo:.2f}",
        f"- Hydrosphere: {planet.hydrosphere_liquid_fraction * 100:.1f}% liquid, "
        f"{planet.hydrosphere_ice_fraction * 100:.1f}% ice",
        f"- Magnetic field: {planet.magnetic_field:.2f} Earth-normal",
        f"",
        f"**Assessment:**",
        f"- Habitability index: **{planet.habitability_index:.0f}/100**",
        f"- Atmospheric retention: {planet.atmospheric_retention}",
    ])

    return "\n".join(lines)

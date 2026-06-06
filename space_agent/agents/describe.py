"""Narrative description generator for planets.

Produces prose descriptions from physical properties. This is a
rendering concern — the simulation engine only deals with physics.
The describe() function takes a planet dict and returns human-readable
text suitable for game transcripts and showcase material.

Descriptions are generated per-category and composed. Each category
keys off property ranges to select appropriate text, then fills in
planet-specific details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_agent.simulation.planet import Planet


def describe(planet: Planet) -> str:
    """Generate a full narrative description of a planet.

    Composes per-category descriptions into a single readable block.
    """
    sections = []

    # Sky and atmosphere
    atm = _describe_atmosphere(planet)
    if atm:
        sections.append(atm)

    # Surface conditions
    surface = _describe_surface(planet)
    if surface:
        sections.append(surface)

    # Gravity and movement
    gravity = _describe_gravity(planet)
    if gravity:
        sections.append(gravity)

    # Magnetic field and radiation
    radiation = _describe_radiation(planet)
    if radiation:
        sections.append(radiation)

    # Resources and geology
    geology = _describe_geology(planet)
    if geology:
        sections.append(geology)

    # Habitability summary
    habitability = _describe_habitability(planet)
    if habitability:
        sections.append(habitability)

    return "\n\n".join(sections)


def _describe_atmosphere(planet: Planet) -> str:
    """Describe atmospheric appearance and feel."""
    atm = planet.atmosphere
    pressure = atm.total_pressure
    temp_c = planet.surface_temperature_c
    comp = atm.summary()

    # Determine dominant gas
    dominant = max(comp, key=comp.get)
    dominant_pct = comp[dominant]

    parts = []

    # Pressure character
    if pressure < 0.01:
        parts.append("The planet has no appreciable atmosphere — a near-vacuum exposed directly to space.")
    elif pressure < 0.3:
        parts.append("The atmosphere is exceedingly thin, barely more than a whisper of gas clinging to the surface.")
    elif pressure < 0.7:
        parts.append("The atmosphere is thin compared to Earth's, though dense enough to support weather patterns.")
    elif pressure <= 1.5:
        parts.append("The atmospheric pressure is comparable to Earth's, thick enough to support complex weather systems.")
    elif pressure <= 3.0:
        parts.append("The atmosphere is dense and heavy, pressing down on the surface with noticeable weight.")
    else:
        parts.append("The atmosphere is crushingly dense, a deep ocean of gas that would flatten unprotected structures.")

    # Composition and color
    co2_pct = comp.get("CO₂", 0)
    so2_present = atm.other > 0.005 or atm.methane > 0.01
    h2o_pct = comp.get("H₂O", 0)

    if dominant == "CO₂" and dominant_pct > 50:
        if temp_c > 100:
            parts.append(
                "The sky is a perpetual, hazy orange-yellow under a thick carbon dioxide blanket. "
                "Dense clouds trap heat relentlessly, creating a suffocating greenhouse environment."
            )
        elif temp_c > 0:
            parts.append(
                "A thick carbon dioxide atmosphere casts the sky in a pale, muted orange. "
                "Cloud cover is extensive, diffusing what light reaches the surface."
            )
        else:
            parts.append(
                "A dense CO₂ atmosphere gives the sky a washed-out amber tone. "
                "The cold is somewhat mitigated by greenhouse trapping, but the air remains hostile."
            )
    elif dominant == "N₂" and dominant_pct > 60:
        if h2o_pct > 1:
            parts.append(
                "A nitrogen-dominated atmosphere supports cloud formation and weather cycles. "
                "Water vapor is present, suggesting potential for precipitation."
            )
        else:
            parts.append(
                "A clear nitrogen atmosphere would give the sky an Earth-like quality, "
                "though the absence of significant water vapor means cloud formation is limited."
            )
    elif dominant == "N₂" and co2_pct > 15:
        parts.append(
            "The nitrogen atmosphere carries a significant CO₂ load, enough to tint the sky "
            "slightly and create a modest greenhouse effect."
        )
    elif pressure < 0.01:
        pass  # already handled above
    else:
        parts.append(
            f"The atmosphere is primarily {dominant.replace('₂', '')} "
            f"({dominant_pct:.0f}%), with a composition unlike anything familiar."
        )

    # Toxicity note
    o2_pct = comp.get("O₂", 0)
    if o2_pct < 5 and pressure > 0.1:
        if o2_pct < 0.5:
            parts.append("The air is entirely unbreathable — no free oxygen is detectable.")
        else:
            parts.append("Trace oxygen is present but far below what would sustain respiration.")

    return " ".join(parts) if parts else ""


def _describe_surface(planet: Planet) -> str:
    """Describe surface conditions and terrain."""
    temp_c = planet.surface_temperature_c
    liquid = planet.hydrosphere_liquid_fraction
    ice = planet.hydrosphere_ice_fraction

    parts = []

    # Temperature feel
    if temp_c > 200:
        parts.append("The surface is a furnace — temperatures high enough to melt lead and vaporize most organic compounds.")
    elif temp_c > 100:
        parts.append("The surface is scorching, far beyond what any unprotected material could endure for long.")
    elif temp_c > 50:
        parts.append("The surface is punishingly hot, hostile to both biology and most electronics.")
    elif temp_c > 30:
        parts.append("The surface is hot by human standards, though within the range that engineered systems could handle.")
    elif temp_c > 15:
        parts.append("The surface temperature is mild and comfortable — remarkably Earth-like.")
    elif temp_c > 0:
        parts.append("The surface is cool but above freezing. Hardy systems could operate with insulation.")
    elif temp_c > -30:
        parts.append("The surface is well below freezing. Ice and frost dominate the landscape.")
    elif temp_c > -80:
        parts.append("The surface is deeply cold, a frozen world where only the hardiest materials remain ductile.")
    else:
        parts.append("The surface is bitterly cold — a deep freeze where even carbon dioxide may frost out of the atmosphere.")

    # Hydrosphere
    if liquid > 0.15:
        parts.append(f"Liquid water covers roughly {liquid * 100:.0f}% of the surface, forming vast basins and shallow seas.")
    elif liquid > 0.01:
        parts.append(f"Scattered lakes and ponds of liquid water cover about {liquid * 100:.0f}% of the surface.")
    elif liquid > 0:
        parts.append("Traces of liquid water exist in sheltered, low-elevation basins — a precious hint of potential.")

    if ice > 0.2:
        parts.append(f"Ice sheets cover {ice * 100:.0f}% of the surface, gleaming white against the terrain.")
    elif ice > 0.01:
        parts.append(f"Patchy ice covers about {ice * 100:.0f}% of the surface, concentrated at higher latitudes.")

    # Terrain hint from temperature + composition
    if temp_c > 100 and planet.atmosphere.co2 > 0.3:
        parts.append("The landscape is dominated by volcanic plains — vast basaltic flats punctuated by shield volcanoes and fumaroles.")
    elif temp_c < -50 and planet.atmosphere.total_pressure < 0.1:
        parts.append("The terrain is barren and cratered, an airless wasteland of impact scars and dust.")
    elif liquid < 0.01 and ice < 0.01 and temp_c > 0:
        parts.append("The terrain is arid and dry, a desert world with no surface water.")

    return " ".join(parts) if parts else ""


def _describe_gravity(planet: Planet) -> str:
    """Describe the effect of gravity on movement and structures."""
    g = planet.surface_gravity

    if g < 0.3:
        return "Gravity is negligible — a near-weightless environment where anchoring is essential and movement is more like flying."
    elif g < 0.6:
        return (
            f"Gravity is light at {g:.1f}g. Movement feels buoyant, each step carrying far "
            "more distance than on Earth. Structures can be lighter and taller, but retaining "
            "an atmosphere is this world's deeper challenge."
        )
    elif g < 0.9:
        return (
            f"Gravity is slightly below Earth-normal at {g:.1f}g. The difference is subtle but "
            "perceptible — a lightness in the limbs that would take adjustment."
        )
    elif g <= 1.3:
        return f"Gravity is Earth-like at {g:.1f}g, one less variable to engineer around."
    elif g <= 2.0:
        return (
            f"Gravity is heavy at {g:.1f}g. Every step carries the weight of an extra burden. "
            "Structural engineering becomes significantly more demanding, and launch costs "
            "increase steeply — escape velocity is correspondingly higher."
        )
    else:
        return (
            f"Gravity is crushing at {g:.1f}g. Movement without mechanical assistance would be "
            "exhausting or impossible. Structures must be over-engineered, and reaching orbit "
            "demands enormous energy expenditure."
        )


def _describe_radiation(planet: Planet) -> str:
    """Describe magnetic field and radiation environment."""
    field = planet.magnetic_field
    star = planet.star
    flux = planet.solar_flux

    parts = []

    if field > 1.0:
        parts.append("A powerful magnetic field wraps the planet, providing strong shielding against stellar radiation.")
    elif field > 0.5:
        parts.append("A moderate magnetic field offers meaningful radiation protection, though not complete coverage.")
    elif field > 0.2:
        parts.append("A weak magnetic field provides only partial radiation shielding — surface exposure is a concern during stellar flares.")
    else:
        parts.append("The planet has negligible magnetic protection. Stellar radiation reaches the surface largely unimpeded.")

    # Stellar flux context
    earth_flux = 1361  # W/m²
    if flux > earth_flux * 3:
        parts.append("The star floods the planet with intense radiation, making shielding a critical survival requirement.")
    elif flux > earth_flux * 1.5:
        parts.append("Solar flux is high enough that radiation management is a factor in colony design.")
    elif flux < earth_flux * 0.3:
        parts.append("Sunlight is dim — the star is distant or faint. Solar power yields are low, and photosynthesis would be marginal.")

    return " ".join(parts) if parts else ""


def _describe_geology(planet: Planet) -> str:
    """Describe geological activity and mineral resources."""
    parts = []
    core = planet.iron_core_fraction

    # Tectonic inference from core and age
    if core > 0.35 and planet.star.age_gyr < 6:
        parts.append("Geological activity is vigorous — a large iron core drives a strong dynamo and active plate tectonics.")
    elif core > 0.25:
        parts.append("Moderate geological activity persists, with occasional quakes and volcanic events.")
    else:
        parts.append("The interior is largely quiescent. The planet is geologically mature, with few active features.")

    # Resource hint from mass and composition
    if planet.mass_earth > 2.0:
        parts.append("The planet's high mass suggests thorough differentiation — heavy elements concentrated in the core, with accessible metal deposits in the crust.")
    elif planet.mass_earth > 1.0:
        parts.append("Terrestrial-style differentiation likely produces a mix of accessible metals and silicates.")

    return " ".join(parts) if parts else ""


def _describe_habitability(planet: Planet) -> str:
    """Summarize habitability assessment."""
    h = planet.habitability_index
    temp_c = planet.surface_temperature_c

    if h >= 75:
        return f"This world is remarkably habitable (index: {h:.0f}/100). With modest engineering, a self-sustaining colony is feasible."
    elif h >= 50:
        return (
            f"This world is marginally habitable (index: {h:.0f}/100). Significant terraforming "
            "would be required, but the fundamentals are present."
        )
    elif h >= 25:
        return (
            f"This world is challenging (index: {h:.0f}/100). Terraforming would be a "
            "multi-generational megaproject, but not impossible."
        )
    else:
        return (
            f"This world is deeply hostile (index: {h:.0f}/100). Colonization would require "
            "fully sealed habitats — terraforming is infeasible with current technology."
        )

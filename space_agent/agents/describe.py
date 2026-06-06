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
        parts.append("The world's surface blazes with an infernal fury, a hellish landscape where temperatures soar high enough to reduce lead to molten rivers and vaporize organic matter in moments. The air itself seems to shimmer and distort with heat, creating mirages that dance across a terrain of cracked, baked rock. Any probe landing here would need extraordinary cooling systems just to survive long enough to transmit data before its components begin to fail in the relentless thermal assault.")
    elif temp_c > 100:
        parts.append("The planet's surface is a scorching wasteland, where the sun beats down with merciless intensity. Rocks glow dull red in the perpetual heat, and the atmosphere carries the acrid scent of vaporized minerals. Unprotected equipment would rapidly degrade as plastics warped, metals expanded, and electronics succumbed to thermal stress. Only the most specialized heat-resistant materials could withstand this hostile environment for more than a few hours.")
    elif temp_c > 50:
        parts.append("A harsh, unforgiving heat blankets this world's surface, creating an environment that pushes the limits of even our most advanced technology. The landscape appears bleached and weathered by constant thermal stress, with heat ripples constantly disturbing the horizon. Biological systems would rapidly dehydrate and fail, while conventional electronics would require extensive cooling to prevent catastrophic failure. This is a world that demands respect and careful engineering to explore.")
    elif temp_c > 30:
        parts.append("The surface radiates a dry, oppressive heat reminiscent of the hottest deserts on Earth. While challenging for human physiology, this temperature range remains within the operational parameters of well-designed exploration equipment. The terrain likely features heat-adapted geological formations, perhaps with mineral deposits that have been baked into interesting crystalline patterns by the persistent warmth. Careful thermal management would be essential for extended surface operations.")
    elif temp_c > 15:
        parts.append("The surface offers a surprisingly temperate climate, with temperatures falling within a comfortable range for human activity. This world's environment feels remarkably familiar, with conditions that would allow for extended exploration without extreme protective measures. The landscape might support complex geological features shaped by moderate thermal cycles, potentially including erosion patterns similar to those found in temperate regions of Earth. This temperature range represents a rare and valuable find in the cosmos.")
    elif temp_c > 0:
        parts.append("A crisp coolness dominates the surface, with temperatures hovering just above the freezing point of water. The landscape likely features a fascinating interplay between liquid and solid states, perhaps with frost patterns that shift with daily temperature variations. While chilly by human standards, this environment would be manageable with proper insulation. The cool temperatures might preserve interesting geological features and potentially support unique chemical processes that would be impossible in warmer climates.")
    elif temp_c > -30:
        parts.append("The surface is gripped by a persistent cold that would challenge any explorer. Ice likely blankets much of the terrain, creating a crystalline wonderland of frozen formations. The landscape appears stark and pristine, with sharp edges preserved by the freezing temperatures. Specialized equipment with robust heating systems would be essential for any surface operations, as conventional machinery would quickly succumb to the cold. This world exists in a state of suspended animation, its features locked in place by the deep freeze.")
    elif temp_c > -80:
        parts.append("An extreme arctic environment dominates this world, with temperatures that render most materials brittle and unworkable. The surface is likely a frozen desert where even the most resilient Earth-based equipment would struggle to function. The atmosphere itself might be partially condensed, creating unusual optical phenomena in the sky. Only specially engineered probes with exotic materials capable of maintaining ductility at these temperatures could effectively explore this frozen realm, where molecular motion has been reduced to a mere crawl.")
    else:
        parts.append("This world exists in a state of profound cold that challenges our understanding of temperature extremes. The surface is so frigid that even carbon dioxide would freeze and fall as dry ice snow, creating an alien landscape of exotic crystalline formations. The atmosphere itself might be nearly frozen, with only the thinnest of gases remaining in a gaseous state. Exploring such an environment would require technology that pushes the boundaries of material science, as conventional physics begins to behave strangely at these temperature extremes, where quantum effects might become visible on a macroscopic scale.")

    # Hydrosphere
    if liquid > 0.15:
        parts.append(f"Vast oceans dominate the world, with shimmering azure waves lapping across {liquid * 100:.0f}% of the planet's surface, their depths hiding countless mysteries.")
    elif liquid > 0.01:
        parts.append(f"Scattered across the landscape, crystalline lakes and winding rivers cover approximately {liquid * 100:.0f}% of the surface, their surfaces reflecting the sky like mirrors.")
    elif liquid > 0:
        parts.append("In sheltered valleys and deep craters, small pockets of liquid water persist — rare oases that might sustain life in an otherwise arid world.")
    if ice > 0.2:
        parts.append(f"Magnificent glaciers and frozen tundras blanket {ice * 100:.0f}% of the planet, creating a dazzling white landscape that sparkles under the light of distant stars.")
    elif ice > 0.01:
        parts.append(f"Patches of permafrost and seasonal ice cover about {ice * 100:.0f}% of the surface, forming intricate patterns of frost that transform the terrain with the changing seasons.")

   # Terrain hint from temperature + composition
    if temp_c > 100 and planet.atmosphere.co2 > 0.3:
        parts.append("The planet's surface is a hellscape of volcanic plains stretching to the horizon. Dark basaltic rock forms vast, cracked flats that shimmer with heat distortion. Towering shield volcanoes dot the landscape, their slopes streaked with glowing lava flows. Fumaroles punctuate the terrain, spewing columns of toxic gases into the oppressive atmosphere. The ground itself seems to breathe, with periodic tremors sending ripples through the semi-molten surface.")
    elif temp_c < -50 and planet.atmosphere.total_pressure < 0.1:
        parts.append("An airless graveyard of cosmic collisions spreads before you. The surface is a stark mosaic of impact craters of all sizes, from microscopic pockmarks to colossal basins hundreds of kilometers across. In the absence of atmosphere, the regolith remains undisturbed for eons, preserving the violent history of this world in perfect detail. Sharp-edged rocks and fine dust create a treacherous landscape that has never known wind or weather to smooth its harsh features.")
    elif liquid < 0.01 and ice < 0.01 and temp_c > 0:
        parts.append("Endless dunes of fine particulate matter roll across the planet's surface like frozen waves of an ancient ocean. The landscape is a monochromatic study in beige and ochre, with occasional outcroppings of bare rock breaking through the sandy expanse. No rivers, lakes, or even morning dew grace this world—the atmosphere holds barely enough moisture to form the occasional dust storm rather than rain. The sun beats down mercilessly on this parched realm where water exists only as a distant memory or buried treasure.")

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
        parts.append("Powerful magnetic field lines weave a protective cocoon around the planet, creating spectacular auroral displays at the poles while deflecting harmful cosmic and stellar radiation. The magnetosphere extends far into space, forming a formidable shield against the star's particle emissions.")
    elif field > 0.5:
        parts.append("Moderate magnetic forces shape the planet's interaction with space, creating visible auroras during periods of heightened stellar activity. The protective field extends several planetary radii into space, significantly reducing but not eliminating radiation exposure on the surface.")
    elif field > 0.2:
        parts.append("Weak magnetic ripples barely reach beyond the planet's atmosphere, offering limited protection during normal conditions but leaving the surface vulnerable during stellar flares. Occasional auroral glimmers mark where the feeble field interacts with charged particles from the star.")
    else:
        parts.append("With virtually no magnetic defense, the planet lies exposed to the full fury of space. Stellar winds and cosmic rays bombard the surface unimpeded, stripping away atmosphere over geological time and rendering the surface hostile to complex life.")

    # Stellar flux context
    earth_flux = 1361  # W/m²
    if flux > earth_flux * 3:
        parts.append("The star's fury scours the planet's surface, bathing it in relentless radiation that would strip the atmosphere from lesser worlds. Colonists must live beneath thick radiation shields or in deep subterranean habitats, while specialized materials are required for any surface structures to prevent rapid degradation. The intense stellar wind creates spectacular auroral displays visible even during daylight hours.")
    elif flux > earth_flux * 1.5:
        parts.append("The sun hangs heavy in the sky, its disk noticeably larger than Earth's. Radiation levels require careful management in colony design, with protected corridors connecting buildings and specialized glass that filters harmful wavelengths. Colonists must monitor their exposure time, especially during peak hours when the star's intensity can cause sunburn in minutes rather than hours. The landscape is baked in perpetual summer, with temperatures soaring in unshaded areas.")
    elif flux < earth_flux * 0.3:
        parts.append("The star hangs in the sky like a pale coin, its light barely sufficient to cast shadows. Daytime resembles a perpetual twilight on Earth, with colors washed out and visibility limited. Solar panels struggle to generate meaningful power, forcing colonies to rely on alternative energy sources. Plants must be genetically engineered to photosynthesize efficiently in the dim conditions, and the cold climate requires constant heating to maintain habitable temperatures.")

    return " ".join(parts) if parts else ""


def _describe_geology(planet: Planet) -> str:
    """Describe geological activity and mineral resources."""
    parts = []
    core = planet.iron_core_fraction
    # Tectonic inference from core and age
    if core > 0.35 and planet.star.age_gyr < 6:
        parts.append("Beneath the surface, the planet's heart beats with restless fury. A massive iron core churns with magnetic energy, powering a dynamo that reaches tendrils of force far into space. The crust fractures and reforms in an endless cycle, where tectonic plates grind against each other in slow, inexorable motion, birthing mountain ranges that would dwarf Earth's Himalayas. Volcanic chains punctuate the landscape like wounds, spewing molten rock and precious metals from the planet's fiery depths. This is a world still in its geological youth, its face constantly reshaped by the violent processes of formation.")
    elif core > 0.25:
        parts.append("The planet's geological pulse beats at a measured pace, neither frenetic nor dormant. Deep beneath the surface, convection currents stir the mantle with enough vigor to occasionally remind inhabitants of the planet's living nature. Earthquakes ripple through the crust at predictable intervals, while volcanic regions smolder with contained energy, occasionally releasing pressure in spectacular displays. The landscape bears the scars of ancient geological violence—mountain ranges worn by eons of erosion, vast plains formed by long-cooled lava flows, and mineral-rich regions where the planet's bounty lies exposed for those who know where to look.")
    else:
        parts.append("This ancient world has settled into geological tranquility. The once-fierce processes that shaped its features have largely subsided, leaving behind a landscape of remarkable stability. The iron core, while still present, no longer drives the violent tectonic activity of the planet's youth. Instead, gentle undulations mark the surface, with only occasional tremors disturbing the long peace. Mountains have been worn to gentle hills by billions of years of weather, their mineral wealth exposed through gradual erosion. The planet's geological story is written in its sedimentary layers—a testament to the vast ages that have passed since the last great upheaval reshaped its face.")
    # Resource hint from mass and composition
    if planet.mass_earth > 2.0:
        parts.append("The planet's substantial mass has worked as a natural refinery over billions of years. Heavy elements have sunk deep into the core, creating a treasure trove of metals that would be the envy of any spacefaring civilization. Yet the crust remains richly endowed with accessible deposits—veins of precious metals threading through mountain ranges, rare earth elements concentrated in ancient geological formations, and crystal formations of breathtaking purity and size. The high gravity has compressed these resources into denser configurations than found on smaller worlds, making mining operations uniquely challenging but potentially extraordinarily rewarding.")
    elif planet.mass_earth > 1.0:
        parts.append("The planet's Earth-like mass has produced a geological bounty familiar yet distinct. Continental drift has created diverse mineral provinces—mountain ranges rich in metallic ores, ancient seabeds transformed into fossil fuel deposits, and volcanic regions where the planet's internal processes have concentrated rare elements. The moderate gravity allows for a balanced distribution of resources, neither too compressed nor too dispersed. Prospectors would find a world where the planet's geological history has conveniently sorted and concentrated its wealth, creating natural resource maps that tell the story of tectonic movements across hundreds of millions of years.")

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

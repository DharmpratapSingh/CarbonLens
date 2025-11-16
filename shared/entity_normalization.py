"""
Shared entity normalization and resolution utilities.
Consolidates entity handling logic used across the application.
"""
from typing import Any
from difflib import SequenceMatcher


# Country aliases dictionary
COUNTRY_ALIASES: dict[str, str] = {
    # United States variations
    "USA": "United States of America",
    "US": "United States of America",
    "U.S.": "United States of America",
    "U.S.A.": "United States of America",
    "United States": "United States of America",
    "America": "United States of America",

    # United Kingdom variations
    "UK": "United Kingdom",
    "U.K.": "United Kingdom",
    "Britain": "United Kingdom",
    "Great Britain": "United Kingdom",
    "England": "United Kingdom",  # Note: England is part of UK

    # China variations
    "China": "People's Republic of China",
    "PRC": "People's Republic of China",
    "Mainland China": "People's Republic of China",

    # Russia variations
    "Russia": "Russian Federation",

    # Korea variations
    "South Korea": "Republic of Korea",
    "North Korea": "Democratic People's Republic of Korea",
    "DPRK": "Democratic People's Republic of Korea",
    "ROK": "Republic of Korea",

    # Other common variations
    "Holland": "Netherlands",
    "Myanmar": "Burma",
    "Czech Republic": "Czechia",
    "Ivory Coast": "Côte d'Ivoire",
    "UAE": "United Arab Emirates",
    "Vietnam": "Viet Nam",

    # Database-specific abbreviations (from EDGAR data)
    "bosnia and herz.": "Bosnia and Herzegovina",
    "bosnia and herz": "Bosnia and Herzegovina",
    "dem. rep. congo": "Democratic Republic of the Congo",
    "eq. guinea": "Equatorial Guinea",
    "n. mariana islands": "Northern Mariana Islands",
    "st. kitts and nevis": "Saint Kitts and Nevis",
    "st. lucia": "Saint Lucia",
    "st. vincent and the grenadines": "Saint Vincent and the Grenadines",
    "são tomé and príncipe": "Sao Tome and Principe",
    "trinidad and tobago": "Trinidad and Tobago",
    "u.s. virgin islands": "United States Virgin Islands",
    "united rep. of tanzania": "United Republic of Tanzania",

    # Additional common variations
    "czech rep.": "Czechia",
    "central african rep.": "Central African Republic",
    "dom. rep.": "Dominican Republic",
}

# State/province aliases dictionary
STATE_ALIASES: dict[str, str] = {
    "Calif": "California",
    "Cali": "California",
    "CA": "California",
    "NY": "New York",
    "TX": "Texas",
    "FL": "Florida",
    "Mass": "Massachusetts",
    "MA": "Massachusetts",
    "Penn": "Pennsylvania",
    "PA": "Pennsylvania",
}

# City aliases dictionary
CITY_ALIASES: dict[str, str] = {
    "NYC": "New York City",
    "LA": "Los Angeles",
    "SF": "San Francisco",
    "DC": "Washington",
    "Philly": "Philadelphia",
}

# ISO3 codes dictionary (for 4x faster database queries)
ISO3_CODES: dict[str, str] = {
    "United States of America": "USA",
    "People's Republic of China": "CHN",
    "China": "CHN",
    "India": "IND",
    "Germany": "DEU",
    "United Kingdom": "GBR",
    "France": "FRA",
    "Japan": "JPN",
    "Canada": "CAN",
    "Australia": "AUS",
    "Brazil": "BRA",
    "Russian Federation": "RUS",
    "Russia": "RUS",
    "Republic of Korea": "KOR",
    "South Korea": "KOR",
    "Mexico": "MEX",
    "Indonesia": "IDN",
    "Saudi Arabia": "SAU",
    "Turkey": "TUR",
    "Italy": "ITA",
    "Spain": "ESP",
    "Netherlands": "NLD",
    "Poland": "POL",
    "South Africa": "ZAF",
    "Argentina": "ARG",
    "Thailand": "THA",
    "Egypt": "EGY",
    "Malaysia": "MYS",
    "Pakistan": "PAK",
    "Bangladesh": "BGD",
    "Viet Nam": "VNM",
    "Vietnam": "VNM",
    "Philippines": "PHL",
    "Nigeria": "NGA",
    "Iran": "IRN",
    "United Arab Emirates": "ARE",
    "UAE": "ARE",
    "Singapore": "SGP",
    "Switzerland": "CHE",
    "Belgium": "BEL",
    "Sweden": "SWE",
    "Norway": "NOR",
    "Denmark": "DNK",
    "Finland": "FIN",
    "Austria": "AUT",
    "Greece": "GRC",
    "Portugal": "PRT",
    "Czechia": "CZE",
    "Czech Republic": "CZE",
    "Romania": "ROU",
    "Hungary": "HUN",
    "Ireland": "IRL",
    "New Zealand": "NZL",
    "Chile": "CHL",
    "Colombia": "COL",
    "Peru": "PER",
    "Venezuela": "VEN",
    "Ukraine": "UKR",
    "Kazakhstan": "KAZ",
    "Algeria": "DZA",
    "Morocco": "MAR",
    "Kenya": "KEN",
    "Ethiopia": "ETH",
    "Ghana": "GHA",
    "Tanzania": "TZA",
    "United Republic of Tanzania": "TZA",
    "Uganda": "UGA",
    "Angola": "AGO",
    "Mozambique": "MOZ",
    "Madagascar": "MDG",
    "Cameroon": "CMR",
    "Côte d'Ivoire": "CIV",
    "Ivory Coast": "CIV",
    "Niger": "NER",
    "Burkina Faso": "BFA",
    "Mali": "MLI",
    "Malawi": "MWI",
    "Zambia": "ZMB",
    "Zimbabwe": "ZWE",
    "Senegal": "SEN",
    "Chad": "TCD",
    "Guinea": "GIN",
    "Rwanda": "RWA",
    "Benin": "BEN",
    "Burundi": "BDI",
    "Tunisia": "TUN",
    "South Sudan": "SSD",
    "Togo": "TGO",
    "Sierra Leone": "SLE",
    "Libya": "LBY",
    "Liberia": "LBR",
    "Central African Republic": "CAF",
    "Mauritania": "MRT",
    "Eritrea": "ERI",
    "Gambia": "GMB",
    "Botswana": "BWA",
    "Namibia": "NAM",
    "Gabon": "GAB",
    "Lesotho": "LSO",
    "Guinea-Bissau": "GNB",
    "Equatorial Guinea": "GNQ",
    "Mauritius": "MUS",
    "Eswatini": "SWZ",
    "Djibouti": "DJI",
    "Comoros": "COM",
    "Cape Verde": "CPV",
    "São Tomé and Príncipe": "STP",
    "Sao Tome and Principe": "STP",
    "Seychelles": "SYC",
}


def normalize_entity_name(entity_name: str, entity_type: str | None = None) -> str:
    """
    Normalize entity name using aliases and fuzzy matching.

    Args:
        entity_name: Raw entity name from user input
        entity_type: Optional type hint ('country', 'admin1', 'city')

    Returns:
        Normalized entity name
    """
    if not entity_name:
        return entity_name

    normalized = entity_name.strip()

    # Try exact match in country aliases (case-insensitive)
    for alias, canonical in COUNTRY_ALIASES.items():
        if normalized.lower() == alias.lower():
            return canonical

    # Try admin1 if level specified
    if entity_type == "admin1":
        for alias, canonical in STATE_ALIASES.items():
            if normalized.lower() == alias.lower():
                return canonical

    # Try city if level specified
    if entity_type == "city":
        for alias, canonical in CITY_ALIASES.items():
            if normalized.lower() == alias.lower():
                return canonical

    # If no level specified, try all
    if not entity_type:
        # Check admin1
        for alias, canonical in STATE_ALIASES.items():
            if normalized.lower() == alias.lower():
                return canonical
        # Check city
        for alias, canonical in CITY_ALIASES.items():
            if normalized.lower() == alias.lower():
                return canonical

    return normalized


def fuzzy_match_entity(
    entity_name: str,
    candidates: list[str],
    threshold: float = 0.8
) -> list[tuple[str, float]]:
    """
    Find best fuzzy matches from candidates.

    Args:
        entity_name: Entity to match
        candidates: List of valid entity names
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        List of (match, similarity_score) tuples, sorted by score descending
    """
    if not entity_name or not candidates:
        return []

    name_lower = entity_name.lower()
    matches: list[tuple[str, float]] = []

    for candidate in candidates:
        candidate_lower = candidate.lower()

        # Exact match
        if name_lower == candidate_lower:
            matches.append((candidate, 1.0))
            continue

        # Substring match
        if name_lower in candidate_lower or candidate_lower in name_lower:
            matches.append((candidate, 0.9))
            continue

        # Fuzzy similarity
        similarity = SequenceMatcher(None, name_lower, candidate_lower).ratio()
        if similarity >= threshold:
            matches.append((candidate, similarity))

    # Sort by similarity score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def get_iso3_code(country_name: str) -> str | None:
    """
    Get ISO3 code for country (for faster database queries).

    ISO3 codes are 4x faster than full country names in WHERE clauses.

    Args:
        country_name: Country name (will be normalized first)

    Returns:
        ISO3 code or None if not found
    """
    # Normalize country name first
    normalized = normalize_entity_name(country_name, entity_type="country")
    return ISO3_CODES.get(normalized)


def detect_geographic_level(entity_name: str, known_entities: dict[str, list[str]] | None = None) -> str:
    """
    Auto-detect whether entity is a country, state/province, or city.

    Args:
        entity_name: Entity name to classify
        known_entities: Optional dict with keys 'country', 'admin1', 'city' containing lists of known entities

    Returns:
        Geographic level classification: 'country', 'admin1', or 'city'
    """
    # Normalize first
    normalized = normalize_entity_name(entity_name)

    # If we have known entities, check against them
    if known_entities:
        if normalized in known_entities.get("city", []):
            return "city"
        if normalized in known_entities.get("admin1", []):
            return "admin1"
        if normalized in known_entities.get("country", []):
            return "country"

    # Fallback: check if entity has ISO3 code (countries have ISO3)
    if get_iso3_code(normalized):
        return "country"

    # Check if it's in state aliases
    if normalized in STATE_ALIASES.values():
        return "admin1"

    # Check if it's in city aliases
    if normalized in CITY_ALIASES.values():
        return "city"

    # Default to country
    return "country"

"""
prompt_parser.py

Lightweight NLP layer that:
- Extracts location (city / region / district / POI) from the user query
- Extracts high-level interest categories (food, shopping, nature, etc.)
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any, List

from app.database import POI_DATA

# -------------------------------------------------------------------
# Category keyword mapping (phrase → abstract category)
# These categories are mapped to actual POI category labels
# in recommender.CATEGORY_MAP
# -------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    # Food & drink
    "food": "food",
    "eat": "food",
    "dinner": "food",
    "lunch": "food",
    "breakfast": "food",
    "supper": "food",
    "restaurant": "food",
    "restaurants": "food",
    "hawker": "food",
    "local food": "food",
    "street food": "food",

    # Cafes / chill
    "cafe": "cafe",
    "cafes": "cafe",
    "coffee": "cafe",
    "brunch": "cafe",
    "tea": "cafe",

    # Shopping
    "shop": "shopping",
    "shopping": "shopping",
    "mall": "shopping",
    "malls": "shopping",
    "boutique": "shopping",
    "buy clothes": "shopping",

    # Nature / outdoors
    "park": "nature",
    "parks": "nature",
    "hike": "nature",
    "hiking": "nature",
    "nature": "nature",
    "garden": "nature",
    "gardens": "nature",
    "zoo": "nature",
    "river": "nature",
    "beach": "nature",

    # Culture & museums
    "museum": "culture",
    "museums": "culture",
    "gallery": "culture",
    "art": "culture",
    "temple": "culture",
    "heritage": "culture",
    "history": "culture",

    # Fun / activities
    "fun things": "activities",
    "things to do": "activities",
    "activities": "activities",
    "date ideas": "activities",
    "romantic": "activities",
    "axe throwing": "activities",
    "escape room": "activities",
    "arcade": "activities",
    "bowling": "activities",
    "indoor playground": "activities",

    # Nightlife
    "bar": "nightlife",
    "bars": "nightlife",
    "club": "nightlife",
    "clubs": "nightlife",
    "drinks": "nightlife",
    "cocktails": "nightlife",
}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


# -------------------------------------------------------------------
# Location extraction
# -------------------------------------------------------------------
def extract_location(query: str) -> Optional[Dict[str, Any]]:
    """
    Try to resolve a location from the query using POI_DATA:
    - If "Singapore" present → treat as city level
    - Else try POI name, district, region
    - Fallback: fuzzy match on district names (e.g. "Jurong")
    """
    q = _normalise(query)

    # 1) City-level: if user mentions Singapore but no more specific
    if "singapore" in q:
        return {
            "location_name": "Singapore",
            "location_level": "city",
        }

    matches: List[Dict[str, Any]] = []

    # 2) Direct matches using pre-computed lower-case columns
    for _, row in POI_DATA.iterrows():
        # POI name
        if isinstance(row.get("name_lower"), str) and row["name_lower"] in q:
            matches.append(
                {
                    "location_name": row["name"],
                    "location_level": "poi",
                    "lat": row.get("lat"),
                    "lon": row.get("lon"),
                    "district": row.get("district"),
                    "region": row.get("region"),
                }
            )

        # District
        if isinstance(row.get("district_lower"), str) and row["district_lower"] in q:
            matches.append(
                {
                    "location_name": row["district"],
                    "location_level": "district",
                    "region": row.get("region"),
                }
            )

        # Region
        if isinstance(row.get("region_lower"), str) and row["region_lower"] in q:
            matches.append(
                {
                    "location_name": row["region"],
                    "location_level": "region",
                }
            )

    if matches:
        # Prefer most specific: poi > district > region
        priority = {"poi": 3, "district": 2, "region": 1}
        matches.sort(key=lambda m: priority[m["location_level"]], reverse=True)
        return matches[0]

    # 3) Fuzzy fallback by district token (e.g. "jurong", "kallang")
    unique_districts = sorted(
        {str(d).lower() for d in POI_DATA["district"].dropna().unique()}
    )

    for district in unique_districts:
        # Match if district word appears in query or vice versa
        if district in q or q in district or any(
            tok and tok in district for tok in q.split()
        ):
            region = (
                POI_DATA.loc[
                    POI_DATA["district"].str.lower() == district, "region"
                ]
                .dropna()
                .unique()
            )
            region_name = region[0] if len(region) else None
            return {
                "location_name": district.upper(),
                "location_level": "district",
                "region": region_name,
            }

    # 4) Fuzzy fallback by region words (east, west, north, etc.)
    REGION_KEYWORDS = {
        "east": "EAST",
        "west": "WEST",
        "north": "NORTH",
        "south": "SOUTH",
        "central": "CENTRAL",
    }
    for key, region_name in REGION_KEYWORDS.items():
        if re.search(rf"\b{key}\b", q):
            return {
                "location_name": region_name,
                "location_level": "region",
            }

    return None


# -------------------------------------------------------------------
# Category extraction
# -------------------------------------------------------------------
def extract_categories(query: str) -> List[str]:
    q = _normalise(query)
    found = set()

    # 1) Phrase-based (multi-word first)
    for phrase, cat in CATEGORY_KEYWORDS.items():
        if phrase in q:
            found.add(cat)

    # 2) Super broad "fun things to do" type queries
    if "things to do" in q or "what to do" in q or "fun" in q:
        found.add("activities")

    return sorted(found)


def parse_query(query: str) -> Dict[str, Any]:
    """
    Main entry point used by multilevel.py
    """
    location = extract_location(query)
    categories = extract_categories(query)

    return {
        "raw_query": query,
        "location": location,
        "categories": categories,
    }

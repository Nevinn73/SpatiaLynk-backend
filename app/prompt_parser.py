# app/prompt_parser.py
import re
from app.database import POI_DATA


# ------------------------------------------------------------
# CATEGORY DETECTION
# ------------------------------------------------------------

CATEGORY_KEYWORDS = {
    # Food / eating
    "food": "food",
    "eat": "food",
    "eats": "food",
    "dine": "food",
    "dining": "food",
    "restaurant": "food",
    "restaurants": "food",
    "lunch": "food",
    "dinner": "food",
    "breakfast": "food",
    "supper": "food",
    "bbq": "food",

    # Cafes
    "cafe": "cafe",
    "cafes": "cafe",
    "coffee": "cafe",
    "brunch": "cafe",

    # Shopping / fashion
    "shop": "shopping",
    "shopping": "shopping",
    "mall": "shopping",
    "malls": "shopping",
    "clothes": "shopping",
    "fashion": "shopping",
    "boutique": "shopping",
    "retail": "shopping",

    # Fun / “things to do” / entertainment
    "fun": "fun",
    "activities": "fun",
    "activity": "fun",
    "entertainment": "fun",
    "attraction": "fun",
    "attractions": "fun",
    "play": "fun",
    "hang out": "fun",
    "hangout": "fun",

    # Outdoors / nature
    "park": "outdoors",
    "parks": "outdoors",
    "hiking": "outdoors",
    "trail": "outdoors",
    "nature": "outdoors",

    # Culture
    "museum": "culture",
    "museums": "culture",
    "gallery": "culture",
    "galleries": "culture",
    "art": "culture",
}


def extract_category(query: str):
    q = query.lower()
    found = set()

    # Multi-word phrases first
    if "things to do" in q or "what to do" in q or "where to go" in q:
        # Broad exploration – we treat it as fun, but we
        # will still allow restaurants, cafes etc. later
        found.add("fun")

    for phrase, category in CATEGORY_KEYWORDS.items():
        if phrase in q:
            found.add(category)

    if not found:
        return None

    return list(found)


# ------------------------------------------------------------
# LOCATION DETECTION
# ------------------------------------------------------------

def extract_location(query: str):
    q = query.lower()

    # SPECIAL: “Singapore” = city level
    if "singapore" in q or "sg " in q or q.strip() == "sg":
        return {
            "location_name": "Singapore",
            "location_level": "city"
        }

    # FUZZY DISTRICT FALLBACK (handles “Jurong”, “Hougang area”, etc.)
    for district_name in POI_DATA["district"].unique():
        base_token = district_name.split()[0].lower()  # e.g. "jurong" from "JURONG EAST"
        if base_token in q:
            region = POI_DATA[POI_DATA["district"] == district_name]["region"].iloc[0]
            return {
                "location_name": district_name,
                "location_level": "district",
                "region": region
            }

    matches = []

    for _, row in POI_DATA.iterrows():
        # POI name
        if row["name_lower"] in q:
            matches.append({
                "location_name": row["name"],
                "location_level": "poi",
                "lat": row["lat"],
                "lon": row["lon"],
                "district": row["district"],
                "region": row["region"]
            })

        # District
        if row["district_lower"] in q:
            matches.append({
                "location_name": row["district"],
                "location_level": "district",
                "region": row["region"]
            })

        # Region
        if row["region_lower"] in q:
            matches.append({
                "location_name": row["region"],
                "location_level": "region"
            })

    if not matches:
        return None

    priority = {"poi": 3, "district": 2, "region": 1}
    matches.sort(key=lambda x: priority[x["location_level"]], reverse=True)
    return matches[0]


# ------------------------------------------------------------
# MASTER PARSER
# ------------------------------------------------------------

def parse_query(query: str):
    return {
        "raw_query": query,
        "location": extract_location(query),
        "categories": extract_category(query),
    }

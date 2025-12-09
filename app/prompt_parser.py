import spacy
from app.database import POI_DATA

# Load NLP model safely
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print("Error loading spaCy model:", e)
    nlp = None


# Keyword → Category Map
CATEGORY_KEYWORDS = {
    # Shopping
    "shop": "shopping",
    "shopping": "shopping",
    "mall": "shopping",
    "malls": "shopping",
    "retail": "shopping",

    # Food
    "food": "food",
    "restaurant": "food",
    "restaurants": "food",
    "eat": "food",
    "hawker": "budget_food",
    "cheap food": "budget_food",
    "affordable food": "budget_food",

    # Cafes
    "cafe": "cafe",
    "cafes": "cafe",
    "coffee": "cafe",
    "brunch": "cafe",

    # Family
    "family": "family",
    "kids": "family",
    "child": "family",
    "child-friendly": "family",
    "family-friendly": "family",

    # Outdoors
    "park": "outdoors",
    "hiking": "outdoors",
    "nature": "outdoors",

    # Culture
    "museum": "culture",
    "museums": "culture",
    "gallery": "culture",
    "art": "culture",

    # Groceries
    "supermarket": "supermarket",
    "supermarkets": "supermarket",
    "grocery": "supermarket",
    "groceries": "supermarket"
}


def extract_location(query: str):
    q = query.lower()
    matches = []

    for _, row in POI_DATA.iterrows():

        if row["name_lower"] in q:
            matches.append({
                "location_name": row["name"],
                "location_level": "poi",
                "lat": row["lat"],
                "lon": row["lon"],
                "district": row["district"],
                "region": row["region"]
            })

        if row["district_lower"] in q:
            matches.append({
                "location_name": row["district"],
                "location_level": "district",
                "region": row["region"]
            })

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


def extract_category(query: str):
    q = query.lower()
    found = set()

    for phrase, cat in CATEGORY_KEYWORDS.items():
        if phrase in q:
            found.add(cat)

    if not found:
        return None

    return list(found)


def parse_query(query: str):
    location = extract_location(query)
    categories = extract_category(query)

    return {
        "raw_query": query,
        "location": location,
        "categories": categories
    }

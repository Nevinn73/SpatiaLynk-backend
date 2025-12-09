from app.database import POI_DATA
from app.prompt_parser import parse_query

# Map user intent → POI categories in the CSV
CATEGORY_MAP = {
    "shopping": ["shopping_mall"],
    "food": ["food", "restaurant", "hawker"],
    "budget_food": ["hawker"],
    "cafe": ["cafe"],
    "family": ["family_activity"],   # adjust if CSV uses different labels
    "outdoors": ["park"],
    "culture": ["museum", "gallery"],
    "supermarket": ["supermarket"]
}


def recommend_places(query: str, top_k: int = 5):
    parsed = parse_query(query)

    location = parsed["location"]
    categories = parsed["categories"]

    if not location:
        return {"error": "Could not detect location."}

    if not categories:
        return {"error": "Could not detect category or intent."}

    district = location["location_name"]
    location_level = location["location_level"]

    # Step 1: Filter by location district
    df = POI_DATA.copy()

    if location_level == "district":
        df = df[df["district"].str.lower() == district.lower()]
    elif location_level == "region":
        df = df[df["region"].str.lower() == district.lower()]
    # If POI level → just return the POI itself
    elif location_level == "poi":
        return {"results": [location]}

    # Step 2: Filter by category mapping
    allowed_categories = []
    for cat in categories:
        allowed_categories.extend(CATEGORY_MAP.get(cat, []))

    df = df[df["category"].isin(allowed_categories)]

    # Step 3: Rank by popularity (simple baseline)
    df = df.sort_values(by="popularity", ascending=False)

    # Step 4: Return results
    results = df.head(top_k).to_dict(orient="records")

    return {
    "parsed": {
        "raw_query": query,
        "location": parsed["location"],
        "categories": categories
    },
    "results": results
}


from app.database import POI_DATA
from app.prompt_parser import parse_query
from app.recommender import CATEGORY_MAP
from app.explain import explain_level, explain_categories, explain_poi


# ---------------------------------------------------------
# Helpers for grouping POIs
# ---------------------------------------------------------

def group_by_region(df):
    """Return a dict of region → list of POIs"""
    grouped = {}
    for region in sorted(df["region"].unique()):
        sub = df[df["region"] == region]
        grouped[region] = sub.to_dict(orient="records")
    return grouped


def group_by_district(df):
    """Return a dict of district → list of POIs"""
    grouped = {}
    for district in sorted(df["district"].unique()):
        sub = df[df["district"] == district]
        grouped[district] = sub.to_dict(orient="records")
    return grouped


# ---------------------------------------------------------
# Main multi-level recommender
# ---------------------------------------------------------

def multilevel_recommend(query: str, top_k: int = 5):
    """
    Multi-level recommendation engine:
    - Detects location level (city, region, district, POI)
    - Detects categories (shopping, food, cafes…)
    - Performs fallback if insufficient POIs
    - Produces explanations for FYP requirements
    """

    parsed = parse_query(query)
    location = parsed["location"]
    categories = parsed["categories"] or []

    # ------------------------------------------------------------------
    # Step 1 — Filter POIs by category (or explore mode)
    # ------------------------------------------------------------------

    if categories:
        allowed_categories = []
        for c in categories:
            allowed_categories.extend(CATEGORY_MAP.get(c, []))

        df = POI_DATA[POI_DATA["category"].isin(allowed_categories)].copy()
    else:
        df = POI_DATA.copy()  # exploration mode → use all POIs

    # Sort by popularity
    if "popularity" in df.columns:
        df = df.sort_values(by="popularity", ascending=False)

    # ------------------------------------------------------------------
    # CASE A: No location detected → city-level recommendations
    # ------------------------------------------------------------------

    if not location:
        region_groups = group_by_region(df)

        return {
            "level": "city",
            "city": "Singapore",
            "regions": region_groups,
            "explanation": {
                "level_reason": explain_level(parsed, None, "city"),
                "category_reason": explain_categories(categories)
            },
            "poi_explanations": {
                region: [explain_poi(p, None, categories) for p in region_groups[region]]
                for region in region_groups
            },
            "parsed": parsed
        }

    # ------------------------------------------------------------------
    # CASE B: Region-level prompt
    # ------------------------------------------------------------------

    if location["location_level"] == "region":
        loc_name = location["location_name"].lower()
        region_df = df[df["region"].str.lower() == loc_name]

        district_groups = group_by_district(region_df)

        return {
            "level": "region",
            "region": location["location_name"],
            "districts": district_groups,
            "explanation": {
                "level_reason": explain_level(parsed, location, "region"),
                "category_reason": explain_categories(categories)
            },
            "poi_explanations": {
                district: [explain_poi(p, location, categories) for p in district_groups[district]]
                for district in district_groups
            },
            "parsed": parsed
        }

    # ------------------------------------------------------------------
    # CASE C: District-level prompt
    # ------------------------------------------------------------------

    if location["location_level"] == "district":
        loc_name = location["location_name"].lower()
        district_df = df[df["district"].str.lower() == loc_name]

        # Fallback: too few POIs → expand to region
        if len(district_df) < top_k:
            region_name = location["region"]
            region_df = df[df["region"] == region_name]

            return {
                "level": "district_fallback",
                "district": location["location_name"],
                "region": region_name,
                "results": region_df.head(top_k).to_dict(orient="records"),
                "explanation": {
                    "level_reason": explain_level(parsed, location, "district_fallback"),
                    "category_reason": explain_categories(categories)
                },
                "poi_explanations": [
                    explain_poi(p, location, categories)
                    for p in region_df.head(top_k).to_dict(orient="records")
                ],
                "parsed": parsed
            }

        # Main district output
        results = district_df.head(top_k).to_dict(orient="records")

        return {
            "level": "district",
            "district": location["location_name"],
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "district"),
                "category_reason": explain_categories(categories)
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed
        }

    # ------------------------------------------------------------------
    # CASE D: POI-level prompt → return nearby POIs in same district
    # ------------------------------------------------------------------

    if location["location_level"] == "poi":
        district_name = location["district"]
        district_df = df[df["district"].str.lower() == district_name.lower()]

        results = district_df.head(top_k).to_dict(orient="records")

        return {
            "level": "poi",
            "poi": location["location_name"],
            "nearby": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "poi"),
                "category_reason": explain_categories(categories)
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed
        }

    # ------------------------------------------------------------------
    # Fallback — should not occur but included for safety
    # ------------------------------------------------------------------

    return {
        "error": "Unable to determine recommendation level.",
        "parsed": parsed
    }

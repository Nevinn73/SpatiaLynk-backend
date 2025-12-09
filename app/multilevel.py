from app.database import POI_DATA
from app.prompt_parser import parse_query
from app.recommender import CATEGORY_MAP
from app.explain import explain_level, explain_categories, explain_poi
import numpy as np


# ---------------------------------------------------------
# Weighted Sampling Helper
# ---------------------------------------------------------

def weighted_sample(df, top_k=5):
    """
    Select top_k POIs using weighted random sampling.
    - Higher popularity = higher chance
    - Still introduces diversity
    """
    if len(df) <= top_k:
        return df.to_dict(orient="records")

    # Convert popularity into probability weights
    weights = df["popularity"].astype(float).values
    weights = weights / weights.sum()

    sampled_idx = np.random.choice(
        df.index,
        size=top_k,
        replace=False,
        p=weights
    )
    return df.loc[sampled_idx].to_dict(orient="records")


# ---------------------------------------------------------
# Grouping Helpers
# ---------------------------------------------------------

def group_by_region(df, top_k=5):
    """Return region → weighted-sampled POIs"""
    grouped = {}
    for region in sorted(df["region"].unique()):
        sub = df[df["region"] == region]
        grouped[region] = weighted_sample(sub, top_k)
    return grouped


def group_by_district(df, top_k=5):
    """Return district → weighted-sampled POIs"""
    grouped = {}
    for district in sorted(df["district"].unique()):
        sub = df[df["district"] == district]
        grouped[district] = weighted_sample(sub, top_k)
    return grouped


# ---------------------------------------------------------
# MAIN Multi-Level Recommender
# ---------------------------------------------------------

def multilevel_recommend(query: str, top_k: int = 5):
    """
    Multi-level recommendation engine:
    - Detects location level (city, region, district, POI)
    - Detects categories
    - Performs fallback if insufficient POIs
    - Produces explainability strings (FYP requirement)
    """

    parsed = parse_query(query)
    location = parsed["location"]
    categories = parsed["categories"] or []

    # -----------------------------------------------------
    # Step 1 — Filter POIs by category
    # -----------------------------------------------------

    if categories:
        allowed_categories = []
        for c in categories:
            allowed_categories.extend(CATEGORY_MAP.get(c, []))
        df = POI_DATA[POI_DATA["category"].isin(allowed_categories)].copy()
    else:
        df = POI_DATA.copy()  # exploration mode

    # Sort by popularity (before sampling)
    if "popularity" in df.columns:
        df = df.sort_values(by="popularity", ascending=False)

    # -----------------------------------------------------
    # CASE A: No location detected → CITY LEVEL
    # -----------------------------------------------------

    if not location:
        region_groups = group_by_region(df, top_k)

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

    # -----------------------------------------------------
    # CASE B: REGION LEVEL
    # -----------------------------------------------------

    if location["location_level"] == "region":
        loc_name = location["location_name"].lower()
        region_df = df[df["region"].str.lower() == loc_name]

        district_groups = group_by_district(region_df, top_k)

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

    # -----------------------------------------------------
    # CASE C: DISTRICT LEVEL
    # -----------------------------------------------------

    if location["location_level"] == "district":
        loc_name = location["location_name"].lower()
        district_df = df[df["district"].str.lower() == loc_name]

        # Fallback: if insufficient POIs → expand to region
        if len(district_df) < top_k:
            region_name = location["region"]
            region_df = df[df["region"] == region_name]
            fallback_results = weighted_sample(region_df, top_k)

            return {
                "level": "district_fallback",
                "district": location["location_name"],
                "region": region_name,
                "results": fallback_results,
                "explanation": {
                    "level_reason": explain_level(parsed, location, "district_fallback"),
                    "category_reason": explain_categories(categories)
                },
                "poi_explanations": [
                    explain_poi(p, location, categories) for p in fallback_results
                ],
                "parsed": parsed
            }

        # Main District Output (Weighted)
        results = weighted_sample(district_df, top_k)

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

    # -----------------------------------------------------
    # CASE D: POI LEVEL → Nearby POIs
    # -----------------------------------------------------

    if location["location_level"] == "poi":
        district_name = location["district"]
        district_df = df[df["district"].str.lower() == district_name.lower()]

        results = weighted_sample(district_df, top_k)

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

    # -----------------------------------------------------
    # FALLBACK (Should Not Occur)
    # -----------------------------------------------------

    return {
        "error": "Unable to determine recommendation level.",
        "parsed": parsed
    }

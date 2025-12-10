"""
multilevel.py

Implements the multi-level + explainable recommender:

Levels:
- city      → "Things to do in Singapore"
- region    → "Things to do in the west"
- district  → "What to do in Kallang"
- poi       → "I want to visit Hougang Mall"

All responses expose a unified `results` list for easy UI integration.
"""

from __future__ import annotations

from typing import Dict, Any

from app.database import POI_DATA
from app.prompt_parser import parse_query
from app.recommender import CATEGORY_MAP, BORING_CATEGORIES, filter_exploration_df, diversified_sample
from app.explain import explain_level, explain_categories, explain_poi


def multilevel_recommend(query: str, top_k: int = 5) -> Dict[str, Any]:
    parsed = parse_query(query)
    location = parsed["location"]
    categories = parsed["categories"] or []

    df = POI_DATA.copy()

    # --------------------------------------------------------------
    # Step 1 – Category filtering
    # --------------------------------------------------------------
    if categories:
        # Map abstract categories → actual labels
        allowed = []
        for c in categories:
            allowed.extend(CATEGORY_MAP.get(c, []))

        if allowed:
            df = df[df["category"].isin(allowed)]
    else:
        # Broad exploration: remove boring categories only
        df = filter_exploration_df(df)

    # Sort by popularity for more stable results
    if "popularity" in df.columns:
        df = df.sort_values("popularity", ascending=False)

    # Early exit: no data
    if df.empty:
        return {
            "level": "none",
            "results": [],
            "explanation": {
                "level_reason": "Could not find any places matching your request.",
                "category_reason": explain_categories(categories),
            },
            "parsed": parsed,
        }

    # --------------------------------------------------------------
    # CASE A – No specific location or explicit 'city'
    # --------------------------------------------------------------
    if not location or location.get("location_level") == "city":
        # Truly city-wide selection (already filtered above)
        results = diversified_sample(df, top_k=top_k)

        return {
            "level": "city",
            "city": "Singapore",
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "city"),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed,
        }

    # --------------------------------------------------------------
    # CASE B – Region-level prompt
    # --------------------------------------------------------------
    if location["location_level"] == "region":
        loc_name = location["location_name"].lower()
        region_df = df[df["region"].str.lower() == loc_name]

        if region_df.empty:
            # Fallback to whole city
            results = diversified_sample(df, top_k=top_k)
        else:
            results = diversified_sample(region_df, top_k=top_k)

        return {
            "level": "region",
            "region": location["location_name"],
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "region"),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed,
        }

    # --------------------------------------------------------------
    # CASE C – District-level prompt
    # --------------------------------------------------------------
    if location["location_level"] == "district":
        loc_name = location["location_name"].lower()
        district_df = df[df["district"].str.lower() == loc_name]

        if district_df.empty:
            # Fallback: region if known, else city
            region_name = location.get("region")
            if region_name:
                region_df = df[df["region"] == region_name]
                results = diversified_sample(region_df, top_k=top_k)
                level = "district_fallback_region"
            else:
                results = diversified_sample(df, top_k=top_k)
                level = "district_fallback_city"
        else:
            results = diversified_sample(district_df, top_k=top_k)
            level = "district"

        return {
            "level": level,
            "district": location["location_name"],
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, level),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed,
        }

    # --------------------------------------------------------------
    # CASE D – POI-level prompt (e.g. "Hougang Mall")
    # --------------------------------------------------------------
    if location["location_level"] == "poi":
        district_name = (location.get("district") or "").lower()
        district_df = df[df["district"].str.lower() == district_name]

        if district_df.empty:
            results = diversified_sample(df, top_k=top_k)
        else:
            results = diversified_sample(district_df, top_k=top_k)

        return {
            "level": "poi",
            "poi": location["location_name"],
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "poi"),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [
                explain_poi(p, location, categories) for p in results
            ],
            "parsed": parsed,
        }

    # --------------------------------------------------------------
    # Fallback (should rarely happen)
    # --------------------------------------------------------------
    results = diversified_sample(df, top_k=top_k)

    return {
        "level": "unknown",
        "results": results,
        "explanation": {
            "level_reason": "Location could not be determined, so we showed general results.",
            "category_reason": explain_categories(categories),
        },
        "poi_explanations": [
            explain_poi(p, location, categories) for p in results
        ],
        "parsed": parsed,
    }



# app/multilevel.py
from app.database import POI_DATA
from app.prompt_parser import parse_query
from app.recommender import weighted_sample, apply_intent_filter
from app.explain import explain_level, explain_categories, explain_poi

import pandas as pd


# ------------------ grouping helpers ------------------

def group_by_region(df: pd.DataFrame, top_k_per_region: int = 6):
    out = {}
    for region in sorted(df["region"].unique()):
        sub = df[df["region"] == region]
        out[region] = weighted_sample(sub, top_k_per_region)
    return out


def group_by_district(df: pd.DataFrame, top_k_per_district: int = 6):
    out = {}
    for d in sorted(df["district"].unique()):
        sub = df[df["district"] == d]
        out[d] = weighted_sample(sub, top_k_per_district)
    return out


# ------------------ main engine ------------------

def multilevel_recommend(query: str, top_k: int = 5):
    parsed = parse_query(query)
    location = parsed["location"]
    categories = parsed["categories"] or []

    df = POI_DATA.copy()
    df = apply_intent_filter(df, categories)

    if len(df) == 0:
        # as an absolute fallback, use everything except boring categories
        df = apply_intent_filter(POI_DATA.copy(), None)

    # sort by popularity first
    if "popularity" in df.columns:
        df = df.sort_values(by="popularity", ascending=False)

    # --------------- CASE 0: city level / no location ---------------

    if not location or location.get("location_level") == "city":
        # If user gave an intent (food, fun, shopping) → simple city results
        if categories:
            results = weighted_sample(df, top_k)
            return {
                "level": "city_intent",
                "city": "Singapore",
                "results": results,
                "explanation": {
                    "level_reason": explain_level(parsed, None, "city_intent"),
                    "category_reason": explain_categories(categories),
                },
                "poi_explanations": [explain_poi(p, None, categories) for p in results],
                "parsed": parsed,
            }
        else:
            # No intent → show regions with a few highlights
            regions = group_by_region(df)
            return {
                "level": "city",
                "city": "Singapore",
                "regions": regions,
                "explanation": {
                    "level_reason": explain_level(parsed, None, "city"),
                    "category_reason": explain_categories(categories),
                },
                "parsed": parsed,
            }

    # --------------- CASE 1: REGION ---------------

    if location["location_level"] == "region":
        r_name = location["location_name"].lower()
        df_r = df[df["region"].str.lower() == r_name]

        if len(df_r) == 0:
            results = weighted_sample(df, top_k)
        else:
            results = weighted_sample(df_r, top_k)

        districts = group_by_district(df_r) if len(df_r) else {}

        return {
            "level": "region",
            "region": location["location_name"],
            "results": results,
            "districts": districts,
            "explanation": {
                "level_reason": explain_level(parsed, location, "region"),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [explain_poi(p, location, categories) for p in results],
            "parsed": parsed,
        }

    # --------------- CASE 2: DISTRICT ---------------

    if location["location_level"] == "district":
        d_name = location["location_name"].lower()
        df_d = df[df["district"].str.lower() == d_name]

        if len(df_d) == 0:
            # fallback to region if district too sparse
            region_name = location.get("region")
            if region_name:
                df_region = df[df["region"].str.lower() == region_name.lower()]
            else:
                df_region = df
            results = weighted_sample(df_region, top_k)
            level_used = "district_fallback"
        else:
            results = weighted_sample(df_d, top_k)
            level_used = "district"

        return {
            "level": level_used,
            "district": location["location_name"],
            "results": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, level_used),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [explain_poi(p, location, categories) for p in results],
            "parsed": parsed,
        }

    # --------------- CASE 3: POI (nearby stuff) ---------------

    if location["location_level"] == "poi":
        d_name = location["district"].lower()
        df_d = df[df["district"].str.lower() == d_name]

        results = weighted_sample(df_d, top_k)

        return {
            "level": "poi",
            "poi": location["location_name"],
            "nearby": results,
            "explanation": {
                "level_reason": explain_level(parsed, location, "poi"),
                "category_reason": explain_categories(categories),
            },
            "poi_explanations": [explain_poi(p, location, categories) for p in results],
            "parsed": parsed,
        }

    # --------------- fallback ---------------

    return {
        "error": "Unable to determine recommendation level.",
        "parsed": parsed,
    }


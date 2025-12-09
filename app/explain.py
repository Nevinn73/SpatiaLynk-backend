def explain_level(parsed, location, level):
    """
    Explain why the system chose this spatial level.
    """
    if not location:
        return "No specific location detected — showing recommendations across Singapore."

    if level == "region":
        return f"Your query referenced the region '{location['location_name']}'."

    if level == "district":
        return f"Your query referenced the district '{location['location_name']}'."

    if level == "district_fallback":
        return (
            f"Too few POIs found in district '{location['location_name']}', "
            f"so results were expanded to the region '{location['region']}'."
        )

    if level == "poi":
        return (
            f"You mentioned a specific POI ('{location['location_name']}'), "
            f"so showing nearby places in the same district."
        )

    if level == "city":
        return "Showing recommendations across Singapore."

    return "General recommendations."


def explain_categories(categories):
    """
    Explain why these POI categories were selected.
    """
    if not categories:
        return "No specific intent detected — showing popular or relevant places."
    
    formatted = ", ".join(categories)
    return f"These places match your interests: {formatted}."


def explain_poi(poi, location, categories):
    """
    Explain why this specific POI was recommended.
    """
    reasons = []

    # Category matching
    if categories:
        reasons.append(f"Matches your interest category '{poi['category']}'.")
    else:
        reasons.append("Recommended due to high popularity.")

    # Location relevance
    if location:
        if poi["district"].lower() == location["location_name"].lower():
            reasons.append(f"Located in the requested district '{poi['district']}'.")
        elif poi["region"].lower() == location.get("region", '').lower():
            reasons.append(f"Located in the requested region '{poi['region']}'.")

    explanation = " ".join(reasons)
    return explanation



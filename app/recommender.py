# app/recommender.py
import numpy as np
import pandas as pd

from app.database import POI_DATA


# High-level categories → concrete POI categories in your CSV
CATEGORY_MAP = {
    "food": ["restaurant", "hawker", "food"],
    "cafe": ["cafe"],
    "shopping": ["shopping_mall", "mall", "shopping"],
    "fun": ["attraction", "theme_park", "playground", "arcade", "bowling", "cinema",
            "restaurant", "cafe"],  # fun can include food
    "outdoors": ["park", "garden", "nature"],
    "culture": ["museum", "gallery", "temple", "heritage"],
}

# Categories we almost never want to show for fun / broad searches
BORING_CATEGORIES = {
    "atm",
    "bank",
    "supermarket",
    "convenience_store",
    "clinic",
    "medical",
    "pharmacy",
    "office",
}


def weighted_sample(data, top_k: int = 5):
    """
    Safe sampler:
    - Accepts DataFrame OR list of dict
    - Returns list[dict]
    """
    if isinstance(data, list):
        if len(data) == 0:
            return []
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    if len(df) == 0:
        return []

    if "popularity" not in df.columns:
        return df.head(top_k).to_dict(orient="records")

    if len(df) <= top_k:
        return df.to_dict(orient="records")

    weights = df["popularity"].astype(float).values
    weights = weights / weights.sum()

    idx = np.random.choice(df.index, size=top_k, replace=False, p=weights)
    return df.loc[idx].to_dict(orient="records")


def apply_intent_filter(df: pd.DataFrame, categories: list | None) -> pd.DataFrame:
    """
    - If categories is None → broad exploration:
        - Drop boring categories, keep everything else (including restaurants).
    - If categories include high-level labels (food, shopping, etc.):
        - Keep POIs whose categories map to those, AND still drop boring ones.
    """
    df = df.copy()

    # Always remove boring stuff unless explicitly desired in future
    df = df[~df["category"].str.lower().isin(BORING_CATEGORIES)]

    if not categories:
        return df

    allowed = set()
    for cat in categories:
        allowed.update(CATEGORY_MAP.get(cat, []))

    if not allowed:
        return df

    df = df[df["category"].isin(list(allowed))]
    return df

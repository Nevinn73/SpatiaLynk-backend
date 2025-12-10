"""
recommender.py

Category mapping + helper functions for sampling & filtering.
"""

from __future__ import annotations

from typing import List, Dict, Any

import numpy as np
import pandas as pd

from app.database import POI_DATA

# -------------------------------------------------------------------
# Map abstract categories → actual POI category labels
# -------------------------------------------------------------------
CATEGORY_MAP: Dict[str, List[str]] = {
    # Food & drink
    "food": ["restaurant", "hawker", "eatery", "bistro"],
    "cafe": ["cafe", "coffee", "dessert_cafe", "tea_house"],

    # Shopping
    "shopping": ["shopping_mall", "market", "boutique"],

    # Nature / outdoors
    "nature": ["park", "garden", "nature_reserve", "zoo", "beach"],

    # Culture & heritage
    "culture": ["museum", "gallery", "temple", "heritage"],

    # Fun / activities
    "activities": [
        "activity_center",
        "sports_center",
        "arcade",
        "escape_room",
        "axe_throwing",
        "indoor_playground",
        "theme_park",
        "attraction",
    ],

    # Nightlife
    "nightlife": ["bar", "club", "lounge"],
}

# Categories that we *never* want to recommend for this app
BORING_CATEGORIES = {
    "supermarket",
    "grocery",
    "atm",
    "convenience",
    "clinic",
    "bank",
    "office",
    "service",
    "pharmacy",
}


def filter_exploration_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Used when the user gives a broad query (no specific category):
    - Start from all POIs
    - Remove 'boring' categories
    """
    if "category" not in df.columns:
        return df
    return df[~df["category"].isin(BORING_CATEGORIES)].copy()


def diversified_sample(df: pd.DataFrame, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Weighted random sampling while encouraging variety by category.

    - If df has <= top_k rows → return all
    - Otherwise:
        * Prefer unique categories first
        * Use 'popularity' as weight if present
    """
    if df.empty:
        return []

    if len(df) <= top_k:
        return df.to_dict(orient="records")

    df = df.copy()

    # Ensure popularity column exists and is numeric
    if "popularity" not in df.columns:
        df["popularity"] = 1.0

    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce").fillna(1.0)

    results: List[Dict[str, Any]] = []
    used_categories = set()

    for _ in range(top_k):
        remaining = df[~df["category"].isin(used_categories)]
        if remaining.empty:
            remaining = df

        weights = remaining["popularity"].astype(float).values
        weights = weights / weights.sum()

        idx = np.random.choice(remaining.index, p=weights)
        row = remaining.loc[idx]
        results.append(row.to_dict())
        used_categories.add(row["category"])

    return results

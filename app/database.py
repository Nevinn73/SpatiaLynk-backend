import pandas as pd

def load_poi_data():
    try:
        df = pd.read_csv("data/POI_with_region.csv")

        # Normalize text columns for matching
        df["name_lower"] = df["name"].astype(str).str.lower()
        df["district_lower"] = df["district"].astype(str).str.lower()
        df["region_lower"] = df["region"].astype(str).str.lower()

        return df

    except Exception as e:
        print("ERROR loading POI CSV:", e)
        return None

# Must exist for the import to work
POI_DATA = load_poi_data()

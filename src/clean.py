import pandas as pd
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Load all team CSVs and combine them
all_files = [f for f in os.listdir("data/raw/") if f.endswith(".csv") and f != "teams.csv"]
all_dfs = [pd.read_csv(f"data/raw/{f}") for f in all_files]
df = pd.concat(all_dfs, ignore_index=True)

print(f"Total players: {len(df)}")

# Setup geocoder
geolocator = Nominatim(user_agent="world-cup-analysis")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def get_country(city):
    """Geocodes a city and returns the country."""
    if pd.isna(city) or city == "":
        return ""
    try:
        location = geocode(city, language="en")
        if location:
            return location.address.split(",")[-1].strip()
        return ""
    except:
        return ""

# Get unique cities to avoid geocoding the same city twice
unique_cities = df["place_of_birth"].dropna().unique()
unique_cities = [c for c in unique_cities if c != ""]
print(f"Unique cities to geocode: {len(unique_cities)}")

# Geocode all unique cities
city_to_country = {}
for i, city in enumerate(unique_cities):
    country = get_country(city)
    city_to_country[city] = country
    print(f"  ({i+1}/{len(unique_cities)}) {city} → {country}")

# Map countries back to players
df["birth_country"] = df["place_of_birth"].map(city_to_country)

# Identify naturalized players
df["is_naturalized"] = df["birth_country"] != df["national_team"]

# Save processed data
df.to_csv("data/processed/all_players.csv", index=False)
print(f"\nDone! Saved to data/processed/all_players.csv")
print(f"Naturalized players: {df['is_naturalized'].sum()}")

# Show sample of naturalized players to check quality
naturalized = df[df["is_naturalized"] == True][["name", "national_team", "place_of_birth", "birth_country"]].head(30)
print(naturalized.to_string())
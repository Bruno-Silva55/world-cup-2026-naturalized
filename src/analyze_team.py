import pandas as pd

# Load the processed file
df = pd.read_csv("data/processed/all_players.csv")

# Filter team
TEAM = "Bosnia and Herzegovina"
team_df = df[df["national_team"] == TEAM].copy()

# Manual corrections
corrections = {
    "Wels": "Austria"
}
team_df["birth_country"] = team_df.apply(
    lambda row: corrections.get(row["place_of_birth"], row["birth_country"]),
    axis=1
)
team_df["is_naturalized"] = team_df["birth_country"] != TEAM

# Show all players with birth info
print(f"\n{TEAM} — Full squad ({len(team_df)} players)")
print("="*70)
print(team_df[["name", "place_of_birth", "birth_country", "is_naturalized"]].to_string(index=False))

# Summary
total = len(team_df)
naturalized = team_df["is_naturalized"].sum()
print(f"\nTotal: {total} players")
print(f"Naturalized: {naturalized} ({round(naturalized/total*100)}%)")
print(f"Native: {total - naturalized} ({round((total - naturalized)/total*100)}%)")
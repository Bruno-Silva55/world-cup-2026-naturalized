import requests
import pandas as pd
import time
import os
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

base_url = "https://www.transfermarkt.com"

# Load the list of teams
teams = pd.read_csv("data/raw/teams.csv")

for _, team in teams.iterrows():
    team_name = team["name"]
    team_id = team["id"]
    
    # Skip if already processed
    output_file = f"data/raw/{team_name.lower().replace(' ', '_')}.csv"
    if os.path.exists(output_file):
        print(f"Skipping {team_name} — already done")
        continue
    
    print(f"\nFetching {team_name}...")
    
    # Fetch the squad page
    url = f"https://www.transfermarkt.com/x/kader/verein/{team_id}/plus/0/galerie/0?saison_id=2026"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    rows = soup.find_all("tr", {"class": ["odd", "even"]})
    
    players = []
    
    for row in rows:
        # Find the link to the player profile
        name_tag = row.find("a", href=lambda x: x and "/profil/spieler/" in x)
        if not name_tag:
            continue
        
        name = name_tag.text.strip()
        link = name_tag["href"]
        
        try:
            # Fetch the player profile page
            profile = requests.get(base_url + link, headers=headers)
            soup_profile = BeautifulSoup(profile.content, "html.parser")
            
            # Extract labels and values from the personal info table
            labels = soup_profile.find_all("span", {"class": "info-table__content--regular"})
            values = soup_profile.find_all("span", {"class": "info-table__content--bold"})
            
            place_of_birth = ""
            citizenship = ""
            
            # Match labels to values and extract what we need
            for label, value in zip(labels, values):
                if "Place of birth" in label.text:
                    place_of_birth = value.text.strip()
                if "Citizenship" in label.text:
                    citizenship = value.text.strip()
            
            players.append({
                "name": name,
                "place_of_birth": place_of_birth,
                "citizenship": citizenship,
                "national_team": team_name
            })
            
            print(f"  ✓ {name} — {place_of_birth} — {citizenship}")
            time.sleep(1)
        
        except Exception as e:
            print(f"  ✗ Error fetching {name}: {e}")
            continue
    
    # Save this team to its own CSV
    if players:
        df = pd.DataFrame(players)
        df.to_csv(output_file, index=False)
        print(f"  Saved {len(players)} players to {output_file}")
    
    time.sleep(2)

# Combine all CSVs into one
print("\nCombining all files...")
all_files = [f for f in os.listdir("data/raw/") if f.endswith(".csv") and f != "teams.csv"]
all_dfs = [pd.read_csv(f"data/raw/{f}") for f in all_files]
df_final = pd.concat(all_dfs, ignore_index=True)
df_final.to_csv("data/processed/all_players.csv", index=False)
print(f"Done! {len(df_final)} players saved to data/processed/all_players.csv")
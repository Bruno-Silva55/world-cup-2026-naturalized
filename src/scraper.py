import requests
import pandas as pd
import time
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# base_url = "https://www.transfermarkt.com"
# url = "https://www.transfermarkt.com/portugal/kader/verein/3300/plus/0/galerie/0?saison_id=2026"

# # Fetch the squad page
# response = requests.get(url, headers=headers)
# soup = BeautifulSoup(response.content, "html.parser")
# rows = soup.find_all("tr", {"class": ["odd", "even"]})

# players = []

# for row in rows:
#     # Find the link to the player profile
#     name_tag = row.find("a", href=lambda x: x and "/profil/spieler/" in x)
#     if not name_tag:
#         continue
    
#     name = name_tag.text.strip()
#     link = name_tag["href"]
    
#     # Fetch the player profile page
#     profile = requests.get(base_url + link, headers=headers)
#     soup_profile = BeautifulSoup(profile.content, "html.parser")
    
#     # Extract labels and values from the personal info table
#     labels = soup_profile.find_all("span", {"class": "info-table__content--regular"})
#     values = soup_profile.find_all("span", {"class": "info-table__content--bold"})
    
#     place_of_birth = ""
#     citizenship = ""
    
#     # Match labels to values and extract what we need
#     for label, value in zip(labels, values):
#         if "Place of birth" in label.text:
#             place_of_birth = value.text.strip()
#         if "Citizenship" in label.text:
#             citizenship = value.text.strip()
    
#     players.append({
#         "name": name,
#         "place_of_birth": place_of_birth,
#         "citizenship": citizenship,
#         "national_team": "Portugal"
#     })
    
#     print(f"✓ {name} — {place_of_birth} — {citizenship}")
#     time.sleep(1)  # wait 1 second between requests to avoid overloading the server

# # Save results to CSV
# df = pd.DataFrame(players)
# df.to_csv("data/raw/portugal.csv", index=False)
# print("\nFile saved to data/raw/portugal.csv")

# Fetch the list of World Cup teams
wc_url = "https://www.transfermarkt.com/weltmeisterschaft/teilnehmer/pokalwettbewerb/FIWC/saison_id/2025"
wc_response = requests.get(wc_url, headers=headers)
wc_soup = BeautifulSoup(wc_response.content, "html.parser")

# Find all links on the page
links = wc_soup.find_all("a")
for link in links[:20]:
    print(link.text.strip(), "—", link.get("href", ""))
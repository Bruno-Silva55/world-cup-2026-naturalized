import pandas as pd
import json

# Load reference metadata
metadata = pd.read_csv("data/raw/country_metadata.csv")
metadata["atlas_id"] = metadata["atlas_id"].astype(str).str.zfill(3)

# Build lookup dictionaries from metadata
country_flags = dict(zip(metadata["name"], metadata["flag_code"]))
country_coords = dict(zip(metadata["name"], zip(metadata["lon"], metadata["lat"])))
country_coords = {k: list(v) for k, v in country_coords.items()}
european = metadata[metadata["continent"] == "Europe"]["name"].tolist()

flags_json = json.dumps(country_flags)
coords_json = json.dumps(country_coords)
european_json = json.dumps(european)

# Load player data
df = pd.read_csv("data/processed/all_players.csv")

# Load groups data
groups_df = pd.read_csv("data/raw/groups.csv")

# Config — change this to generate a different team
TEAM = "Bosnia and Herzegovina"

team_df = df[df["national_team"] == TEAM].copy()

# Manual corrections per team
corrections = {
    "Bosnia and Herzegovina": {"Wels": "Austria"}
}
team_corrections = corrections.get(TEAM, {})
team_df["birth_country"] = team_df.apply(
    lambda row: team_corrections.get(row["place_of_birth"], row["birth_country"]),
    axis=1
)
team_df["is_naturalized"] = team_df["birth_country"] != TEAM

# Get naturalized players
naturalized = team_df[team_df["is_naturalized"] == True].copy()
total = len(team_df)
nat_count = len(naturalized)
nat_pct = round(nat_count / total * 100)

# Get native players
natives = team_df[team_df["is_naturalized"] == False].copy()
native_names = natives["name"].tolist()
native_json = json.dumps(native_names)

# Group players by birth country
grouped = naturalized.groupby("birth_country")["name"].apply(list).to_dict()

# Warn if any birth country is missing from metadata
for country in grouped.keys():
    if country not in country_coords:
        print(f"WARNING: '{country}' not found in country_metadata.csv — add it!")

# Convert to JSON for JavaScript, sorted by number of players descending
players_json = json.dumps(sorted([
    {"country": country, "players": players}
    for country, players in grouped.items()
], key=lambda x: len(x["players"]), reverse=True))

# Team metadata
team_meta = metadata[metadata["name"] == TEAM].iloc[0]
team_center = [float(team_meta["lon"]), float(team_meta["lat"])]
team_flag = team_meta["flag_code"]
team_atlas_id = team_meta["atlas_id"]
flag_url = f"https://flagcdn.com/32x24/{team_flag}.png"

# Group info
team_group = groups_df[groups_df["team"] == TEAM]["group"].iloc[0]
group_opponents = groups_df[
    (groups_df["group"] == team_group) & (groups_df["team"] != TEAM)
]["team"].tolist()
opponent_flags = [country_flags.get(t, "") for t in group_opponents]
opponents_json = json.dumps([
    {"team": team, "flag": flag}
    for team, flag in zip(group_opponents, opponent_flags)
])

print(f"{TEAM}: {nat_count}/{total} naturalized ({nat_pct}%)")
print(f"Group {team_group}: {group_opponents}")

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{TEAM} — World Cup 2026</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0a0f1e; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
  #container {{ width: 1200px; height: 675px; position: relative; overflow: hidden; }}
  #map-svg {{ width: 100%; height: 100%; }}
  #header {{ position: absolute; top: 24px; left: 24px; display: flex; align-items: center; gap: 12px; }}
  #flag {{ border-radius: 3px; }}
  #title {{ color: #ffffff; font-size: 22px; font-weight: 600; }}
  #subtitle {{ color: #8899bb; font-size: 14px; margin-top: 4px; }}
  #stats {{ position: absolute; top: 24px; right: 24px; text-align: right; }}
  #big-number {{ color: #FFCC00; font-size: 42px; font-weight: 700; line-height: 1; }}
  #big-number span {{ color: #8899bb; font-size: 20px; font-weight: 400; }}
  #big-label {{ color: #8899bb; font-size: 13px; margin-top: 4px; }}
  #cards {{ position: absolute; top: 110px; right: 24px; display: flex; flex-direction: column; gap: 6px; width: 320px; }}
  .card {{ background: rgba(255,255,255,0.07); border: 0.5px solid rgba(255,255,255,0.15); border-radius: 6px; padding: 5px 10px; font-size: 11px; color: #fff; opacity: 0; transition: opacity 0.6s; }}
  .card .player-names {{ color: #aabbcc; }}
  #group {{ position: absolute; bottom: 24px; right: 24px; display: flex; align-items: center; gap: 8px; }}
  #group-label {{ color: #8899bb; font-size: 11px; margin-right: 4px; }}
  .opponent-flag {{ border-radius: 2px; opacity: 0.85; }}
  #footer {{ position: absolute; bottom: 6px; left: 24px; color: #445566; font-size: 10px; }}
</style>
</head>
<body>
<div id="container">
  <svg id="map-svg" viewBox="0 0 1200 675"></svg>
  <div id="header">
    <img id="flag" src="{flag_url}" width="48" height="36">
    <div>
      <div id="title">{TEAM}</div>
      <div id="subtitle">World Cup 2026 — players born abroad</div>
    </div>
  </div>
  <div id="stats">
    <div id="big-number">{nat_count}<span>/{total}</span></div>
    <div id="big-label">{nat_pct}% born outside {TEAM}</div>
  </div>
  <div id="cards"></div>
  <div id="group">
    <span id="group-label">Group {team_group}</span>
  </div>
  <div id="footer">Data: Transfermarkt · github.com/Bruno-Silva55</div>
</div>

<script>
const teamData = {players_json};
const countryCoords = {coords_json};
const europeanCountries = {european_json};
const countryFlags = {flags_json};
const teamCenter = {json.dumps(team_center)};
const teamAtlasId = "{team_atlas_id}";
const teamName = "{TEAM}";
const teamFlagCode = "{team_flag}";
const nativePlayers = {native_json};
const opponents = {opponents_json};
const width = 1200, height = 675;

const svg = d3.select("#map-svg");
const projection = d3.geoMercator()
  .center([teamCenter[0]-40, teamCenter[1]])
  .scale(400)
  .translate([width / 2 - 100, height / 2 + 40]);

const path = d3.geoPath().projection(projection);

d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(world => {{
  const countries = topojson.feature(world, world.objects.countries);

  svg.append("rect").attr("width", width).attr("height", height).attr("fill", "#0a0f1e");

  const defs = svg.append("defs");
  const pattern = defs.append("pattern")
    .attr("id", "flag-pattern")
    .attr("patternUnits", "objectBoundingBox")
    .attr("width", 1).attr("height", 1);
  pattern.append("image")
    .attr("href", `https://flagcdn.com/${{teamFlagCode}}.png`)
    .attr("width", 300).attr("height", 200)
    .attr("preserveAspectRatio", "xMidYMid slice");

  const birthCountryAtlasIds = {json.dumps([
      metadata[metadata["name"] == c]["atlas_id"].iloc[0]
      if len(metadata[metadata["name"] == c]) > 0 else ""
      for c in grouped.keys()
  ])};

  svg.selectAll("path.land")
    .data(countries.features)
    .join("path")
    .attr("d", path)
    .attr("fill", d => {{
      if (d.id === teamAtlasId) return "url(#flag-pattern)";
      if (birthCountryAtlasIds.includes(d.id)) return "#1a3a6b";
      return "#111827";
    }})
    .attr("stroke", d => d.id === teamAtlasId ? "#ffffff" : "#1e2d50")
    .attr("stroke-width", d => d.id === teamAtlasId ? 1 : 0.4);

  const linesG = svg.append("g");
  const dotsG = svg.append("g");
  const teamXY = projection(teamCenter);

  teamData.forEach((item, i) => {{
    const coords = countryCoords[item.country];
    if (!coords) return;

    const color = "#4a9eff";
    const xy = projection(coords);

    setTimeout(() => {{
      const line = linesG.append("line")
        .attr("x1", xy[0]).attr("y1", xy[1])
        .attr("x2", xy[0]).attr("y2", xy[1])
        .attr("stroke", color)
        .attr("stroke-width", 0.8 + item.players.length * 0.8)
        .attr("stroke-opacity", 0.75);

      line.transition().duration(700)
        .attr("x2", teamXY[0])
        .attr("y2", teamXY[1]);

      setTimeout(() => {{
        dotsG.append("circle")
          .attr("cx", xy[0]).attr("cy", xy[1])
          .attr("r", 0)
          .attr("fill", color)
          .attr("stroke", "#0a0f1e")
          .attr("stroke-width", 1.5)
          .transition().duration(300);

        const card = document.createElement("div");
        card.className = "card";
        const flagCode = countryFlags[item.country] || "";
        const flagImg = flagCode ? `<img src="https://flagcdn.com/20x15/${{flagCode}}.png" style="vertical-align:middle; margin-right:6px; border-radius:2px;">` : "";
        card.innerHTML = `${{flagImg}}<span style="color:${{color}}; font-weight:600;">${{item.country}} (${{item.players.length}})</span> <span class="player-names">· ${{item.players.join(", ")}}</span>`;
        document.getElementById("cards").appendChild(card);
        setTimeout(() => card.style.opacity = "1", 50);
      }}, 700);

    }}, i * 700);
  }});

  // Native players card — appears last
  setTimeout(() => {{
    const card = document.createElement("div");
    card.className = "card";
    const flagImg = `<img src="https://flagcdn.com/20x15/${{teamFlagCode}}.png" style="vertical-align:middle; margin-right:6px; border-radius:2px;">`;
    card.innerHTML = `${{flagImg}}<span style="color:#FFCC00; font-weight:600;">Born in {TEAM} (${{nativePlayers.length}})</span> <span class="player-names">· ${{nativePlayers.join(", ")}}</span>`;
    card.style.borderColor = "rgba(255, 204, 0, 0.3)";
    document.getElementById("cards").appendChild(card);
    setTimeout(() => card.style.opacity = "1", 50);
  }}, {len(grouped)} * 700 + 1000);

  // Group opponents flags
  const groupDiv = document.getElementById("group");
  opponents.forEach(opp => {{
    if (opp.flag) {{
      const img = document.createElement("img");
      img.src = `https://flagcdn.com/32x24/${{opp.flag}}.png`;
      img.title = opp.team;
      img.className = "opponent-flag";
      img.width = 32;
      img.height = 24;
      groupDiv.appendChild(img);
    }}
  }});

  svg.append("circle")
    .attr("cx", teamXY[0]).attr("cy", teamXY[1])
    .attr("r", 8)
    .attr("fill", "#FFCC00")
    .attr("stroke", "#0a0f1e")
    .attr("stroke-width", 2);
}});
</script>
</body>
</html>"""

output_path = f"outputs/{TEAM.lower().replace(' ', '_').replace('/', '_')}_viz.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nHTML saved to {output_path}")
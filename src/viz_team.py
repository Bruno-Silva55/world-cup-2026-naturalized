import pandas as pd
import json

# ============================================================
# LOAD REFERENCE DATA
# ============================================================

# Load country metadata (flag codes, atlas IDs, coordinates, continents)
metadata = pd.read_csv("data/raw/country_metadata.csv")
# Pad atlas_id with leading zeros to match world-atlas format (e.g. "70" → "070")
metadata["atlas_id"] = metadata["atlas_id"].astype(str).str.zfill(3)

# Build lookup dictionaries from metadata
country_flags = dict(zip(metadata["name"], metadata["flag_code"]))
country_coords = dict(zip(metadata["name"], zip(metadata["lon"], metadata["lat"])))
country_coords = {k: list(v) for k, v in country_coords.items()}
european = metadata[metadata["continent"] == "Europe"]["name"].tolist()

# Convert to JSON strings for embedding in JavaScript
flags_json = json.dumps(country_flags)
coords_json = json.dumps(country_coords)
european_json = json.dumps(european)

# Load player data (output from clean.py)
df = pd.read_csv("data/processed/all_players.csv")

# Load World Cup group stage data
groups_df = pd.read_csv("data/raw/groups.csv")

# ============================================================
# CONFIG — CHANGE THIS LINE TO SWITCH TEAMS
# ============================================================
TEAM = "Bosnia and Herzegovina"

# ============================================================
# FILTER AND PROCESS TEAM DATA
# ============================================================

team_df = df[df["national_team"] == TEAM].copy()

# Manual corrections for geocoding errors, organized by team
# Add new corrections here as: "Team Name": {"City": "Correct Country"}
corrections = {
    "Bosnia and Herzegovina": {"Wels": "Austria"},
    "Portugal": {"Benavente": "Portugal"}
}
team_corrections = corrections.get(TEAM, {})

# Apply corrections to birth_country column
team_df["birth_country"] = team_df.apply(
    lambda row: team_corrections.get(row["place_of_birth"], row["birth_country"]),
    axis=1
)

# Mark players as naturalized if born outside the country they represent
team_df["is_naturalized"] = team_df["birth_country"] != TEAM

# ============================================================
# SPLIT INTO NATURALIZED vs NATIVE
# ============================================================

naturalized = team_df[team_df["is_naturalized"] == True].copy()
total = len(team_df)
nat_count = len(naturalized)
nat_pct = round(nat_count / total * 100)

natives = team_df[team_df["is_naturalized"] == False].copy()
native_names = natives["name"].tolist()
native_json = json.dumps(native_names)

# Group naturalized players by their birth country
grouped = naturalized.groupby("birth_country")["name"].apply(list).to_dict()

# Warn if a birth country is missing from country_metadata.csv
for country in grouped.keys():
    if country not in country_coords:
        print(f"WARNING: '{country}' not found in country_metadata.csv — add it!")

# Convert grouped players to JSON, sorted by number of players (most first)
players_json = json.dumps(sorted([
    {"country": country, "players": players}
    for country, players in grouped.items()
], key=lambda x: len(x["players"]), reverse=True))

# ============================================================
# TEAM METADATA
# ============================================================

team_meta = metadata[metadata["name"] == TEAM].iloc[0]
team_center = [float(team_meta["lon"]), float(team_meta["lat"])]
team_flag = team_meta["flag_code"]
team_atlas_id = team_meta["atlas_id"]
flag_url = f"https://flagcdn.com/32x24/{team_flag}.png"

# ============================================================
# GROUP STAGE INFO
# ============================================================

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

# ============================================================
# BUILD ATLAS IDs FOR BIRTH COUNTRIES (used to highlight map)
# ============================================================

birth_country_atlas_ids = [
    metadata[metadata["name"] == c]["atlas_id"].iloc[0]
    if len(metadata[metadata["name"] == c]) > 0 else ""
    for c in grouped.keys()
]

# ============================================================
# GENERATE HTML
# ============================================================

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

  /* Main container — fixed at 1200x675 (16:9) for screen recording */
  #container {{ width: 1200px; height: 675px; position: relative; overflow: hidden; }}
  #map-svg {{ width: 100%; height: 100%; }}

  /* Top left — flag + title + subtitle + group opponents */
  #header {{ position: absolute; top: 24px; left: 24px; display: flex; align-items: flex-start; gap: 12px; background: rgba(0,0,0,0.5); border-radius: 8px; padding: 10px 14px; backdrop-filter: blur(4px); }}
  #flag {{ border-radius: 3px; margin-top: 3px; }}
  #title {{ color: #ffffff; font-size: 22px; font-weight: 600; }}
  #subtitle {{ color: #8899bb; font-size: 13px; margin-top: 3px; }}
  #group-inline {{ display: flex; align-items: center; gap: 6px; margin-top: 6px; }}
  #group-label {{ color: #8899bb; font-size: 11px; }}
  .opponent-flag {{ border-radius: 2px; opacity: 0.9; }}

  /* Top right — big number stat */
  #stats {{ position: absolute; top: 24px; right: 24px; text-align: right; background: rgba(0,0,0,0.5); border-radius: 8px; padding: 10px 14px; backdrop-filter: blur(4px); }}
  #big-number {{ color: #FFCC00; font-size: 42px; font-weight: 700; line-height: 1; }}
  #big-number span {{ color: #8899bb; font-size: 20px; font-weight: 400; }}
  #big-label {{ color: #8899bb; font-size: 13px; margin-top: 4px; }}

  /* Right side — animated player cards */
  /* To move cards: adjust top/right values */
  #cards {{ position: absolute; top: 120px; right: 24px; display: flex; flex-direction: column; gap: 6px; width: 320px; }}
  .card {{ background: rgba(0,0,0,0.6); border: 0.5px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 5px 10px; font-size: 11px; color: #fff; opacity: 0; transition: opacity 0.6s; backdrop-filter: blur(4px); }}
  .card .player-names {{ color: #ccd6e0; }}

  /* Bottom left — social handles + data source */
  #footer {{ position: absolute; bottom: 16px; left: 24px; display: flex; align-items: center; gap: 16px; background: rgba(255,255,255,0.9); border-radius: 6px; padding: 6px 12px; }}
  #footer a {{ color: #111827; font-size: 11px; display: flex; align-items: center; gap: 5px; text-decoration: none; font-weight: 500; }}
  #footer img {{ opacity: 1; filter: brightness(0); }}
  #footer .source {{ color: #444444; font-size: 11px; }}
</style>
</head>
<body>
<div id="container">
  <svg id="map-svg" viewBox="0 0 1200 675"></svg>

  <!-- Top left: flag + team name + subtitle + group opponents -->
  <div id="header">
    <img id="flag" src="{flag_url}" width="48" height="36">
    <div>
      <div id="title">{TEAM}</div>
      <div id="subtitle">World Cup 2026 — players born abroad</div>
      <div id="group-inline">
        <span id="group-label">Group {team_group} ·</span>
      </div>
    </div>
  </div>

  <!-- Top right: main stat -->
  <div id="stats">
    <div id="big-number">{nat_count}<span>/{total}</span></div>
    <div id="big-label">{nat_pct}% born outside {TEAM}</div>
  </div>

  <!-- Player cards injected here by JavaScript -->
  <div id="cards"></div>

  <!-- Bottom left: social + data credit -->
  <div id="footer">
    <a href="#">
      <img src="https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/x.svg" width="12" height="12">
      @bruno_silva55
    </a>
    <a href="#">
      <img src="https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/github.svg" width="12" height="12">
      Bruno-Silva55
    </a>
    <span class="source">· Data: Transfermarkt</span>
  </div>
</div>

<script>
// ── Data injected by Python ──────────────────────────────────
const teamData = {players_json};           // naturalized players grouped by birth country
const countryCoords = {coords_json};       // lon/lat for every country
const countryFlags = {flags_json};         // country name → flag code
const teamCenter = {json.dumps(team_center)};
const teamAtlasId = "{team_atlas_id}";     // world-atlas ID for the team's country
const teamFlagCode = "{team_flag}";        // flag code for the team
const nativePlayers = {native_json};       // players born in the team's country
const opponents = {opponents_json};        // group stage opponents
const birthCountryAtlasIds = {json.dumps(birth_country_atlas_ids)};

const width = 1200, height = 675;

// ── Map setup ────────────────────────────────────────────────
const svg = d3.select("#map-svg");

// Collect all coordinates that need to be visible
const allCoords = [teamCenter, ...Object.keys(countryCoords)
  .filter(c => teamData.map(d => d.country).includes(c))
  .map(c => countryCoords[c])];

// Calculate bounding box with padding
const lons = allCoords.map(c => c[0]);
const lats = allCoords.map(c => c[1]);
const minLon = Math.min(...lons) - 5;
const maxLon = Math.max(...lons) + 5;
const minLat = Math.min(...lats) - 5;
const maxLat = Math.max(...lats) + 5;

// fitExtent automatically centers and zooms to fit all countries
// [[left, top], [right, bottom]] — leaves space for cards on the right
const projection = d3.geoMercator()
  .fitExtent(
    [[80, 60], [width - 350, height - 60]],
    {{ type: "FeatureCollection", features: [
      {{ type: "Feature", geometry: {{ type: "MultiPoint", coordinates: [
        [minLon, minLat], [maxLon, maxLat],
        [minLon, maxLat], [maxLon, minLat]
      ]}}}}
    ]}}
  );

const path = d3.geoPath().projection(projection);

// ── Draw map ─────────────────────────────────────────────────
d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(world => {{
  const countries = topojson.feature(world, world.objects.countries);

  // Dark background
  svg.append("rect").attr("width", width).attr("height", height).attr("fill", "#0a0f1e");

  // Flag pattern for team country fill
  const defs = svg.append("defs");
  const pattern = defs.append("pattern")
    .attr("id", "flag-pattern")
    .attr("patternUnits", "objectBoundingBox")
    .attr("width", 1).attr("height", 1);
  pattern.append("image")
    .attr("href", `https://flagcdn.com/${{teamFlagCode}}.png`)
    .attr("width", 300).attr("height", 200)
    .attr("preserveAspectRatio", "xMidYMid slice");

  // Draw countries:
  // - Team country → flag pattern fill
  // - Birth countries → highlighted blue
  // - Everything else → dark grey
  svg.selectAll("path.land")
    .data(countries.features)
    .join("path")
    .attr("d", path)
    .attr("fill", d => {{
      if (d.id === teamAtlasId) return "#FFCC00";
      if (birthCountryAtlasIds.includes(d.id)) return "#1a3a6b";
      return "#000000";
    }})
    .attr("stroke", d => d.id === teamAtlasId ? "#ffffff" : "#ffffff")
    .attr("stroke-width", d => d.id === teamAtlasId ? 1 : 0.4);

  const linesG = svg.append("g");
  const teamXY = projection(teamCenter);

  // ── Animate lines and cards ───────────────────────────────
  // Each country animates with 700ms stagger
  // To change speed: adjust (i * 700) and duration(700)
  teamData.forEach((item, i) => {{
    const coords = countryCoords[item.country];
    if (!coords) return;

    const color = "#4a9eff";
    const xy = projection(coords);

    setTimeout(() => {{
      // Animated line from birth country to team country
      const line = linesG.append("line")
        .attr("x1", xy[0]).attr("y1", xy[1])
        .attr("x2", xy[0]).attr("y2", xy[1])
        .attr("stroke", color)
        .attr("stroke-width", 1.5)
        .attr("stroke-opacity", 0.75);

      line.transition().duration(700)
        .attr("x2", teamXY[0])
        .attr("y2", teamXY[1]);

      // Player card appears after line finishes
      setTimeout(() => {{
        const card = document.createElement("div");
        card.className = "card";
        const flagCode = countryFlags[item.country] || "";
        const flagImg = flagCode
          ? `<img src="https://flagcdn.com/20x15/${{flagCode}}.png" style="vertical-align:middle; margin-right:6px; border-radius:2px;">`
          : "";
        card.innerHTML = `${{flagImg}}<span style="color:${{color}}; font-weight:600;">${{item.country}} (${{item.players.length}})</span> <span class="player-names">· ${{item.players.join(", ")}}</span>`;
        document.getElementById("cards").appendChild(card);
        setTimeout(() => card.style.opacity = "1", 50);
      }}, 700);

    }}, i * 700);
  }});

  // ── Native players card ───────────────────────────────────
  // Appears last, highlighted in yellow
  setTimeout(() => {{
    const card = document.createElement("div");
    card.className = "card";
    const flagImg = `<img src="https://flagcdn.com/20x15/${{teamFlagCode}}.png" style="vertical-align:middle; margin-right:6px; border-radius:2px;">`;
    card.innerHTML = `${{flagImg}}<span style="color:#FFCC00; font-weight:600;">Born in {TEAM} (${{nativePlayers.length}})</span> <span class="player-names">· ${{nativePlayers.join(", ")}}</span>`;
    card.style.borderColor = "rgba(255, 204, 0, 0.3)";
    document.getElementById("cards").appendChild(card);
    setTimeout(() => card.style.opacity = "1", 50);
  }}, {len(grouped)} * 700 + 1000);

  // ── Group opponents flags in header ──────────────────────
  const groupInline = document.getElementById("group-inline");
  opponents.forEach(opp => {{
    if (opp.flag) {{
      const img = document.createElement("img");
      img.src = `https://flagcdn.com/24x18/${{opp.flag}}.png`;
      img.title = opp.team;
      img.className = "opponent-flag";
      img.width = 24;
      img.height = 18;
      groupInline.appendChild(img);
    }}
  }});

}});
</script>
</body>
</html>"""

# ============================================================
# SAVE HTML FILE
# ============================================================

output_path = f"outputs/{TEAM.lower().replace(' ', '_').replace('/', '_')}_viz.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nHTML saved to {output_path}")
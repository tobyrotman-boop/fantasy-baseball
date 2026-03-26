# Diamond Nights Fantasy Baseball — Developer Handoff Document

## What This Project Is
A fantasy baseball league website for a private 12-team ESPN league called Diamond Nights. The project has two parts:

1. **A Python backend pipeline** that authenticates with ESPN's unofficial API, pulls weekly fantasy baseball stats, calculates custom rotisserie (roto) standings and a luck metric, and outputs everything as JSON files to GitHub.

2. **A frontend website** built in Lovable.dev that reads those JSON files and displays standings, luck reports, weekly history, owner profiles, historical records, keepers, and league rules.

The owner (Toby Rotman, team "This is a new low.....") is a product manager with no prior coding experience who built this from scratch. Keep explanations clear.

---

## Current Status (as of late March 2026)
- **Season just started** — first games played but ESPN API not yet returning stats for week 1
- **Most likely cause:** ESPN hasn't processed game data to the API layer yet. This is expected behavior — ESPN's real-time stats page pulls from a different data layer than the API. The API typically reflects data after overnight processing.
- **Action required:** Check `league_data.json` the morning after games are played. If week 1 shows non-zero stats, everything is working. If still zero, debug using the box score inspection method below.
- **Empty week handling:** The script currently loops through all 19 weeks. Empty weeks produce zero stats. The `roto_history` empty guard prevents crashes. A smarter empty-week check needs to be added back once we confirm data is flowing (see Known Issues).
- **OBP/SLG and SV+HLD keys:** These are new 2026 categories. We have not yet verified the exact ESPN API stat keys for these. Must verify after week 1 data appears.

---

## Key Credentials & IDs
- **ESPN League ID:** 4080
- **SWID:** `{27E33A0F-8C90-11D3-8208-00A0C9E58E2D}` (stable, rarely changes)
- **ESPN_S2:** Expires periodically — re-grab from browser when auth fails (see instructions below)
- **GitHub repo:** `github.com/tobyrotman-boop/fantasy-baseball`
- **GitHub username:** `tobyrotman-boop`

---

## Data URLs (what the frontend reads)
- **Current season:** `https://raw.githubusercontent.com/tobyrotman-boop/fantasy-baseball/main/league_data.json`
- **Historical:** `https://raw.githubusercontent.com/tobyrotman-boop/fantasy-baseball/main/historical.json`

Note: GitHub's CDN caches raw files for ~5-10 minutes. Changes won't appear instantly after a push.

---

## League Configuration
- **Platform:** ESPN (private league)
- **Format:** H2H Categories (weekly head-to-head matchups, each category is a win/loss)
- **Teams:** 12
- **Regular season:** 19 weeks
- **Playoffs:** 6 teams qualify, top 2 seeds get a bye in round 1
- **Keepers:** 5 per team, submitted annually before the draft
- **Draft format:** Auction

### 2026 Scoring Categories
**Hitting (6):** HR, RBI, SB, R, OBP, SLG
**Pitching (6):** QS, W, K, SV+HLD, ERA, WHIP
**Lower is better:** ERA, WHIP (these are ranked in reverse — lowest ERA gets 12 points)

### Category history
- OBP and SLG replaced AVG and OPS starting in 2026
- SV+HLD (saves + holds combined) replaced SV at some point
- League went from 10 to 12 categories at some point before 2019

### Excluded owners (left the league, should not appear in historical data)
- Bradd Caplan
- Josh Lessner

---

## Repository File Structure
```
fantasy-baseball/
├── roto.py                    # Main script — pulls current season ESPN data
├── historical.py              # Historical script — builds owner profiles across years
├── test_historical.py         # One-off test script — ignore, safe to delete
├── league_data.json           # Current season output — auto-updated daily by GitHub Actions
├── historical.json            # Historical owner data — auto-updated daily by GitHub Actions
├── diamond_nights_handoff.md  # This document
└── .github/
    └── workflows/
        └── weekly_update.yml  # GitHub Actions automation config
```

---

## roto.py — Detailed Explanation

### What it does
1. Authenticates with ESPN using `espn_s2` and `SWID` cookies
2. Connects to league 4080 for the current year (2026)
3. Loops through all 19 regular season weeks
4. For each week pulls box scores (each box score = one matchup between two teams)
5. Extracts raw counting stats for each team
6. Accumulates stats across weeks for season totals
7. Calculates ratio stats (OBP, SLG, ERA, WHIP) from underlying counting stats — never sums ratios directly as that's mathematically wrong
8. Ranks all 12 teams 1-12 in each category with half-point tie splitting
9. Tracks actual weekly matchup results (category wins/losses)
10. Simulates every team vs every other team each week (universal matchups) for luck calculation
11. Outputs `league_data.json`

### Ratio calculations
```python
# OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
# SLG = (1B + 2*2B + 3*3B + 4*HR) / AB
# ERA = (ER * 9) / (OUTS / 3)
# WHIP = (P_H + P_BB) / (OUTS / 3)
```

### Ranking logic
- All categories: rank 12 = best = 12 points, rank 1 = worst = 1 point
- ERA and WHIP: lowest value gets rank 12 (most points)
- Ties: points are averaged between tied teams (e.g. two teams tied for 3rd/4th each get 3.5 points)

### Luck metric
- **Universal win%:** For each week, simulate every team vs every other team (11 opponents × 12 categories = 132 possible category wins). Accumulate across all weeks.
- **Actual win%:** Real category wins in actual scheduled matchups. Accumulate across all weeks.
- **Luck = Actual% - Universal%**
- Positive = lucky (scheduled easy opponents), Negative = unlucky (scheduled tough opponents)

### Key variables
```python
YEAR = 2026           # Update each season
LEAGUE_ID = 4080      # Never changes
HITTING_CATS = ['HR', 'RBI', 'SB', 'R', 'OBP', 'SLG']
PITCHING_CATS = ['QS', 'W', 'K', 'SV', 'ERA', 'WHIP']  # NOTE: SV key may need updating for SV+HLD
LOWER_IS_BETTER = {'ERA', 'WHIP'}
```

### Credentials handling
```python
# In GitHub Actions — reads from GitHub Secrets (ESPN_S2 and SWID)
# Locally — set environment variables before running:
#   export ESPN_S2="your_cookie_here"
#   export SWID="{your_swid_here}"
# If you get auth errors locally, run: unset ESPN_S2
ESPN_S2 = os.environ.get("ESPN_S2")
SWID = os.environ.get("SWID")
```

### Empty week handling (KNOWN ISSUE — needs improvement)
Currently the script loops all 19 weeks. Empty weeks (not yet played) return zero stats. There is a guard that prevents crashing when no data exists:
```python
if not roto_history:
    print("No data yet - season hasn't started")
    exit(0)
```
A previous attempt to skip empty weeks using an HR check (`total_hr == 0`) and then a Runs check (`total_r == 0`) both incorrectly triggered during week 1 when data existed. This needs a better solution — perhaps checking multiple stats or using a threshold rather than zero.

---

## historical.py — Detailed Explanation

### What it does
1. Loops through years 2019-2026 (skips 2020 — COVID year, handled differently)
2. Note: ESPN API does not reliably return box scores before 2019
3. For each year tracks championships (final_standing == 1)
4. Pulls all regular season weeks and accumulates stats per owner
5. Tracks owners by real name (firstName + lastName from ESPN owner object)
6. Records best single week and best single season per category
7. Filters out excluded owners (Bradd Caplan, Josh Lessner)
8. Outputs `historical.json`

### Owner tracking
ESPN exposes owner data as:
```python
{'firstName': 'Jason', 'lastName': 'Smulson', 'id': '{7265779A-...}'}
```
The script uses `firstName + lastName` as the owner key. The owner ID is stable across years even when team names change, but we use real name for display.

### Known issues to fix
1. **Year range:** Currently `range(2019, 2026)` — needs to be `range(2019, 2027)` to include 2026
2. **OBP/SLG missing:** Script only tracks `HR, RBI, SB, R, K, W, QS, SV, ERA, WHIP`. Need to add OBP and SLG plus underlying stats: H, AB, B_BB, HBP, SF, 2B, 3B
3. **SV+HLD:** Script tracks `SV` — may need updating once ESPN key is confirmed

---

## league_data.json Structure
```json
{
  "generated_at": "2026-03-25",
  "roto_standings": [
    {
      "team": "Team Name",
      "hitting_pts": 62.5,
      "pitching_pts": 58.5,
      "total_pts": 121.0
    }
  ],
  "luck_table": [
    {
      "team": "Team Name",
      "actual_wins": 139,
      "actual_losses": 75,
      "actual_pct": 0.650,
      "universal_wins": 1417,
      "universal_losses": 950,
      "universal_pct": 0.599,
      "luck": 0.051
    }
  ],
  "weekly_roto": [
    {
      "week": 1,
      "standings": [
        {
          "team": "Team Name",
          "hitting_pts": 51.5,
          "pitching_pts": 62.5,
          "total_pts": 114.0
        }
      ]
    }
  ]
}
```

---

## historical.json Structure
```json
{
  "generated_at": "2026-03-25",
  "owners": [
    {
      "name": "Jason Smulson",
      "championships": 0,
      "seasons": [
        {
          "year": 2019,
          "stats": {
            "HR": 312.0,
            "RBI": 875.0,
            "ERA": 4.554,
            "WHIP": 1.381
          }
        }
      ],
      "weekly_records": {
        "HR": {
          "value": 27.0,
          "year": 2019,
          "week": 19,
          "team": "Barry McCockiner"
        }
      },
      "season_records": {
        "HR": {
          "value": 312.0,
          "year": 2019
        }
      }
    }
  ]
}
```

---

## GitHub Actions Automation
**File:** `.github/workflows/weekly_update.yml`
**Schedule:** Runs daily at 7am Pacific (cron: `0 14 * * *`)
**Also:** Can be triggered manually from GitHub Actions tab → Run workflow

### What the workflow does
1. Checks out the repo
2. Sets up Python 3.11
3. Installs `espn-api` library
4. Runs `python3 roto.py` with ESPN credentials from GitHub Secrets
5. Runs `python3 historical.py` with ESPN credentials from GitHub Secrets
6. Commits and pushes updated `league_data.json` and `historical.json`

### GitHub Secrets (repo Settings → Secrets and variables → Actions)
- `ESPN_S2` — ESPN session cookie, update when auth fails
- `SWID` — ESPN user ID, stable

### Known warning (non-breaking)
GitHub Actions shows a Node.js 20 deprecation warning. Not breaking. Actions versions need updating before June 2026:
- `actions/checkout@v3` → `@v4`
- `actions/setup-python@v4` → `@v5`

---

## How to Grab Fresh ESPN Cookies
ESPN cookies expire periodically. When you see `ESPNAccessDenied` errors:
1. Open Chrome, go to `fantasy.espn.com`, make sure you're logged in
2. Press **Command + Option + I** to open dev tools
3. Click **Application** tab
4. Click **Cookies** → `fantasy.espn.com`
5. Find `espn_s2` (long string) and `SWID` (looks like `{XXXXXXXX-...}`)
6. Copy both values
7. Go to GitHub repo → Settings → Secrets and variables → Actions
8. Update `ESPN_S2` and `SWID` secrets with new values
9. **Do not paste cookies into chat or commit them to code**

---

## How to Debug Box Score Stats
When you need to see exactly what ESPN is returning (e.g. to find the key for SV+HLD or OBP):

Add this temporarily to roto.py right after `boxes = league.box_scores(week)`:
```python
if week == 1:
    print(boxes[0].home_stats)
    print(boxes[0].away_stats)
    break
```
Run locally, check output, remove the debug lines before committing.

---

## Terminal Commands

### Setup (every time you open a new Terminal window)
```bash
cd fantasy-baseball
source venv/bin/activate     # you'll see (venv) in your prompt when active
```

### Running scripts
```bash
python3 roto.py
python3 historical.py
```

### Opening files in VS Code
```bash
code roto.py
code historical.py
code league_data.json
code .                       # open entire project folder
```

### Standard git push workflow
```bash
git add .
git commit -m "describe what you changed"
git pull origin main --rebase
git push
```

### If push is rejected
```bash
git pull origin main --rebase
git push
# If still failing:
git push --force             # use sparingly, only when you're sure your version is correct
```

### Troubleshooting auth errors locally
```bash
unset ESPN_S2                # clears cached environment variable
unset SWID
# Then set fresh values:
export ESPN_S2="your_cookie_here"
export SWID="{your_swid_here}"
```

---

## Opening Day / Start of Season Checklist
1. Run `python3 roto.py` manually after first week of games
2. Dump box score stats dict (see debug method above)
3. Verify ESPN key for **SV+HLD** — might be `SV+HLD`, `SVHLD`, `SVH` or something else
4. Verify **OBP** and **SLG** appear directly in stats dict or confirm calculation from underlying stats is correct
5. Update `get_raw_stats()` function in roto.py with correct keys
6. Sanity check week 1 numbers against what ESPN shows on their site
7. Fix historical.py year range: `range(2019, 2026)` → `range(2019, 2027)`
8. Add OBP/SLG tracking to historical.py

---

## Frontend (Lovable.dev)
- Built at lovable.dev, connected to GitHub repo
- 3 free AI credits per day on free tier
- Code is read-only on free tier without using a credit
- Do not burn credits on placeholder/empty data — wait for real season data

### Pages built
- Roto standings (hitting pts, pitching pts, total — sortable)
- Luck report (actual win% vs universal win%, luck delta)
- Weekly roto (week selector showing standings for that week)
- Matchup recap (who played who, category results)
- Owner profiles (click owner → see their history, records, championships)
- League records (best single week and season per category across all owners)
- Keeper history (year selector showing each team's keepers)
- Rulebook (searchable, full league rules)
- Pay Dues button (Venmo link)

### Updating the frontend with new data
The frontend reads directly from the GitHub raw URLs. No frontend changes needed when data updates — the JSON files update automatically and the site reflects new data within ~10 minutes (CDN cache).

### Updating content (rules, keepers, etc.)
Use a Lovable credit and describe the change in plain English. Example: "Update rule 4.2 to say X instead of Y."

---

## Known Issues & TODO List
1. **Empty week check** — current approach (checking for zero stats) incorrectly triggers. Need a smarter check. Consider: check if `generated_at` date is before the season start date, or check ESPN's matchup period dates.
2. **SV+HLD key** — `PITCHING_CATS` in roto.py uses `'SV'` but league uses saves+holds combined. Update after verifying ESPN key.
3. **historical.py year range** — change `range(2019, 2026)` to `range(2019, 2027)`
4. **historical.py OBP/SLG** — add these categories and the underlying stats needed: H, AB, B_BB, HBP, SF, 2B, 3B
5. **GitHub Actions Node.js deprecation** — update `actions/checkout@v3` to `@v4` and `actions/setup-python@v4` to `@v5` before June 2026
6. **Weekly JSON shows 19 weeks of zeros** when season is early — frontend should gracefully handle empty weeks (show only weeks with data)

---

## ESPN API Notes
- ESPN's API is **unofficial and undocumented** — reverse engineered by the community via the `espn-api` Python library
- Private leagues require `espn_s2` and `SWID` cookies for authentication
- Box scores (weekly matchup data with stats) are only available from 2019 onwards for this league
- ESPN may change their API without notice — if things break suddenly, check if the `espn-api` library has updates
- Real-time stats during games are in a different data layer and may not appear in the API until overnight processing
- The `espn-api` library version installed: check with `pip show espn-api` in the venv

---

## Useful Context About the League
- **30+ year old league** — one of the oldest and most competitive fantasy baseball leagues around
- **Team names change every year** — do not hardcode team names anywhere
- **Owners are tracked by real name**, not ESPN username or team name
- **2020 was skipped** in historical data — league ran differently that COVID year
- **Toby Rotman** won the championship in 2024 (team name at the time: "Try to Shake Things Up, Again")
- The luck metric is Toby's invention for this site — it's not an ESPN feature

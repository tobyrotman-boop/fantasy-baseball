from espn_api.baseball import League
import json
from datetime import date

# Your league credentials
LEAGUE_ID = 4080
YEAR = 2025
ESPN_S2 = "AEBLtSnyQ1nrcjPtcW+i9HCeoKtko0oaKEVutWzgmbFH3xvd1MG2Ev7/31UvBmJNxUXRyCFRGA4rS/hfVFgxPnkYmozGjxX/RfV8VepheMJQa1rS1MAfW2ifECTVB6adfqR6NIUzge9wO+5o6vGl0YGCx+dmpi/6DxEUP+EcykGMQvrNhp4K9LTxB9cg4iikK+PKLYeQsaC3qDgz9ACOBqYiY831kTbtWtwDj2oWexfMdb2VbxOkoRPT1PptXW7Wi+whDXWunNj/8qKrC7Nvbvy0"
SWID = "{27E33A0F-8C90-11D3-8208-00A0C9E58E2D}"

league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)


HITTING_CATS  = ['HR', 'RBI', 'SB', 'R', 'OBP', 'SLG']
PITCHING_CATS = ['QS', 'W', 'K', 'SV', 'ERA', 'WHIP']
ALL_CATS      = HITTING_CATS + PITCHING_CATS
LOWER_IS_BETTER = {'ERA', 'WHIP'}

def get_raw_stats(stats):
    return {
        'HR':   stats.get('HR',   {}).get('value', 0) or 0,
        'RBI':  stats.get('RBI',  {}).get('value', 0) or 0,
        'SB':   stats.get('SB',   {}).get('value', 0) or 0,
        'R':    stats.get('R',    {}).get('value', 0) or 0,
        'H':    stats.get('H',    {}).get('value', 0) or 0,
        'AB':   stats.get('AB',   {}).get('value', 0) or 0,
        'B_BB': stats.get('B_BB', {}).get('value', 0) or 0,
        'HBP':  stats.get('HBP',  {}).get('value', 0) or 0,
        'SF':   stats.get('SF',   {}).get('value', 0) or 0,
        '2B':   stats.get('2B',   {}).get('value', 0) or 0,
        '3B':   stats.get('3B',   {}).get('value', 0) or 0,
        'QS':   stats.get('QS',   {}).get('value', 0) or 0,
        'W':    stats.get('W',    {}).get('value', 0) or 0,
        'K':    stats.get('K',    {}).get('value', 0) or 0,
        'SV':   stats.get('SV',   {}).get('value', 0) or 0,
        'ER':   stats.get('ER',   {}).get('value', 0) or 0,
        'OUTS': stats.get('OUTS', {}).get('value', 0) or 0,
        'P_H':  stats.get('P_H',  {}).get('value', 0) or 0,
        'P_BB': stats.get('P_BB', {}).get('value', 0) or 0,
    }

def calc_ratios(s):
    obp_den = s['AB'] + s['B_BB'] + s['HBP'] + s['SF']
    obp = (s['H'] + s['B_BB'] + s['HBP']) / obp_den if obp_den > 0 else 0
    singles = s['H'] - s['2B'] - s['3B'] - s['HR']
    tb = singles + (2 * s['2B']) + (3 * s['3B']) + (4 * s['HR'])
    slg = tb / s['AB'] if s['AB'] > 0 else 0
    ip = s['OUTS'] / 3
    era  = (s['ER'] * 9) / ip if ip > 0 else 0
    whip = (s['P_H'] + s['P_BB']) / ip if ip > 0 else 0
    return {
        'HR': s['HR'], 'RBI': s['RBI'], 'SB': s['SB'], 'R': s['R'],
        'OBP': obp, 'SLG': slg,
        'QS': s['QS'], 'W': s['W'], 'K': s['K'], 'SV': s['SV'],
        'ERA': era, 'WHIP': whip
    }

def rank_category(teams_stats, cat):
    """
    Rank all teams in a single category with half-point tie splitting.
    Returns dict of {team_name: points}
    """
    # Sort: lower is better for ERA/WHIP, higher is better otherwise
    reverse = cat not in LOWER_IS_BETTER
    sorted_teams = sorted(teams_stats.keys(),
                          key=lambda n: teams_stats[n][cat],
                          reverse=reverse)
    
    points = {}
    n = len(sorted_teams)
    i = 0
    while i < n:
        # Find all teams tied at this position
        j = i
        while j < n and teams_stats[sorted_teams[j]][cat] == teams_stats[sorted_teams[i]][cat]:
            j += 1
        # Ranks for tied teams: i+1 through j (1-indexed)
        # Average them for half-point splits
         # Convert rank to points: best rank (1) = n points, worst rank (n) = 1 point
        avg_rank = sum(range(i + 1, j + 1)) / (j - i)
        converted = (n + 1) - avg_rank
        for k in range(i, j):
            points[sorted_teams[k]] = converted
        i = j
    return points

def compare_cats(stats_a, stats_b):
    """Compare two teams category by category. Returns (wins_a, wins_b, ties)."""
    wins_a = wins_b = ties = 0
    for cat in ALL_CATS:
        a = stats_a[cat]
        b = stats_b[cat]
        if a == b:
            ties += 1
        elif cat in LOWER_IS_BETTER:
            if a < b: wins_a += 1
            else:     wins_b += 1
        else:
            if a > b: wins_a += 1
            else:     wins_b += 1
    return wins_a, wins_b, ties

# ── Initialize accumulators ──────────────────────────────────────────────────
team_names = [t.team_name for t in league.teams]

cumulative_raw = {
    name: {k: 0 for k in ['HR','RBI','SB','R','H','AB','B_BB','HBP','SF',
                           '2B','3B','QS','W','K','SV','ER','OUTS','P_H','P_BB']}
    for name in team_names
}

actual_wins    = {name: 0 for name in team_names}
actual_losses  = {name: 0 for name in team_names}
universal_wins  = {name: 0 for name in team_names}
universal_losses = {name: 0 for name in team_names}

roto_history = []

# ── Main loop ────────────────────────────────────────────────────────────────
print("Pulling data for all 19 weeks...")
for week in range(1, 20):
    try:
        boxes = league.box_scores(week)

        # Accumulate raw stats
        week_raw = {}
        for box in boxes:
            for team, stats_dict in [(box.home_team, box.home_stats),
                                     (box.away_team, box.away_stats)]:
                name = team.team_name
                raw  = get_raw_stats(stats_dict)
                week_raw[name] = raw
                for k in cumulative_raw[name]:
                    cumulative_raw[name][k] += raw[k]

        # Weekly ratios (for matchup comparisons)
        week_ratios = {name: calc_ratios(week_raw[name]) for name in week_raw}

        # Actual records
        for box in boxes:
            home = box.home_team.team_name
            away = box.away_team.team_name
            if home not in week_ratios or away not in week_ratios:
                continue
            w_h, w_a, _ = compare_cats(week_ratios[home], week_ratios[away])
            actual_wins[home]   += w_h
            actual_losses[home] += w_a
            actual_wins[away]   += w_a
            actual_losses[away] += w_h

        # Universal matchups
        names_this_week = list(week_ratios.keys())
        for i in range(len(names_this_week)):
            for j in range(i + 1, len(names_this_week)):
                a, b = names_this_week[i], names_this_week[j]
                w_a, w_b, _ = compare_cats(week_ratios[a], week_ratios[b])
                universal_wins[a]   += w_a
                universal_losses[a] += w_b
                universal_wins[b]   += w_b
                universal_losses[b] += w_a

        # Rolling roto snapshot with half-point tie splitting
        cumulative_ratios = {name: calc_ratios(cumulative_raw[name]) for name in team_names}
        
        hit_pts  = {name: 0.0 for name in team_names}
        pitch_pts = {name: 0.0 for name in team_names}

        for cat in HITTING_CATS:
            cat_points = rank_category(cumulative_ratios, cat)
            for name, pts in cat_points.items():
                hit_pts[name] += pts

        for cat in PITCHING_CATS:
            cat_points = rank_category(cumulative_ratios, cat)
            for name, pts in cat_points.items():
                pitch_pts[name] += pts

        roto_history.append({
            'week': week,
            'hit_pts':   hit_pts.copy(),
            'pitch_pts': pitch_pts.copy()
        })

        print(f"  Week {week} done")

    except Exception as e:
        print(f"  Week {week} failed: {e}")

# ── REPORT 1: Roto Standings ─────────────────────────────────────────────────
print("\n" + "="*75)
print("REPORT 1: FINAL ROTO STANDINGS")
print("="*75)

final = roto_history[-1]
roto_rows = []
for name in team_names:
    h = final['hit_pts'][name]
    p = final['pitch_pts'][name]
    roto_rows.append((name, h, p, h + p))

roto_rows.sort(key=lambda x: x[3], reverse=True)
print(f"{'TEAM':<30} {'HIT PTS':>9} {'PITCH PTS':>10} {'TOTAL':>8}")
print("-"*60)
for name, h, p, t in roto_rows:
    print(f"{name:<30} {h:>9.1f} {p:>10.1f} {t:>8.1f}")

# ── REPORT 2: Luck Table ──────────────────────────────────────────────────────
print("\n" + "="*75)
print("REPORT 2: LUCK TABLE (actual win% vs universal win%)")
print("="*75)
print(f"{'TEAM':<30} {'ACT W':>6} {'ACT L':>6} {'ACT%':>7} {'UNI W':>7} {'UNI L':>7} {'UNI%':>7} {'LUCK':>7}")
print("-"*85)

luck_rows = []
for name in team_names:
    aw = actual_wins[name]
    al = actual_losses[name]
    ap = aw / (aw + al) if (aw + al) > 0 else 0
    uw = universal_wins[name]
    ul = universal_losses[name]
    up = uw / (uw + ul) if (uw + ul) > 0 else 0
    luck_rows.append((name, aw, al, ap, uw, ul, up, ap - up))

luck_rows.sort(key=lambda x: x[7], reverse=True)
for name, aw, al, ap, uw, ul, up, luck in luck_rows:
    print(f"{name:<30} {aw:>6} {al:>6} {ap:>7.3f} {uw:>7} {ul:>7} {up:>7.3f} {luck:>+7.3f}")

# ── REPORT 3: Rolling Roto Standings by Week ──────────────────────────────────
print("\n" + "="*75)
print("REPORT 3: ROLLING ROTO STANDINGS BY WEEK")
print("="*75)

for snapshot in roto_history:
    week = snapshot['week']
    print(f"\n--- Week {week} ---")
    rows = []
    for name in team_names:
        h = snapshot['hit_pts'][name]
        p = snapshot['pitch_pts'][name]
        rows.append((name, h, p, h + p))
    rows.sort(key=lambda x: x[3], reverse=True)
    print(f"{'TEAM':<30} {'HIT':>7} {'PITCH':>7} {'TOTAL':>7}")
    print("-"*55)
    for name, h, p, t in rows:
        print(f"{name:<30} {h:>7.1f} {p:>7.1f} {t:>7.1f}")

# ── JSON Output ───────────────────────────────────────────────────────────────

output = {
    "generated_at": str(date.today()),
    "roto_standings": [
        {
            "team": name,
            "hitting_pts": round(h, 1),
            "pitching_pts": round(p, 1),
            "total_pts": round(h + p, 1)
        }
        for name, h, p, t in roto_rows
    ],
    "luck_table": [
        {
            "team": name,
            "actual_wins": aw,
            "actual_losses": al,
            "actual_pct": round(ap, 3),
            "universal_wins": uw,
            "universal_losses": ul,
            "universal_pct": round(up, 3),
            "luck": round(luck, 3)
        }
        for name, aw, al, ap, uw, ul, up, luck in luck_rows
    ],
    "weekly_roto": [
        {
            "week": snapshot['week'],
            "standings": sorted(
                [
                    {
                        "team": name,
                        "hitting_pts": round(snapshot['hit_pts'][name], 1),
                        "pitching_pts": round(snapshot['pitch_pts'][name], 1),
                        "total_pts": round(snapshot['hit_pts'][name] + snapshot['pitch_pts'][name], 1)
                    }
                    for name in team_names
                ],
                key=lambda x: x['total_pts'],
                reverse=True
            )
        }
        for snapshot in roto_history
    ]
}

with open("league_data.json", "w") as f:
    json.dump(output, f, indent=2)

print("\nData written to league_data.json")





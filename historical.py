from espn_api.baseball import League
import json
from datetime import date

ESPN_S2 = "AEBLtSnyQ1nrcjPtcW+i9HCeoKtko0oaKEVutWzgmbFH3xvd1MG2Ev7/31UvBmJNxUXRyCFRGA4rS/hfVFgxPnkYmozGjxX/RfV8VepheMJQa1rS1MAfW2ifECTVB6adfqR6NIUzge9wO+5o6vGl0YGCx+dmpi/6DxEUP+EcykGMQvrNhp4K9LTxB9cg4iikK+PKLYeQsaC3qDgz9ACOBqYiY831kTbtWtwDj2oWexfMdb2VbxOkoRPT1PptXW7Wi+whDXWunNj/8qKrC7Nvbvy0"
SWID = "{27E33A0F-8C90-11D3-8208-00A0C9E58E2D}"
LEAGUE_ID = 4080

SKIP_YEARS = {2020}
FIRST_VALID_YEAR = 2019  # box scores not available before this

# Categories we actually care about
COUNTING_CATS = ['HR', 'RBI', 'SB', 'R', 'K', 'W', 'QS', 'SV']
RATIO_CATS = ['ERA', 'WHIP']
ALL_SCORE_CATS = COUNTING_CATS + RATIO_CATS
LOWER_IS_BETTER = {'ERA', 'WHIP'}

def get_owner_key(team):
    for owner in team.owners:
        first = owner.get('firstName', '')
        last = owner.get('lastName', '')
        if first or last:
            return f"{first} {last}".strip()
    return team.team_name

def get_raw_stats(stats):
    """Extract raw underlying stats needed for calculations."""
    def v(key):
        return stats.get(key, {}).get('value', 0) or 0
    return {
        'HR': v('HR'), 'RBI': v('RBI'), 'SB': v('SB'), 'R': v('R'),
        'K': v('K'), 'W': v('W'), 'QS': v('QS'), 'SV': v('SV'),
        'ER': v('ER'), 'OUTS': v('OUTS'),
        'P_H': v('P_H'), 'P_BB': v('P_BB')
    }

def calc_era(er, outs):
    ip = outs / 3
    return (er * 9) / ip if ip > 0 else 0

def calc_whip(p_h, p_bb, outs):
    ip = outs / 3
    return (p_h + p_bb) / ip if ip > 0 else 0

def is_better(cat, new_val, old_val):
    if cat in LOWER_IS_BETTER:
        return new_val < old_val
    return new_val > old_val

owners = {}

def ensure_owner(name):
    if name not in owners:
        owners[name] = {
            'name': name,
            'championships': 0,
            'seasons': [],
            'weekly_records': {},
            'season_records': {},
        }

for year in range(2019, 2026):
    if year in SKIP_YEARS:
        print(f"Skipping {year}")
        continue

    print(f"\nProcessing {year}...")
    try:
        league = League(league_id=LEAGUE_ID, year=year, espn_s2=ESPN_S2, swid=SWID)
    except Exception as e:
        print(f"  Could not load {year}: {e}")
        continue

    reg_season_weeks = league.settings.reg_season_count
    print(f"  {reg_season_weeks} regular season weeks")

    # Championships
    for team in league.teams:
        owner = get_owner_key(team)
        ensure_owner(owner)
        if team.final_standing == 1:
            owners[owner]['championships'] += 1
            print(f"  Champion: {owner} ({team.team_name})")

    # Season accumulators
    season_raw = {get_owner_key(t): {k: 0 for k in ['HR','RBI','SB','R','K','W','QS','SV','ER','OUTS','P_H','P_BB']}
                  for t in league.teams}

    for week in range(1, reg_season_weeks + 1):
        try:
            boxes = league.box_scores(week)
            for box in boxes:
                for team, stats_dict in [(box.home_team, box.home_stats),
                                         (box.away_team, box.away_stats)]:
                    owner = get_owner_key(team)
                    ensure_owner(owner)
                    raw = get_raw_stats(stats_dict)

                    # Accumulate season totals
                    for k in season_raw[owner]:
                        season_raw[owner][k] += raw[k]

                    # Weekly records for counting cats
                    for cat in COUNTING_CATS:
                        val = raw[cat]
                        if val == 0:
                            continue
                        rec = owners[owner]['weekly_records'].get(cat)
                        if rec is None or is_better(cat, val, rec['value']):
                            owners[owner]['weekly_records'][cat] = {
                                'value': val, 'year': year, 'week': week, 'team': team.team_name
                            }

                    # Weekly records for ratio cats
                    week_era  = calc_era(raw['ER'], raw['OUTS'])
                    week_whip = calc_whip(raw['P_H'], raw['P_BB'], raw['OUTS'])
                    for cat, val in [('ERA', week_era), ('WHIP', week_whip)]:
                        if val == 0:
                            continue
                        rec = owners[owner]['weekly_records'].get(cat)
                        if rec is None or is_better(cat, val, rec['value']):
                            owners[owner]['weekly_records'][cat] = {
                                'value': round(val, 3), 'year': year, 'week': week, 'team': team.team_name
                            }

            print(f"  Week {week} done")
        except Exception as e:
            print(f"  Week {week} failed: {e}")

    # Season records
    for owner, s in season_raw.items():
        season_era  = calc_era(s['ER'], s['OUTS'])
        season_whip = calc_whip(s['P_H'], s['P_BB'], s['OUTS'])

        season_stats = {cat: s[cat] for cat in COUNTING_CATS}
        season_stats['ERA']  = round(season_era, 3)
        season_stats['WHIP'] = round(season_whip, 3)

        # Check season records
        for cat, val in season_stats.items():
            if val == 0:
                continue
            rec = owners[owner]['season_records'].get(cat)
            if rec is None or is_better(cat, val, rec['value']):
                owners[owner]['season_records'][cat] = {
                    'value': val, 'year': year
                }

        owners[owner]['seasons'].append({
            'year': year,
            'stats': season_stats
        })

output = {
    'generated_at': str(date.today()),
    'owners': list(owners.values())
}

with open('historical.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\nDone! Data written to historical.json")
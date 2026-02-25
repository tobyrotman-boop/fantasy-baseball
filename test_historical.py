from espn_api.baseball import League
import os

LEAGUE_ID = 4080
YEAR = 2020
ESPN_S2 = "AEBLtSnyQ1nrcjPtcW+i9HCeoKtko0oaKEVutWzgmbFH3xvd1MG2Ev7/31UvBmJNxUXRyCFRGA4rS/hfVFgxPnkYmozGjxX/RfV8VepheMJQa1rS1MAfW2ifECTVB6adfqR6NIUzge9wO+5o6vGl0YGCx+dmpi/6DxEUP+EcykGMQvrNhp4K9LTxB9cg4iikK+PKLYeQsaC3qDgz9ACOBqYiY831kTbtWtwDj2oWexfMdb2VbxOkoRPT1PptXW7Wi+whDXWunNj/8qKrC7Nvbvy0"
SWID = "{27E33A0F-8C90-11D3-8208-00A0C9E58E2D}"

league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

for team in league.teams:
    print(f"Team: {team.team_name}")
    print(f"  Owners: {team.owners}")
    print(f"  Final standing: {team.final_standing}")
    print()

boxes = league.box_scores(1)
box = boxes[0]
print(box.home_team.team_name)
print(box.home_stats)
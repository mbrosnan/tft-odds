#!/usr/bin/env python3
"""Debug script to understand round 12 cut threshold issue"""

import json
from simulation import *
from models import *

# Load the tour format and initial state
with open('s14_na_gs/tour_format.json', 'r') as f:
    tour_format_data = json.load(f)
tour_format = TourFormat(**tour_format_data)

# Create a simple test state with 16 players before round 12
players = []
for i in range(1, 17):
    player = Player(
        id=i,
        name=f"Player {i}",
        points=50 + i,  # Give them different points
        total_points=50 + i,
        tiebreakers=Tiebreakers(),
        round_history=[],
        avg_placement=4.5,
        completed_rounds=11,
        is_eliminated=False,
        eliminated_at=None
    )
    players.append(player)

# Create tour state at round 12
current_round = CurrentRound(
    overall_round=12,
    day=2,
    round_in_day=6,
    round_status=RoundStatus.COMPLETED
)

tour_state = TourState(
    current_round=current_round,
    players=players,
    eliminated_players=[]
)

print("BEFORE PROCESSING POST-ROUND ACTIONS:")
print(f"Number of players: {len(tour_state.players)}")
print(f"Player points: {[(p.name, p.points) for p in sorted(tour_state.players, key=lambda x: x.points, reverse=True)[:5]]}")

# Process post-round actions for round 12
results = {"cut_thresholds": {}}
updated_state, cut_history = process_post_round_actions(tour_state, tour_format, results)

print("\nAFTER PROCESSING POST-ROUND ACTIONS:")
print(f"Number of players: {len(updated_state.players)}")
print(f"Player points: {[(p.name, p.points) for p in sorted(updated_state.players, key=lambda x: x.points, reverse=True)[:5]]}")
print(f"Cut thresholds collected: {results.get('cut_thresholds', {})}")

# Check the cut threshold
if 'round_12_cut_to_8' in results['cut_thresholds']:
    threshold = results['cut_thresholds']['round_12_cut_to_8'][0]
    print(f"\nRound 12 cut threshold: {threshold}")
else:
    print("\nNo cut threshold recorded for round 12!")
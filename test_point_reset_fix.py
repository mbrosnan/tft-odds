#!/usr/bin/env python3

import json
from simulation import simulate_tournament, load_tour_state_from_csv
from utils import load_tour_format_from_json
from models import SimSettings, SimulationMode, ProbabilityTarget

def test_point_reset_fix():
    """Test that the point reset fix is working correctly."""
    
    # Create a simple test case
    print("=" * 60)
    print("TESTING POINT RESET FIX")
    print("=" * 60)
    
    # Load the tournament format that has a point reset after round 6
    tour_format = load_tour_format_from_json("s14tt3/tour_format_Set14_NA_TacTrials3.json")
    
    # Create a minimal tour state for testing
    # We'll create a state at round 3 with some players having different points
    tour_state_json = {
        "current_round": {
            "overall_round": 3,
            "day": 1,
            "round_in_day": 3,
            "round_status": "not_started"
        },
        "players": [
            {
                "id": 1,
                "name": "Player_8pts_1first",
                "points": 8,
                "total_points": 8,
                "prior_day_points": 0,
                "avg_placement": 4.5,
                "completed_rounds": 2,
                "round_history": [
                    {"overall_round": 1, "day": 1, "round_in_day": 1, "lobby": "A", "placement": 1, "points": 8, "no_show": False},
                    {"overall_round": 2, "day": 1, "round_in_day": 2, "lobby": "B", "placement": 8, "points": 0, "no_show": False}
                ],
                "tiebreakers": {"firsts": 1, "seconds": 0, "thirds": 0, "fourths": 0, "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 1, "top4s": 1, "firsts_plus_top4s": 2, "total_points": 8},
                "is_eliminated": False,
                "eliminated_at": None
            },
            {
                "id": 2,
                "name": "Player_15pts_consistent",
                "points": 15,
                "total_points": 15,
                "prior_day_points": 0,
                "avg_placement": 1.5,
                "completed_rounds": 2,
                "round_history": [
                    {"overall_round": 1, "day": 1, "round_in_day": 1, "lobby": "A", "placement": 2, "points": 7, "no_show": False},
                    {"overall_round": 2, "day": 1, "round_in_day": 2, "lobby": "B", "placement": 1, "points": 8, "no_show": False}
                ],
                "tiebreakers": {"firsts": 1, "seconds": 1, "thirds": 0, "fourths": 0, "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 0, "top4s": 2, "firsts_plus_top4s": 3, "total_points": 15},
                "is_eliminated": False,
                "eliminated_at": None
            },
            {
                "id": 3,
                "name": "Player_3pts_poor",
                "points": 3,
                "total_points": 3,
                "prior_day_points": 0,
                "avg_placement": 6.5,
                "completed_rounds": 2,
                "round_history": [
                    {"overall_round": 1, "day": 1, "round_in_day": 1, "lobby": "A", "placement": 7, "points": 2, "no_show": False},
                    {"overall_round": 2, "day": 1, "round_in_day": 2, "lobby": "B", "placement": 6, "points": 1, "no_show": False}
                ],
                "tiebreakers": {"firsts": 0, "seconds": 0, "thirds": 0, "fourths": 0, "fifths": 0, "sixths": 1, "sevenths": 1, "eighths": 0, "top4s": 0, "firsts_plus_top4s": 0, "total_points": 3},
                "is_eliminated": False,
                "eliminated_at": None
            }
        ],
        "eliminated_players": []
    }
    
    # Save to temporary file
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(tour_state_json, f)
        temp_file = f.name
    
    try:
        # Load the tour state
        from utils import load_tour_state_from_json
        tour_state = load_tour_state_from_json(temp_file)
        
        # Create sim settings for a small number of iterations
        sim_settings = SimSettings(
            max_iterations=100,
            mode=SimulationMode.ITERATIONS_ONLY,
            probability_targets=[
                ProbabilityTarget(
                    probability_name="made_top_120_cut",
                    type="made_cut",
                    players_remaining=120
                ),
                ProbabilityTarget(
                    probability_name="made_top_104_cut",
                    type="made_cut",
                    players_remaining=104
                ),
                ProbabilityTarget(
                    probability_name="finished_top_54",
                    type="overall_standing",
                    comparison="at_or_above",
                    threshold=54
                )
            ]
        )
        
        print(f"Starting simulation with {len(tour_state.players)} test players")
        print("Player states before simulation:")
        for player in tour_state.players:
            print(f"  {player.name}: {player.points} pts, firsts={player.tiebreakers.firsts}")
        
        # Run simulation
        results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings)
        
        print(f"\nSimulation complete: {sim_count} iterations")
        
        # Check results
        if "player_probabilities" in results:
            print("\nProbability results:")
            for player_name, probs in results["player_probabilities"].items():
                if player_name.startswith("Player_"):
                    print(f"\n{player_name}:")
                    for prob_name, prob_data in probs.items():
                        if isinstance(prob_data, dict) and "probability" in prob_data:
                            print(f"  {prob_name}: {prob_data['probability']:.1%}")
        
        # The key test: Player_8pts_1first should NOT have an unrealistically high probability
        # of making the top 104 cut (which happens after round 10, well after the point reset)
        if "player_probabilities" in results:
            player_8pts = results["player_probabilities"].get("Player_8pts_1first", {})
            top_104_prob = player_8pts.get("made_top_104_cut", {}).get("probability", 0)
            
            print(f"\nKEY TEST RESULT:")
            print(f"Player with 8 points (1 first) has {top_104_prob:.1%} chance of making top 104 cut")
            print(f"Expected: Should be much lower than 40% (the original bug)")
            
            if top_104_prob < 0.20:  # Should be less than 20%
                print("✓ TEST PASSED: Probability is reasonable")
            else:
                print("✗ TEST FAILED: Probability is still too high")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.unlink(temp_file)

if __name__ == "__main__":
    test_point_reset_fix()
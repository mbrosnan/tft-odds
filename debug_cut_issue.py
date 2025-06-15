#!/usr/bin/env python3

import json
from simulation import simulate_tournament
from utils import load_tour_format_from_json
from csv_to_tourstate import parse_csv_to_tourstate
from models import SimSettings, SimulationMode, ProbabilityTarget

def debug_cut_issue():
    """Debug the cut probability issue with minimal iterations."""
    
    # Load data
    from simulation import load_tour_state_from_csv
    
    tour_format = load_tour_format_from_json("s14tt3/tour_format_Set14_NA_TacTrials3.json")
    tour_state = load_tour_state_from_csv("s14tt3/day2/TT3_Live_beforer7_5.csv", "s14tt3/tour_format_Set14_NA_TacTrials3.json")
    
    # Create minimal sim settings with just the problematic targets
    sim_settings = SimSettings(
        max_iterations=1,  # Just 1 iteration to see debug output clearly
        mode=SimulationMode.ITERATIONS_ONLY,
        probability_targets=[
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
    
    print("=" * 60)
    print("DEBUGGING CUT PROBABILITY ISSUE")
    print("=" * 60)
    print(f"Starting simulation with {len(tour_state.players)} players")
    print(f"Current round: {tour_state.current_round.overall_round}")
    print(f"Cut rules: {[f'Round {rule.after_round} -> {rule.players_remaining}' for rule in tour_format.cut_rules]}")
    print("=" * 60)
    
    # Manually run one simulation to inspect the data
    from simulation import validate_and_load_state, simulate_next_round, process_post_round_actions, is_tournament_complete, determine_final_standings, evaluate_probability_targets
    
    current_state = validate_and_load_state(tour_state)
    cut_history = {}
    
    # Run simulation loop
    round_count = 0
    while not is_tournament_complete(current_state, tour_format):
        round_count += 1
        if round_count > 10:  # Safety break to avoid infinite loop
            print(f"  SAFETY BREAK: Too many rounds simulated")
            break
            
        print(f"\n--- Round {current_state.current_round.overall_round} ---")
        print(f"  Players before round: {len(current_state.players)}")
        
        current_state = simulate_next_round(current_state, tour_format)
        print(f"  Players after round: {len(current_state.players)}")
        
        current_state, round_cut_history = process_post_round_actions(current_state, tour_format)
        print(f"  Players after post-round actions: {len(current_state.players)}")
        print(f"  Round cut history: {list(round_cut_history.keys())}")
        print(f"  Tournament complete: {is_tournament_complete(current_state, tour_format)}")
        
        cut_history.update(round_cut_history)
    
    # Get final standings
    final_standings = determine_final_standings(current_state, silent=True)
    
    print(f"Final tournament state:")
    print(f"  Active players: {len(final_standings)}")
    print(f"  Eliminated players: {len(current_state.eliminated_players)}")
    print(f"  Cut history keys: {list(cut_history.keys())}")
    
    for cut_size, players in cut_history.items():
        print(f"  Cut to {cut_size}: {len(players)} players")
        # Show first few player names for each cut
        player_names = [p.name for p in players[:5]]
        print(f"    First 5: {player_names}")
    
    # Show final standings players
    final_player_names = [p.name for p in final_standings[:5]]
    print(f"  Final standings first 5: {final_player_names}")
    
    # Test the evaluation logic
    target_results = evaluate_probability_targets(final_standings, current_state.eliminated_players, sim_settings, cut_history)
    
    print(f"\nTarget evaluation results:")
    for target_name, results in target_results.items():
        true_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        print(f"  {target_name}: {true_count}/{total_count} players achieved target")
        
        # Show which players achieved the target
        true_players = [name for name, result in results.items() if result][:5]
        print(f"    First 5 true players: {true_players}")
    
    # Manual check: see if the cut_history[104] contains different players than final_standings
    if 104 in cut_history and 54 in cut_history:
        cut_104_names = set(p.name for p in cut_history[104])
        cut_54_names = set(p.name for p in cut_history[54])
        final_names = set(p.name for p in final_standings)
        
        print(f"\nManual verification:")
        print(f"  Players in cut_history[104]: {len(cut_104_names)}")
        print(f"  Players in cut_history[54]: {len(cut_54_names)}")
        print(f"  Players in final_standings: {len(final_names)}")
        print(f"  cut_history[54] == final_standings: {cut_54_names == final_names}")
        print(f"  cut_history[104] contains all of cut_history[54]: {cut_54_names.issubset(cut_104_names)}")
        
        # Show some players who made 104 cut but not 54 cut
        only_104_not_54 = cut_104_names - cut_54_names
        print(f"  Players who made 104 cut but not 54 cut: {len(only_104_not_54)}")
        if only_104_not_54:
            print(f"    Examples: {list(only_104_not_54)[:5]}")
    
    print("=" * 60)

if __name__ == "__main__":
    debug_cut_issue() 
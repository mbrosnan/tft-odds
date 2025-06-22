#!/usr/bin/env python3
"""Debug script to run simulation round by round and inspect results."""

import json
import sys
from models import TourState
from simulation import simulate_next_round, sort_players_by_standing
from csv_to_tourstate import parse_csv_to_tourstate
from utils import load_tour_format_from_json

def print_round_summary(tour_state, round_num):
    """Print a summary of the current round state."""
    print(f"\n{'='*60}")
    print(f"AFTER ROUND {round_num}")
    print(f"{'='*60}")
    
    # Sort players by standing
    sorted_players = sort_players_by_standing(tour_state.players)
    
    # Count active players
    active_players = [p for p in sorted_players if not p.is_eliminated]
    print(f"Active players: {len(active_players)}")
    
    # Show top 10 and bottom 10 players
    print("\nTop 10 players:")
    print(f"{'Rank':<6} {'Name':<12} {'Points':<8} {'Prior':<8} {'Total':<8} {'Avg Place':<10}")
    print("-" * 60)
    
    for i, player in enumerate(sorted_players[:10]):
        total_with_prior = player.points + player.prior_day_points
        avg_place = sum(r.placement for r in player.round_history if r.placement) / len([r for r in player.round_history if r.placement]) if any(r.placement for r in player.round_history) else 0
        print(f"{i+1:<6} {player.name:<12} {player.points:<8} {player.prior_day_points:<8} {total_with_prior:<8} {avg_place:<10.2f}")
    
    if len(active_players) > 20:
        print("\n...")
        print(f"\nBottom 10 active players (ranks {len(active_players)-9} to {len(active_players)}):")
        print(f"{'Rank':<6} {'Name':<12} {'Points':<8} {'Prior':<8} {'Total':<8} {'Avg Place':<10}")
        print("-" * 60)
        
        bottom_players = [p for p in sorted_players if not p.is_eliminated][-10:]
        for i, player in enumerate(bottom_players):
            rank = len(active_players) - 10 + i + 1
            total_with_prior = player.points + player.prior_day_points
            avg_place = sum(r.placement for r in player.round_history if r.placement) / len([r for r in player.round_history if r.placement]) if any(r.placement for r in player.round_history) else 0
            print(f"{rank:<6} {player.name:<12} {player.points:<8} {player.prior_day_points:<8} {total_with_prior:<8} {avg_place:<10.2f}")
    
    # Check for any anomalies
    print("\nChecking for anomalies:")
    
    # Check if anyone has too many points
    max_possible_points = round_num * 8  # 8 points per round max
    for player in sorted_players:
        if player.points > max_possible_points:
            print(f"  WARNING: {player.name} has {player.points} points after {round_num} rounds (max possible: {max_possible_points})")
    
    # Check average placements
    for player in sorted_players[:10]:
        placements = [r.placement for r in player.round_history if r.placement]
        if placements and sum(placements) / len(placements) > 5:  # avg placement worse than 5th
            print(f"  WARNING: {player.name} in top 10 with avg placement {sum(placements)/len(placements):.2f}")

def main():
    # Load tournament state and format
    print("Loading tournament data...")
    # Parse CSV to JSON first
    parse_csv_to_tourstate("tc3day3/tour_state_round1_complete.csv", 
                          "tc3day3/tour_state_debug.json",
                          "tc3day3/tour_format_Set14_NA_TacCup3Day3.json")
    
    # Load the tour state from JSON
    with open("tc3day3/tour_state_debug.json", 'r') as f:
        tour_state_dict = json.load(f)
    
    # Convert to TourState object
    tour_state = TourState(**tour_state_dict)
    tour_format = load_tour_format_from_json("tc3day3/tour_format_Set14_NA_TacCup3Day3.json")
    
    print(f"Starting simulation with {len(tour_state.players)} players")
    print(f"Tournament format: {tour_format.name}")
    
    # Print initial state
    print_round_summary(tour_state, 1)
    
    # Simulate rounds 2-7
    for round_num in range(2, 8):
        print(f"\n\nSimulating round {round_num}...")
        
        # Get round structure
        round_structure = tour_format.round_structures[round_num - 1]
        print(f"  Shuffle type: {round_structure.shuffle}")
        
        # Check for cuts before this round
        if round_structure.post_round_actions:
            for action in round_structure.post_round_actions:
                if action.action == "cut":
                    print(f"  Cut scheduled after this round: top {action.top_n}")
        
        # Simulate the round
        simulate_next_round(tour_state, tour_format)
        
        # Print summary
        print_round_summary(tour_state, round_num)
        
        # Check cut thresholds if there was a cut
        if round_structure.post_round_actions:
            for action in round_structure.post_round_actions:
                if action.action == "cut":
                    sorted_players = sort_players_by_standing(tour_state.players)
                    active_players = [p for p in sorted_players if not p.is_eliminated]
                    
                    if len(active_players) > action.top_n:
                        cutoff_player = active_players[action.top_n - 1]
                        next_player = active_players[action.top_n]
                        
                        print(f"\n  CUT ANALYSIS:")
                        print(f"    Player at position {action.top_n}: {cutoff_player.name} - {cutoff_player.points} points")
                        print(f"    Player at position {action.top_n + 1}: {next_player.name} - {next_player.points} points")
                        print(f"    Cut threshold: {cutoff_player.points} points")

if __name__ == "__main__":
    main()
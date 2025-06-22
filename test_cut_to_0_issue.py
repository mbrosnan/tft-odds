#!/usr/bin/env python3
"""Test script to reproduce and debug the cut_to_0 issue when all players have 0 points."""

import json
from simulation import (
    simulate_tournament, load_tour_state_from_csv, calculate_cut_threshold,
    sort_players_by_standing, apply_cuts
)
from utils import load_tour_format_from_json
from models import SimSettings, SimulationMode, ProbabilityTarget, TourFormat, CutRule, Player, Tiebreakers

def test_cut_threshold_with_zero_points():
    """Test the cut threshold calculation when all players have 0 points."""
    print("=" * 60)
    print("TESTING CUT THRESHOLD WITH ALL PLAYERS AT 0 POINTS")
    print("=" * 60)
    
    # Create mock players with 0 points
    players = []
    for i in range(10):
        player = Player(
            id=i+1, 
            name=f"Player{i+1}", 
            points=0,
            total_points=0,
            prior_day_points=0,
            avg_placement=0.0,
            completed_rounds=0,
            round_history=[],
            tiebreakers=Tiebreakers(
                firsts=0, seconds=0, thirds=0, fourths=0,
                fifths=0, sixths=0, sevenths=0, eighths=0,
                top4s=0, firsts_plus_top4s=0, total_points=0
            ),
            is_eliminated=False,
            eliminated_at=None
        )
        players.append(player)
    
    print(f"Created {len(players)} players, all with 0 points")
    
    # Sort players by standing
    sorted_players = sort_players_by_standing(players)
    print(f"Sorted {len(sorted_players)} players")
    
    # Test cut threshold calculation for various cuts
    test_cuts = [8, 6, 4, 2, 1]
    
    for cut_to in test_cuts:
        if cut_to < len(players):
            threshold = calculate_cut_threshold(sorted_players, cut_to)
            print(f"\nCut to {cut_to} players:")
            print(f"  Threshold: {threshold}")
            
            # Check what happens in the cut logic
            if cut_to < len(sorted_players):
                last_advancing = sorted_players[cut_to - 1]
                first_eliminated = sorted_players[cut_to]
                print(f"  Last advancing player: {last_advancing.name} with {last_advancing.points} points")
                print(f"  First eliminated player: {first_eliminated.name} with {first_eliminated.points} points")
                print(f"  Points equal? {last_advancing.points == first_eliminated.points}")

def test_csv_simulation_with_no_placements():
    """Test the actual CSV file that's causing the issue."""
    print("\n" * 2)
    print("=" * 60)
    print("TESTING CSV SIMULATION WITH NO ROUND 1 PLACEMENTS")
    print("=" * 60)
    
    # Load the problematic CSV
    csv_file = "s14tt3/day2/TT3_Live_beforer7_5.csv"
    tour_format_file = "s14tt3/tour_format_Set14_NA_TacTrials3.json"
    
    # First, let's check what the CSV parser produces
    print(f"\nLoading CSV: {csv_file}")
    tour_state = load_tour_state_from_csv(csv_file, tour_format_file)
    
    print(f"Tournament state after CSV load:")
    print(f"  Current round: {tour_state.current_round.overall_round}")
    print(f"  Active players: {len(tour_state.players)}")
    
    # Check player points
    players_with_points = [p for p in tour_state.players if p.points > 0]
    print(f"  Players with points > 0: {len(players_with_points)}")
    
    # Show first 5 players' points
    print(f"\nFirst 5 players:")
    for i, player in enumerate(tour_state.players[:5]):
        print(f"  {i+1}. {player.name}: {player.points} points, {player.completed_rounds} completed rounds")
        # Check their round history
        if player.round_history:
            completed_rounds = [r for r in player.round_history if r.placement is not None]
            print(f"     Round history: {len(player.round_history)} entries, {len(completed_rounds)} with placements")
    
    # Now test cut calculation with these players
    sorted_players = sort_players_by_standing(tour_state.players)
    
    # Load tour format to see what cuts are configured
    tour_format = load_tour_format_from_json(tour_format_file)
    
    print(f"\nTour format cuts:")
    for rule in tour_format.cut_rules:
        print(f"  After round {rule.after_round}: cut to {rule.players_remaining} players")
    
    # Test what happens if we try to apply a cut now
    print(f"\nTesting cut calculation with current player state:")
    
    # Find the first cut that would apply
    current_round = tour_state.current_round.overall_round
    for rule in tour_format.cut_rules:
        if rule.after_round >= current_round - 1:  # Could be applied after completing current round
            threshold = calculate_cut_threshold(sorted_players, rule.players_remaining)
            print(f"\nCut to {rule.players_remaining} players (after round {rule.after_round}):")
            print(f"  Current players: {len(sorted_players)}")
            print(f"  Threshold: {threshold}")
            
            # Show the boundary players
            if rule.players_remaining < len(sorted_players):
                last_idx = rule.players_remaining - 1
                first_elim_idx = rule.players_remaining
                
                if last_idx >= 0 and first_elim_idx < len(sorted_players):
                    last_advancing = sorted_players[last_idx]
                    first_eliminated = sorted_players[first_elim_idx]
                    print(f"  Last advancing: {last_advancing.name} - {last_advancing.points} pts")
                    print(f"  First eliminated: {first_eliminated.name} - {first_eliminated.points} pts")
            break

def main():
    """Run all tests."""
    # Test 1: Pure logic test with mock data
    test_cut_threshold_with_zero_points()
    
    # Test 2: Test with actual CSV data
    test_csv_simulation_with_no_placements()
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    print("\nThe issue occurs when:")
    print("1. All players have 0 points (no completed rounds)")
    print("2. calculate_cut_threshold returns 0.0 when cutting from N to M players")
    print("3. This happens because when all players have equal points (0),")
    print("   the threshold calculation returns (0 + 0) / 2.0 = 0.0")
    print("\nThis causes the 'cut_to_0' label in results because the threshold is 0.0")

if __name__ == "__main__":
    main()
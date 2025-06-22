#!/usr/bin/env python3
"""Test script to verify the round duplication fix."""

import json
import tempfile
import os
from csv_to_tourstate import parse_csv_to_tourstate
from simulation import simulate_tournament, load_tour_state_from_csv
from models import TourFormat, SimSettings, SimulationMode

def create_test_csv():
    """Create a test CSV file with round 1 completed."""
    csv_content = """Current Round,2
Round Status,in_progress

Day,,1,1
Round,,1,2
Overall Round,,1,2
PlayerID,Player Name,Lobby,Placement,,Lobby,Placement,
1,Player1,A,1,,B,,
2,Player2,A,2,,B,,
3,Player3,A,3,,B,,
4,Player4,A,4,,B,,
5,Player5,A,5,,B,,
6,Player6,A,6,,B,,
7,Player7,A,7,,B,,
8,Player8,A,8,,B,,
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        return f.name

def test_round_duplication():
    """Test that round 1 placements are not duplicated in round 2."""
    print("=" * 60)
    print("TESTING ROUND DUPLICATION FIX")
    print("=" * 60)
    
    # Create test CSV
    csv_file = create_test_csv()
    print(f"Created test CSV: {csv_file}")
    
    try:
        # Convert CSV to JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
        
        parse_csv_to_tourstate(csv_file, json_file)
        print(f"Converted to JSON: {json_file}")
        
        # Load the JSON and check the data
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print("\nInitial state from CSV:")
        for player in data['players'][:3]:  # Show first 3 players
            print(f"  {player['name']}: points={player['points']}, max_csv_round={player.get('max_csv_round', 'NOT SET')}")
            for rd in player['round_history']:
                print(f"    Round {rd['overall_round']}: placement={rd['placement']}, points={rd['points']}")
        
        # Load tour state for simulation
        tour_state = load_tour_state_from_csv(csv_file)
        
        # Create minimal tour format and sim settings
        tour_format = TourFormat(total_rounds=8)
        sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
        
        # Simulate round 2
        print("\nSimulating round 2...")
        results, _ = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=True)
        
        # Check the output CSV
        output_csv = "/tmp/test_single_round_2_result.csv"
        if os.path.exists(output_csv):
            print(f"\nChecking output CSV: {output_csv}")
            
            # Read the CSV to check points
            with open(output_csv, 'r') as f:
                lines = f.readlines()
            
            print("\nRound 2 results (first few lines of CSV):")
            for i, line in enumerate(lines[:15]):
                print(f"  {line.strip()}")
            
            # Parse specific player data
            print("\nPlayer points after round 2:")
            for i in range(7, min(15, len(lines))):  # Player data starts at line 7
                parts = lines[i].strip().split(',')
                if len(parts) > 1 and parts[1]:  # Has name
                    name = parts[1]
                    # Count points from placements
                    r1_placement = parts[3] if len(parts) > 3 else ''
                    r2_placement = parts[6] if len(parts) > 6 else ''
                    
                    expected_points = 0
                    if r1_placement.isdigit():
                        expected_points += {1:8, 2:7, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1}.get(int(r1_placement), 0)
                    if r2_placement.isdigit():
                        expected_points += {1:8, 2:7, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1}.get(int(r2_placement), 0)
                    
                    print(f"  {name}: R1={r1_placement}, R2={r2_placement}, Expected points={expected_points}")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print("\nIf the fix is working correctly:")
        print("- Each player should have different placements in R1 and R2")
        print("- Points should be the sum of R1 and R2 points, not double R1 points")
        
    finally:
        # Cleanup
        if os.path.exists(csv_file):
            os.unlink(csv_file)
        if 'json_file' in locals() and os.path.exists(json_file):
            os.unlink(json_file)

if __name__ == "__main__":
    test_round_duplication()
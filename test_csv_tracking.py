#!/usr/bin/env python3
"""Simple test to verify max_csv_round tracking."""

import json
import tempfile
import os
from csv_to_tourstate import parse_csv_to_tourstate

def test_csv_tracking():
    """Test that max_csv_round is properly set when parsing CSV."""
    
    # Create a test CSV with round 1 completed and round 2 in progress
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
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_file = f.name
    
    try:
        # Parse CSV to JSON
        parse_csv_to_tourstate(csv_file, json_file)
        
        # Load and check the JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        print(f"Total players found: {len(data['players'])}")
        print("\nPlayers and their max_csv_round values:")
        for player in data['players']:
            print(f"  {player['name']}: max_csv_round={player.get('max_csv_round', 'NOT SET')}")
            print(f"    Points: {player['points']}, Total points: {player['total_points']}")
            print(f"    Round history: {len(player['round_history'])} rounds")
            for rd in player['round_history']:
                print(f"      Round {rd['overall_round']}: placement={rd.get('placement')}, points={rd.get('points')}")
        
        # Verify max_csv_round is set correctly
        for player in data['players']:
            expected_max = 1  # Round 1 has placement data
            actual_max = player.get('max_csv_round', 0)
            if actual_max != expected_max:
                print(f"\nERROR: {player['name']} has max_csv_round={actual_max}, expected {expected_max}")
            else:
                print(f"\n✓ {player['name']} correctly has max_csv_round={actual_max}")
                
    finally:
        # Cleanup
        if os.path.exists(csv_file):
            os.unlink(csv_file)
        if os.path.exists(json_file):
            os.unlink(json_file)

if __name__ == "__main__":
    test_csv_tracking()
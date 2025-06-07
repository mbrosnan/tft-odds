import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Any

def get_max_rounds(tour_state: Dict[str, Any]) -> int:
    """Determine the maximum number of rounds from all players' history."""
    max_round = 0
    for player in tour_state["players"] + tour_state["eliminated_players"]:
        for round_data in player["round_history"]:
            max_round = max(max_round, round_data["overall_round"])
    return max_round

def get_round_data(player: Dict[str, Any], round_num: int) -> tuple[str, str]:
    """Get lobby and placement for a specific round from player data."""
    for round_data in player["round_history"]:
        if round_data["overall_round"] == round_num:
            lobby = round_data["lobby"]
            placement = round_data["placement"]
            # Handle None/null placement values by returning empty string
            placement_str = "" if placement is None else str(placement)
            return lobby, placement_str
    
    # If player is eliminated, return "cut" for rounds after elimination
    if player["is_eliminated"] and player["eliminated_at"]["overall_round"] < round_num:
        return "cut", ""
    
    return "", ""  # No data for this round

def get_round_info_from_json(tour_state: Dict[str, Any], round_num: int) -> tuple[int, int]:
    """Get day and round_in_day for a specific round from the JSON data."""
    # Find this round in any player's history to get the day and round info
    for player in tour_state["players"] + tour_state["eliminated_players"]:
        for round_data in player["round_history"]:
            if round_data["overall_round"] == round_num:
                return round_data.get("day", ""), round_data.get("round_in_day", "")
    
    # If not found, return empty strings
    return "", ""

def tourstate_to_csv(input_file: str, output_file: str):
    """Convert tour_state.json to CSV format."""
    # Read JSON input
    with open(input_file, 'r', encoding='utf-8') as f:
        tour_state = json.load(f)
    
    # Initialize CSV rows
    rows = []
    
    # Add metadata rows
    current_round = tour_state["current_round"]
    rows.extend([
        ["Current Round", str(current_round["overall_round"])],
        ["Current Round Progress", current_round["round_status"].replace("_", " ").title()],
        [],  # Empty row
    ])
    
    # Create column headers based on max rounds
    max_rounds = get_max_rounds(tour_state)
    
    # Create the three header rows for day, round, and overall round
    day_header = ["Day", ""]  # Start with row label
    round_header = ["Round", ""]  # Start with row label
    overall_round_header = ["Overall Round", ""]  # Start with row label
    
    # Create the column labels row
    column_labels = ["Player ID", "Player Name"]
    
    # Add headers for each round
    for round_num in range(1, max_rounds + 1):
        # Get day and round_in_day from JSON data
        day, round_in_day = get_round_info_from_json(tour_state, round_num)
        
        # Add three columns for each round (Lobby, Placement, Spacer)
        # Day, round, and overall round should appear above both lobby and placement
        day_header.extend([str(day), str(day), ""])
        round_header.extend([str(round_in_day), str(round_in_day), ""])
        overall_round_header.extend([str(round_num), str(round_num), ""])
        column_labels.extend(["Lobby", "Placement", ""])
    
    # Add all header rows
    rows.extend([
        day_header,
        round_header,
        overall_round_header,
        column_labels
    ])
    
    # Combine and sort all players by ID
    all_players = sorted(
        tour_state["players"] + tour_state["eliminated_players"],
        key=lambda x: x["id"]
    )
    
    # Add player data rows
    for player in all_players:
        player_row = [str(player["id"]), player["name"]]
        
        # Add data for each round
        for round_num in range(1, max_rounds + 1):
            lobby, placement = get_round_data(player, round_num)
            player_row.extend([lobby, placement, ""])  # Add lobby, placement, and spacer
            
        rows.append(player_row)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description='Convert tour_state.json to TFT tournament CSV format')
    parser.add_argument('input_file', help='Path to input JSON file')
    parser.add_argument('output_file', help='Path to output CSV file')
    
    args = parser.parse_args()
    
    try:
        tourstate_to_csv(args.input_file, args.output_file)
        print(f"Successfully converted {args.input_file} to {args.output_file}")
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
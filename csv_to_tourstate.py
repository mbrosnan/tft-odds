import csv
import json
from typing import Dict, List, Optional
import argparse
from pathlib import Path

def get_points_for_placement(placement: int) -> int:
    """Convert placement to points using standard TFT scoring."""
    points_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
    return points_map.get(placement, 0)

def calculate_tiebreakers(round_history: List[Dict]) -> Dict:
    """Calculate tiebreaker statistics from round history."""
    tiebreakers = {
        "firsts": 0, "seconds": 0, "thirds": 0, "fourths": 0,
        "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 0,
        "top4s": 0
    }
    
    for round_data in round_history:
        placement = round_data.get("placement")
        if placement is None:
            continue
            
        if placement == 1: tiebreakers["firsts"] += 1
        elif placement == 2: tiebreakers["seconds"] += 1
        elif placement == 3: tiebreakers["thirds"] += 1
        elif placement == 4: tiebreakers["fourths"] += 1
        elif placement == 5: tiebreakers["fifths"] += 1
        elif placement == 6: tiebreakers["sixths"] += 1
        elif placement == 7: tiebreakers["sevenths"] += 1
        elif placement == 8: tiebreakers["eighths"] += 1
        
        if placement <= 4:
            tiebreakers["top4s"] += 1
    
    # Calculate firsts_plus_top4s (firsts count twice: once as firsts, once as top4s)
    tiebreakers["firsts_plus_top4s"] = tiebreakers["firsts"] + tiebreakers["top4s"]
            
    return tiebreakers

def validate_lobby_data(players_by_lobby: Dict[str, List], round_num: int):
    """Validate lobby data for a given round."""
    for lobby, players in players_by_lobby.items():
        if not players:
            continue
        
        # Count no-shows and active players
        no_shows = sum(1 for p in players if p.get("no_show", False))
        active_players = len(players) - no_shows
        
        # Check that we have between 1-8 total players (allowing for no-shows)
        if len(players) > 8:
            raise ValueError(f"Round {round_num}, Lobby {lobby} has {len(players)} players, maximum is 8")
        
        # For completed rounds, check placement consistency
        placements = [p["placement"] for p in players if p["placement"] is not None]
        
        # Check for duplicate placements among active players
        if len(placements) != len(set(placements)):
            raise ValueError(f"Round {round_num}, Lobby {lobby} has duplicate placements")
        
        # Check that placements are sequential from 1 to number of active players
        if placements and active_players > 0:
            expected_placements = set(range(1, active_players + 1))
            actual_placements = set(placements)
            if actual_placements != expected_placements:
                raise ValueError(f"Round {round_num}, Lobby {lobby} has invalid placements. Expected 1-{active_players}, got {sorted(actual_placements)}")

def parse_csv_to_tourstate(input_file: str, output_file: str):
    """Convert CSV tournament data to tour_state.json format."""
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = list(csv.reader(f))
        
    # Parse metadata
    current_round = int(lines[0][1])
    round_status = lines[1][1].lower().replace(" ", "_")
    
    # Parse round structure from header rows
    day_row = lines[3]  # Day header row
    round_row = lines[4]  # Round header row
    overall_round_row = lines[5]  # Overall Round header row
    
    # Get current round day and round_in_day from the current round column
    current_round_col = (current_round * 3) - 1  # Column where current round data should be
    current_day = int(day_row[current_round_col]) if current_round_col < len(day_row) and day_row[current_round_col] else -99
    current_round_in_day = int(round_row[current_round_col]) if current_round_col < len(round_row) and round_row[current_round_col] else -99
    
    player_start = 7
    
    # Initialize data structure
    tour_state = {
        "current_round": {
            "overall_round": current_round,
            "day": current_day,
            "round_in_day": current_round_in_day,
            "round_status": round_status
        },
        "players": [],
        "eliminated_players": []
    }
    
    # Process player data
    for row in lines[player_start:]:
        if not row[1]:  # Skip empty rows
            continue
            
        player_data = {
            "id": int(row[0]),  # Add player ID
            "name": row[1],
            "points": 0,
            "avg_placement": 0,
            "completed_rounds": 0,
            "round_history": [],
            "tiebreakers": {},
            "is_eliminated": False, # Initialize elimination data
            "eliminated_at": None  
        }
        
        # Process each round
        total_points = 0
        total_placement = 0
        completed_rounds = 0
        
        # Each round has 3 columns (Lobby, Placement, spacer)
        for round_num in range(1, current_round + 1):
            col_offset = (round_num * 3) - 1  # Starting column for round data
            
            lobby = row[col_offset]
            placement_str = row[col_offset + 1]
            
            # Check for cut marker
            if lobby.lower() == 'cut':
                player_data["is_eliminated"] = True
                player_data["eliminated_at"] = {
                    "overall_round": round_num - 1,  # Cut means eliminated after previous round
                    "reason": "cut"
                }
                continue

            # Skip if no lobby data for this round
            if not lobby:
                continue
                
            # Get day and round_in_day from header rows
            day = int(day_row[col_offset]) if col_offset < len(day_row) and day_row[col_offset] else 1
            round_in_day = int(round_row[col_offset]) if col_offset < len(round_row) and round_row[col_offset] else 1
            
            # Handle in-progress rounds (lobby exists but no placement)
            if not placement_str:
                round_data = {
                    "overall_round": round_num,
                    "day": day,
                    "round_in_day": round_in_day,
                    "lobby": lobby,
                    "placement": None,
                    "points": None,
                    "no_show": False
                }
                player_data["round_history"].append(round_data)
                continue
            
            # Handle no-show entries
            if placement_str.lower() == "no-show":
                round_data = {
                    "overall_round": round_num,
                    "day": day,
                    "round_in_day": round_in_day,
                    "lobby": lobby,
                    "placement": None,
                    "points": 0,
                    "no_show": True
                }
                player_data["round_history"].append(round_data)
                continue
                
            try:
                placement = int(placement_str)
                points = get_points_for_placement(placement)
                total_points += points
                total_placement += placement
                completed_rounds += 1
                
                round_data = {
                    "overall_round": round_num,
                    "day": day,
                    "round_in_day": round_in_day,
                    "lobby": lobby,
                    "placement": placement,
                    "points": points,
                    "no_show": False
                }
                player_data["round_history"].append(round_data)
                
            except ValueError:
                continue
        
        if completed_rounds > 0 or any(rd.get("no_show", False) for rd in player_data["round_history"]):
            player_data["points"] = total_points
            player_data["avg_placement"] = round(total_placement / completed_rounds, 2) if completed_rounds > 0 else 0.0
            player_data["completed_rounds"] = completed_rounds
            player_data["tiebreakers"] = calculate_tiebreakers(player_data["round_history"])
            
            # Add to appropriate list (active or eliminated)
            if player_data["is_eliminated"]:
                tour_state["eliminated_players"].append(player_data)
            else:
                tour_state["players"].append(player_data)
    
    # Validate lobby data for completed rounds
    for round_num in range(1, current_round):
        players_by_lobby = {}
        for player in tour_state["players"] + tour_state["eliminated_players"]:
            for round_data in player["round_history"]:
                if round_data["overall_round"] == round_num:
                    lobby = round_data["lobby"]
                    if lobby not in players_by_lobby:
                        players_by_lobby[lobby] = []
                    players_by_lobby[lobby].append(round_data)
        validate_lobby_data(players_by_lobby, round_num)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tour_state, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Convert TFT tournament CSV data to tour_state.json format')
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('output_file', help='Path to output JSON file')
    
    args = parser.parse_args()
    
    try:
        parse_csv_to_tourstate(args.input_file, args.output_file)
        print(f"Successfully converted {args.input_file} to {args.output_file}")
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
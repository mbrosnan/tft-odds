import csv
import json
from typing import Dict, List, Optional
import argparse
from pathlib import Path

def load_tour_format(tour_format_file: str) -> Optional[Dict]:
    """Load tour format from JSON file."""
    try:
        with open(tour_format_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load tour format file {tour_format_file}: {e}")
        return None

def get_point_reset_rounds(tour_format: Dict) -> List[int]:
    """Get list of rounds after which points are reset."""
    reset_rounds = []
    
    if not tour_format or 'round_structure' not in tour_format:
        return reset_rounds
    
    for round_info in tour_format['round_structure']:
        if round_info.get('post_round_actions', {}).get('point_reset', False):
            reset_rounds.append(round_info['overall_round'])
    
    return reset_rounds

def calculate_points_with_resets(round_history: List[Dict], reset_rounds: List[int], current_round: int = None) -> tuple[int, int]:
    """Calculate current points and total points, accounting for point resets.
    
    Args:
        round_history: List of round data for the player
        reset_rounds: List of rounds after which points are reset
        current_round: Current tournament round (used to determine which resets have occurred)
    
    Returns:
        tuple: (current_points, total_points)
        - current_points: Points since last reset (or all points if no resets)
        - total_points: All points accumulated (survives resets)
    """
    if not reset_rounds:
        # No resets - both values are the same
        total_points = sum(rd.get("points", 0) for rd in round_history if rd.get("points") is not None)
        return total_points, total_points
    
    # Calculate total_points (all points from all rounds)
    total_points = sum(rd.get("points", 0) for rd in round_history if rd.get("points") is not None)
    
    # If no current_round provided, fall back to player's max completed round
    if current_round is None:
        completed_rounds = [rd["overall_round"] for rd in round_history if rd.get("points") is not None]
        if not completed_rounds:
            return 0, 0
        current_round = max(completed_rounds)
    
    # Find the most recent reset that has occurred based on current tournament round
    applicable_resets = [r for r in reset_rounds if r < current_round]
    
    if not applicable_resets:
        # No resets have occurred yet
        return total_points, total_points
    
    # Most recent reset round
    last_reset_round = max(applicable_resets)
    
    # Calculate current_points (only points after the last reset)
    current_points = sum(
        rd.get("points", 0) for rd in round_history 
        if rd.get("points") is not None and rd["overall_round"] > last_reset_round
    )
    
    return current_points, total_points

def get_points_for_placement(placement: int) -> int:
    """Convert placement to points using standard TFT scoring."""
    points_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
    return points_map.get(placement, 0)

def calculate_tiebreakers(round_history: List[Dict], reset_rounds: List[int] = None, current_round: int = None) -> Dict:
    """Calculate tiebreaker statistics from round history."""
    tiebreakers = {
        "firsts": 0, "seconds": 0, "thirds": 0, "fourths": 0,
        "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 0,
        "top4s": 0, "total_points": 0
    }
    
    # Calculate total_points using reset-aware function
    if reset_rounds is None:
        reset_rounds = []
    
    _, total_points = calculate_points_with_resets(round_history, reset_rounds, current_round)
    
    for round_data in round_history:
        placement = round_data.get("placement")
        points = round_data.get("points", 0)
            
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
    
    # Set total_points tiebreaker (survives resets)
    tiebreakers["total_points"] = total_points
            
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
        
        # More flexible placement validation - check if placements make sense
        if placements and active_players > 0:
            min_placement = min(placements)
            max_placement = max(placements)
            
            # Check if placements start from 1
            if min_placement != 1:
                print(f"Warning: Round {round_num}, Lobby {lobby} placements don't start from 1. Min placement: {min_placement}")
            
            # Check if max placement is reasonable (allow some flexibility)
            if max_placement > len(players):
                print(f"Warning: Round {round_num}, Lobby {lobby} has placement {max_placement} but only {len(players)} total players")
                print(f"  Active players: {active_players}, No-shows: {no_shows}")
                print(f"  All placements: {sorted(placements)}")
                
                # Only raise error if the placement is extremely unreasonable (more than 9)
                if max_placement > 9:
                    raise ValueError(f"Round {round_num}, Lobby {lobby} has invalid placement {max_placement} (too high)")
            
            # Check if we have the expected number of placements for active players
            if len(placements) != active_players:
                print(f"Warning: Round {round_num}, Lobby {lobby} has {len(placements)} placements but {active_players} active players")
                print(f"  Placements: {sorted(placements)}")
                print(f"  Player details: {[(p.get('placement', 'None'), p.get('no_show', False)) for p in players]}")
            
            # Only enforce strict sequential validation if placements look normal (1-8 range)
            if max_placement <= 8 and min_placement == 1:
                expected_placements = set(range(1, active_players + 1))
                actual_placements = set(placements)
                if actual_placements != expected_placements:
                    print(f"Warning: Round {round_num}, Lobby {lobby} has non-sequential placements")
                    print(f"  Expected: {sorted(expected_placements)}")
                    print(f"  Actual: {sorted(actual_placements)}")
                    print(f"  Missing: {sorted(expected_placements - actual_placements)}")
                    print(f"  Extra: {sorted(actual_placements - expected_placements)}")
                    
                    # Convert to warning instead of error for now
                    # raise ValueError(f"Round {round_num}, Lobby {lobby} has invalid placements. Expected 1-{active_players}, got {sorted(actual_placements)}")

def parse_csv_to_tourstate(input_file: str, output_file: str, tour_format_file: str = None):
    """Convert CSV tournament data to tour_state.json format.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output JSON file  
        tour_format_file: Optional path to tour format JSON file for point reset handling
    """
    # Load tour format if provided
    tour_format = None
    reset_rounds = []
    if tour_format_file:
        tour_format = load_tour_format(tour_format_file)
        if tour_format:
            reset_rounds = get_point_reset_rounds(tour_format)
            if reset_rounds:
                print(f"Detected point resets after rounds: {reset_rounds}")
    
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
            "total_points": 0,  # Initialize total_points
            "avg_placement": 0,
            "completed_rounds": 0,
            "round_history": [],
            "tiebreakers": {},
            "is_eliminated": False, # Initialize elimination data
            "eliminated_at": None  
        }
        
        # Process each round to build round history first
        total_placement = 0
        completed_rounds = 0
        
        # Each round has 3 columns (Lobby, Placement, spacer)
        for round_num in range(1, current_round + 1):
            col_offset = (round_num * 3) - 1  # Starting column for round data
            
            lobby = row[col_offset]
            placement_str = row[col_offset + 1]
            
            # Check for cut marker - this means player was eliminated before this round
            if lobby.lower() == 'cut':
                player_data["is_eliminated"] = True
                player_data["eliminated_at"] = {
                    "overall_round": round_num,  # Eliminated before this round starts
                    "reason": "cut"
                }
                break  # Stop processing once we find the first cut

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
        
        # Calculate points using reset-aware logic
        if completed_rounds > 0 or any(rd.get("no_show", False) for rd in player_data["round_history"]):
            current_points, total_points = calculate_points_with_resets(player_data["round_history"], reset_rounds, current_round)
            
            player_data["points"] = current_points
            player_data["total_points"] = total_points
            player_data["avg_placement"] = round(total_placement / completed_rounds, 2) if completed_rounds > 0 else 0.0
            player_data["completed_rounds"] = completed_rounds
            player_data["tiebreakers"] = calculate_tiebreakers(player_data["round_history"], reset_rounds, current_round)
            
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
    parser.add_argument('--tour-format', help='Path to tour format JSON file for point reset handling')
    
    args = parser.parse_args()
    
    try:
        parse_csv_to_tourstate(args.input_file, args.output_file, args.tour_format)
        print(f"Successfully converted {args.input_file} to {args.output_file}")
        if args.tour_format:
            print(f"Used tour format: {args.tour_format}")
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
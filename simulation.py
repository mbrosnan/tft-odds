import time
import random
import os
import tempfile
import json
import argparse
from typing import Dict, List, Set
from models import TourFormat, TourState, SimSettings, SimulationMode, CutRule, RoundHistory, RoundStatus, EliminatedAt, Player, Tiebreakers, CurrentRound, PostRoundActions, RoundStructure, ProbabilityTarget
from utils import load_tour_state_from_json, save_results_to_json, save_json, load_tour_format_from_json
from tourstate_to_csv import tourstate_to_csv, pydantic_tourstate_to_csv
from csv_to_tourstate import parse_csv_to_tourstate

# Simulation Functions

def mark_player_no_show(tour_state: TourState, player_id: int, round_num: int):
    """Mark a player as no-show for a specific round."""
    # Find the player
    for player in tour_state.players:
        if player.id == player_id:
            # Find the round entry
            for round_entry in player.round_history:
                if round_entry.overall_round == round_num:
                    round_entry.no_show = True
                    round_entry.placement = None
                    round_entry.points = 0
                    return True
    return False

def get_lobby_stats(lobby_players: List) -> Dict[str, int]:
    """Get statistics about a lobby (total, active, no-shows)."""
    total_players = len(lobby_players)
    no_shows = sum(1 for _, round_entry in lobby_players if round_entry.no_show)
    active_players = total_players - no_shows
    
    return {
        "total": total_players,
        "active": active_players, 
        "no_shows": no_shows
    }

def get_points_for_placement(placement: int, lobby_size: int = 8) -> int:
    """Convert placement to points using standard TFT scoring.
    For no-show scenarios:
    - No-show players get 0 points
    - Active players get points 8-2 (1st gets 8, 2nd gets 7, etc.)
    """
    if placement is None:  # No-show case
        return 0
    
    # Standard 8-player scoring, regardless of actual lobby size
    points_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
    return points_map.get(placement, 0)

def calculate_tiebreakers(round_history: List[RoundHistory]) -> Dict[str, int]:
    """Calculate tiebreaker statistics from round history."""
    tiebreakers = {
        "firsts": 0, "seconds": 0, "thirds": 0, "fourths": 0,
        "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 0,
        "top4s": 0, "total_points": 0
    }
    
    total_points = 0
    for round_data in round_history:
        # Add points to total_points
        if round_data.points:
            total_points += round_data.points
            
        # Skip if no placement (in-progress or no-show)
        if round_data.placement is None:
            continue
            
        placement = round_data.placement
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
    
    # Set total_points tiebreaker
    tiebreakers["total_points"] = total_points
    
    return tiebreakers

def update_player_stats(player, round_history: List[RoundHistory]):
    """Update player statistics based on round history."""
    # Calculate total_points (all points from all rounds - survives resets)
    total_points = sum(rd.points for rd in round_history if rd.points is not None)
    
    # Handle current_points and total_points logic
    # If player already has points/total_points from CSV parsing, preserve them and only add new simulation points
    if hasattr(player, 'points') and hasattr(player, 'total_points'):
        # Player has existing values from CSV parsing - preserve them
        existing_current_points = player.points
        existing_total_points = player.total_points
        
        # Calculate points from simulation rounds only
        # Find the highest round number that existed before simulation
        max_existing_round = 0
        if hasattr(player, '_max_csv_round'):
            max_existing_round = player._max_csv_round
        else:
            # Fallback: assume current round - 1 was the last CSV round
            # This works for single-round simulations
            current_round = max((rd.overall_round for rd in round_history), default=0)
            max_existing_round = current_round - 1
        
        # Calculate points from new simulation rounds only
        new_simulation_points = sum(
            rd.points for rd in round_history 
            if rd.points is not None and rd.overall_round > max_existing_round
        )
        
        # Add simulation points to both current and total
        current_points = existing_current_points + new_simulation_points
        total_points = existing_total_points + new_simulation_points
        

    else:
        # No existing values - calculate from scratch (no reset scenario)
        current_points = total_points
    
    # Calculate placement stats
    total_placement = 0
    completed_rounds = 0
    for round_data in round_history:
        if round_data.placement is not None:
            total_placement += round_data.placement
            completed_rounds += 1
    
    player.points = current_points
    player.total_points = total_points
    player.avg_placement = round(total_placement / completed_rounds, 2) if completed_rounds > 0 else 0.0
    player.completed_rounds = completed_rounds
    
    # Calculate tiebreakers
    tiebreakers = calculate_tiebreakers(round_history)
    
    # Update tiebreakers - handle both dict and object formats
    if hasattr(player.tiebreakers, 'firsts'):
        # Pydantic object format
        player.tiebreakers.firsts = tiebreakers['firsts']
        player.tiebreakers.seconds = tiebreakers['seconds']
        player.tiebreakers.thirds = tiebreakers['thirds']
        player.tiebreakers.fourths = tiebreakers['fourths']
        player.tiebreakers.fifths = tiebreakers['fifths']
        player.tiebreakers.sixths = tiebreakers['sixths']
        player.tiebreakers.sevenths = tiebreakers['sevenths']
        player.tiebreakers.eighths = tiebreakers['eighths']
        player.tiebreakers.top4s = tiebreakers['top4s']
        player.tiebreakers.firsts_plus_top4s = tiebreakers['firsts_plus_top4s']
        player.tiebreakers.total_points = player.total_points  # Sync total_points tiebreaker
    else:
        # Dict format
        player.tiebreakers.update(tiebreakers)
        player.tiebreakers['total_points'] = player.total_points

def initialize_results(tour_format: TourFormat) -> Dict:
    """Initialize results structure based on what we're tracking."""
    results = {}
    
    if tour_format.track_placement_probabilities:
        results["placement_probabilities"] = {}
    
    if tour_format.track_points_distribution:
        results["points_distribution"] = {}
        
    if tour_format.track_elimination_probabilities:
        results["elimination_probabilities"] = {}
    
    return results

def validate_and_load_state(tour_state: TourState) -> TourState:
    """Step 1: Validate and load the tournament state."""
    # Create a deep copy for this simulation run
    return tour_state.model_copy(deep=True)

def simulate_next_round(current_state: TourState, tour_format: TourFormat) -> TourState:
    """Step 2: Simulate the next round or finish an in-progress round."""
    current_round_num = current_state.current_round.overall_round
    
    # Group players by lobby for the current round
    lobbies = {}
    
    # Check all active players for current round assignments
    for player in current_state.players:
        # Find this player's entry for the current round
        current_round_entry = None
        for round_data in player.round_history:
            if round_data.overall_round == current_round_num:
                current_round_entry = round_data
                break
        
        if current_round_entry and current_round_entry.lobby:
            lobby = current_round_entry.lobby
            if lobby not in lobbies:
                lobbies[lobby] = []
            lobbies[lobby].append((player, current_round_entry))
    
    # Simulate each lobby
    for lobby_name, lobby_players in lobbies.items():
        # Get lobby statistics
        lobby_stats = get_lobby_stats(lobby_players)
        
        # Find which placements are already assigned and separate no-shows
        taken_placements: Set[int] = set()
        unplaced_players = []
        no_show_players = []
        
        for player, round_entry in lobby_players:
            if round_entry.no_show:
                # Handle no-show: 0 points, no placement
                round_entry.placement = None
                round_entry.points = 0
                no_show_players.append((player, round_entry))
            elif round_entry.placement is not None:
                taken_placements.add(round_entry.placement)
            else:
                unplaced_players.append((player, round_entry))
        
        # Calculate available placements based on active players
        active_players_count = len(lobby_players) - len(no_show_players)
        
        if active_players_count > 0:
            # Available placements are 1 through active_players_count
            all_placements = set(range(1, active_players_count + 1))
            available_placements = list(all_placements - taken_placements)
            
            # Randomly assign remaining placements
            if unplaced_players and available_placements:
                random.shuffle(available_placements)
                
                for i, (player, round_entry) in enumerate(unplaced_players):
                    if i < len(available_placements):
                        placement = available_placements[i]
                        # Calculate points using standard 8-player scoring
                        points = get_points_for_placement(placement)
                        
                        # Update the round entry
                        round_entry.placement = placement
                        round_entry.points = points
        
    # Update all player stats after round completion
    for player in current_state.players:
        update_player_stats(player, player.round_history)
    
    # Mark current round as completed.  DO NOT advance to the next round.  that will be a separate item.
    current_state.current_round.round_status = RoundStatus.COMPLETED

    
    return current_state

def process_post_round_actions(current_state: TourState, tour_format: TourFormat, results: Dict = None) -> tuple[TourState, Dict[int, List]]:
    """Step 3: Handle cuts, shuffles, and other post-round actions."""
    completed_round = current_state.current_round.overall_round  # The round we just finished
    cut_history = {}  # Track cuts that happen in this function
    
    # Step 3a: Check for victory conditions first
    if check_victory_conditions(current_state, tour_format, completed_round):
        # Tournament ends early due to victory condition
        # Mark tournament as complete by setting round beyond total
        current_state.current_round.overall_round = tour_format.total_rounds + 1
        current_state.current_round.round_status = RoundStatus.COMPLETED
        return current_state, cut_history
    
    # Step 3b: Apply cuts if there are any for this round (BEFORE checking end_tournament)
    players_before_cut = current_state.players.copy()  # Save players before cut
    current_state, cut_threshold = apply_cuts(current_state, tour_format, completed_round)
    
    # Track cut history if a cut was applied
    if len(current_state.players) < len(players_before_cut):
        # A cut happened - record which players survived
        cut_history[len(current_state.players)] = current_state.players.copy()
    
    # Step 3c: Store cut threshold data if we have one and results dict
    if cut_threshold is not None and results is not None:
        if "cut_thresholds" not in results:
            results["cut_thresholds"] = {}
        
        cut_name = f"round_{completed_round}_cut_to_{len(current_state.players)}"
        if cut_name not in results["cut_thresholds"]:
            results["cut_thresholds"][cut_name] = []
        
        results["cut_thresholds"][cut_name].append(cut_threshold)
    
    # Step 3d: Check if tournament should end after this round (AFTER processing cuts)
    if tour_format.round_structure:
        for round_info in tour_format.round_structure:
            if round_info.overall_round == completed_round:
                if round_info.post_round_actions.end_tournament:
                    # Tournament ends after this round - mark as complete
                    current_state.current_round.overall_round = tour_format.total_rounds + 1
                    current_state.current_round.round_status = RoundStatus.COMPLETED
                    return current_state, cut_history
                break
    
    # Step 3e: Advance to next round (only if tournament is continuing)
    current_state = advance_to_next_round(current_state, tour_format)
    
    # Step 3f: Determine shuffle type for next round
    shuffle_type = get_shuffle_type_for_round(tour_format, completed_round)
    
    # Step 3g: Assign lobbies for the next round (if not tournament complete)
    if not is_tournament_complete(current_state, tour_format):
        current_state = assign_next_round_lobbies(current_state, tour_format, shuffle_type=shuffle_type)
    
    # Step 3h: Handle point reset if specified (LAST action after cuts, shuffles, etc.)
    if tour_format.round_structure:
        for round_info in tour_format.round_structure:
            if round_info.overall_round == completed_round:
                if round_info.post_round_actions.point_reset:
                    # Reset points and tiebreakers for ALL players (active AND eliminated)
                    # total_points is NOT reset - it survives the reset
                    all_players = current_state.players + current_state.eliminated_players
                    
                    print(f"DEBUG: Point reset triggered after round {completed_round}")
                    print(f"DEBUG: Before reset - first 3 players:")
                    for i, player in enumerate(current_state.players[:3]):
                        print(f"  {player.name}: points={player.points}, total_points={player.total_points}")
                    
                    for player in all_players:
                        old_points = player.points  # Capture old points before reset
                        player.points = 0
                        
                        # Reset all tiebreakers to 0 except total_points
                        if hasattr(player.tiebreakers, 'firsts'):
                            # Pydantic object format
                            player.tiebreakers.firsts = 0
                            player.tiebreakers.seconds = 0
                            player.tiebreakers.thirds = 0
                            player.tiebreakers.fourths = 0
                            player.tiebreakers.fifths = 0
                            player.tiebreakers.sixths = 0
                            player.tiebreakers.sevenths = 0
                            player.tiebreakers.eighths = 0
                            player.tiebreakers.top4s = 0
                            player.tiebreakers.firsts_plus_top4s = 0
                            # total_points tiebreaker is NOT reset
                        else:
                            # Dict format
                            total_points_value = player.tiebreakers.get('total_points', 0)
                            player.tiebreakers = {
                                'firsts': 0, 'seconds': 0, 'thirds': 0, 'fourths': 0,
                                'fifths': 0, 'sixths': 0, 'sevenths': 0, 'eighths': 0,
                                'top4s': 0, 'firsts_plus_top4s': 0,
                                'total_points': total_points_value  # Preserve total_points
                            }
                        
                        if old_points > 0:  # Only print for players who had points
                            print(f"DEBUG: Reset {player.name}: {old_points} -> 0 points (total_points: {player.total_points})")
                    
                    print(f"DEBUG: Point reset complete for round {completed_round}")
                break
    
    return current_state, cut_history

def get_shuffle_type_for_round(tour_format: TourFormat, completed_round: int) -> str:
    """Determine what type of shuffle to use based on the tour format."""
    # Check if we have round structure information
    if tour_format.round_structure:
        for round_info in tour_format.round_structure:
            if round_info.overall_round == completed_round:
                post_actions = round_info.post_round_actions
                
                if post_actions.snake_shuffle:
                    return "snake"
                elif post_actions.random_shuffle:
                    return "random"
                else:
                    # No explicit shuffle specified, default to random
                    return "random"
    
    # Fallback: if no round structure or round not found, use random
    return "random"

def calculate_cut_threshold(sorted_players: List, players_remaining: int) -> float:
    """Calculate the cut threshold, using whole numbers for tiebreakers and half numbers for clean cuts."""
    if players_remaining >= len(sorted_players):
        return 0.0  # No cut needed
    
    # Get the last player who advances and first player who gets eliminated
    last_advancing_player = sorted_players[players_remaining - 1]
    first_eliminated_player = sorted_players[players_remaining]
    
    last_advancing_points = last_advancing_player.points
    first_eliminated_points = first_eliminated_player.points
    
    if last_advancing_points == first_eliminated_points:
        # Tiebreaker situation - use whole number
        return float(last_advancing_points)
    else:
        # Clean cut - use half number between the two point values
        return (last_advancing_points + first_eliminated_points) / 2.0

def apply_cuts(current_state: TourState, tour_format: TourFormat, completed_round: int) -> tuple[TourState, float]:
    """Apply elimination cuts based on tour format rules. Returns updated state and cut threshold."""
    # Find if there's a cut rule for this round
    cut_rule = None
    for rule in tour_format.cut_rules:
        if rule.after_round == completed_round:
            cut_rule = rule
            break
    
    if not cut_rule:
        # print(f"No cuts after round {completed_round}")
        return current_state, None
    
    # print(f"Applying cut: {len(current_state.players)} -> {cut_rule.players_remaining} players")
    
    # Sort players by tournament standing (points desc, then tiebreakers)
    sorted_players = sort_players_by_standing(current_state.players)
    
    # Calculate cut threshold
    cut_threshold = calculate_cut_threshold(sorted_players, cut_rule.players_remaining)
    
    # Keep top N players, eliminate the rest
    players_to_keep = sorted_players[:cut_rule.players_remaining]
    players_to_eliminate = sorted_players[cut_rule.players_remaining:]
    
    # print(f"\nPlayers advancing to next round:")
    # for player in players_to_keep:
    #     print(f"  ✓ {player.name} ({player.points} points)")
    
    # print(f"\nPlayers eliminated:")
    next_round = completed_round + 1
    # Mark eliminated players and add "cut" round entry for next round
    for player in players_to_eliminate:
        player.is_eliminated = True
        player.eliminated_at = EliminatedAt(
            overall_round=next_round,  # Eliminated before next round
            reason=f"Cut after round {completed_round}"
        )
        
        # Add a "cut" lobby entry for the next round to show they were eliminated
        cut_round_entry = RoundHistory(
            overall_round=next_round,
            day=current_state.current_round.day,  # Use current day info
            round_in_day=current_state.current_round.round_in_day + 1,  # Next round in day
            lobby="cut",
            placement=None,
            points=None,
            no_show=False
        )
        player.round_history.append(cut_round_entry)
        
        # print(f"  ✗ {player.name} ({player.points} points)")
    
    # Update current state
    current_state.players = players_to_keep
    current_state.eliminated_players.extend(players_to_eliminate)
    
    # print(f"\nCut complete: {len(current_state.players)} players remaining")
    return current_state, cut_threshold

def sort_players_by_standing(players: List) -> List:
    """Sort players by tournament standing (points desc, then tiebreakers)."""
    def standing_key(player):
        # Primary: points (descending)
        # Secondary: tiebreakers in the correct order
        tb = player.tiebreakers
        if isinstance(tb, dict):
            # Handle dict format
            firsts = tb.get('firsts', 0)
            seconds = tb.get('seconds', 0) 
            thirds = tb.get('thirds', 0)
            fourths = tb.get('fourths', 0)
            fifths = tb.get('fifths', 0)
            sixths = tb.get('sixths', 0)
            sevenths = tb.get('sevenths', 0)
            eighths = tb.get('eighths', 0)
            top4s = tb.get('top4s', 0)
            firsts_plus_top4s = tb.get('firsts_plus_top4s', 0)
            total_points = tb.get('total_points', 0)
        else:
            # Handle Pydantic object
            firsts = tb.firsts
            seconds = tb.seconds
            thirds = tb.thirds
            fourths = tb.fourths
            fifths = tb.fifths
            sixths = tb.sixths
            sevenths = tb.sevenths
            eighths = tb.eighths
            top4s = tb.top4s
            firsts_plus_top4s = tb.firsts_plus_top4s
            total_points = getattr(tb, 'total_points', 0)
        
        # Follow the correct tiebreaker order:
        # 1. points (current points)
        # 2. total_points (survives resets)
        # 3. firsts_plus_top4s
        # 4. firsts
        # 5. seconds
        # 6. thirds
        # 7. fourths
        # 8. fifths
        # 9. sixths
        # 10. sevenths
        # 11. eighths
        # 12. average placement (lower is better)
        return (
            -player.points,              # Higher current points = better (negative for desc)
            -total_points,               # Higher total_points = better (survives resets)
            -firsts_plus_top4s,          # More firsts_plus_top4s = better
            -firsts,                     # More firsts = better
            -seconds,                    # More seconds = better
            -thirds,                     # More thirds = better
            -fourths,                    # More fourths = better
            -fifths,                     # More fifths = better
            -sixths,                     # More sixths = better
            -sevenths,                   # More sevenths = better
            -eighths,                    # More eighths = better
            player.avg_placement,        # Lower avg placement = better
        )
    
    return sorted(players, key=standing_key)

def advance_to_next_round(current_state: TourState, tour_format: TourFormat) -> TourState:
    """Advance the tournament to the next round."""
    # Increment round counter
    current_state.current_round.overall_round += 1
    
    # Update round status
    if current_state.current_round.overall_round <= tour_format.total_rounds:
        current_state.current_round.round_status = RoundStatus.NOT_STARTED
    
    # TODO: Implement proper day/round_in_day logic based on tournament format
    # For now, just increment round_in_day
    current_state.current_round.round_in_day += 1
    
    # print(f"Advanced to round {current_state.current_round.overall_round}")
    return current_state

def assign_next_round_lobbies(current_state: TourState, tour_format: TourFormat, players_per_lobby: int = 8, shuffle_type: str = "random") -> TourState:
    """Assign players to lobbies for the next round."""
    next_round = current_state.current_round.overall_round
    remaining_players = current_state.players.copy()
    
    # print(f"Assigning lobbies for round {next_round} with {len(remaining_players)} players using {shuffle_type} shuffle")
    
    # Choose assignment strategy based on shuffle type
    if shuffle_type == "snake":
        lobby_assignments = assign_lobbies_snake_shuffle(remaining_players, players_per_lobby)
    elif shuffle_type == "random":
        lobby_assignments = assign_lobbies_random_shuffle(remaining_players, players_per_lobby)
    else:
        # print(f"Warning: Unknown shuffle type '{shuffle_type}', defaulting to random")
        lobby_assignments = assign_lobbies_random_shuffle(remaining_players, players_per_lobby)
    
    # Add round history entries for each player
    for lobby_name, lobby_players in lobby_assignments.items():
        # print(f"  Lobby {lobby_name}: {[p.name for p in lobby_players]}")
        
        for player in lobby_players:
            # Add new round entry
            new_round = RoundHistory(
                overall_round=next_round,
                day=current_state.current_round.day,
                round_in_day=current_state.current_round.round_in_day,
                lobby=lobby_name,
                placement=None,  # To be filled during simulation
                points=None,     # To be filled during simulation
                no_show=False
            )
            player.round_history.append(new_round)
    
    return current_state

def generate_lobby_name(index: int) -> str:
    """Generate lobby name for given index. Handles more than 26 lobbies gracefully.
    
    Examples:
    0 -> "A", 1 -> "B", ..., 25 -> "Z"
    26 -> "AA", 27 -> "AB", ..., 51 -> "AZ"
    52 -> "BA", 53 -> "BB", etc.
    """
    if index < 26:
        # Single letter: A-Z
        return chr(ord('A') + index)
    else:
        # Multiple letters: AA, AB, AC, etc.
        # This creates Excel-style column naming
        result = ""
        temp_index = index
        while temp_index >= 0:
            result = chr(ord('A') + (temp_index % 26)) + result
            temp_index = temp_index // 26 - 1
            if temp_index < 0:
                break
        return result

def assign_lobbies_snake_shuffle(players: List, players_per_lobby: int = 8) -> Dict[str, List]:
    """Assign players to lobbies using snake shuffle (balanced by standings)."""
    # Sort players by current standings
    sorted_players = sort_players_by_standing(players)
    
    # Calculate number of lobbies needed
    num_lobbies = (len(sorted_players) + players_per_lobby - 1) // players_per_lobby
    
    # Initialize lobbies
    lobbies = {}
    for i in range(num_lobbies):
        lobby_name = generate_lobby_name(i)
        lobbies[lobby_name] = []
    
    # Snake distribution
    lobby_names = list(lobbies.keys())
    
    for i, player in enumerate(sorted_players):
        # Calculate which lobby using snake pattern
        cycle_position = i // num_lobbies  # Which "round" of the snake we're in
        lobby_index = i % num_lobbies      # Position within this round
        
        # Snake pattern: alternate direction each cycle
        if cycle_position % 2 == 0:
            # Forward direction: A, B, C, D
            chosen_lobby = lobby_names[lobby_index]
        else:
            # Reverse direction: D, C, B, A
            chosen_lobby = lobby_names[num_lobbies - 1 - lobby_index]
        
        lobbies[chosen_lobby].append(player)
    
    # Show snake pattern for debugging
    # print(f"  Snake shuffle pattern (by standings):")
    # for i, player in enumerate(sorted_players):
    #     print(f"    {i+1}. {player.name} ({player.points} pts)")
    
    return lobbies

def assign_lobbies_random_shuffle(players: List, players_per_lobby: int = 8) -> Dict[str, List]:
    """Assign players to lobbies using random shuffle."""
    # Shuffle players randomly
    shuffled_players = players.copy()
    random.shuffle(shuffled_players)
    
    # Create lobbies
    lobbies = {}
    lobby_count = 0
    
    for i in range(0, len(shuffled_players), players_per_lobby):
        lobby_name = generate_lobby_name(lobby_count)
        lobby_players = shuffled_players[i:i + players_per_lobby]
        lobbies[lobby_name] = lobby_players
        lobby_count += 1
    
    return lobbies

def record_simulation_data(current_state: TourState, results: Dict, tour_format: TourFormat):
    """Step 4: Record relevant data during the simulation."""
    # TODO: Implement data recording
    pass

def filter_future_probability_targets(probability_targets: List[ProbabilityTarget], current_round: int, tour_format: TourFormat) -> List[ProbabilityTarget]:
    """Filter probability targets to only include future events (cuts that haven't happened yet).
    
    Args:
        probability_targets: List of all probability targets
        current_round: Current tournament round
        tour_format: Tournament format with cut rules
        
    Returns:
        List of probability targets for events that haven't occurred yet
    """
    if not probability_targets:
        return []
    
    # Get all cut rounds that have already occurred
    past_cut_rounds = []
    
    # Check round_structure format first
    if tour_format.round_structure:
        for round_info in tour_format.round_structure:
            if (round_info.post_round_actions.cut and 
                round_info.overall_round < current_round):
                past_cut_rounds.append(round_info.overall_round)
    
    # Fallback to old cut_rules format
    elif hasattr(tour_format, 'cut_rules') and tour_format.cut_rules:
        for cut_rule in tour_format.cut_rules:
            if cut_rule.after_round < current_round:
                past_cut_rounds.append(cut_rule.after_round)
    
    # Filter out probability targets for past cuts
    future_targets = []
    for target in probability_targets:
        if target.type == "made_cut":
            # Find which cut round this target corresponds to
            target_cut_round = None
            
            # Check round_structure format first
            if tour_format.round_structure:
                for round_info in tour_format.round_structure:
                    if (round_info.post_round_actions.cut and 
                        round_info.post_round_actions.cut_to == target.players_remaining):
                        target_cut_round = round_info.overall_round
                        break
            
            # Fallback to old cut_rules format
            if target_cut_round is None and hasattr(tour_format, 'cut_rules') and tour_format.cut_rules:
                for cut_rule in tour_format.cut_rules:
                    if cut_rule.players_remaining == target.players_remaining:
                        target_cut_round = cut_rule.after_round
                        break
            
            # Only include if this cut hasn't happened yet
            if target_cut_round is None or target_cut_round >= current_round:
                future_targets.append(target)
        else:
            # Non-cut targets (tournament winner, final standings) are always future
            future_targets.append(target)
    
    return future_targets

def evaluate_past_cut_probabilities(tour_state: TourState, tour_format: TourFormat, probability_targets: List[ProbabilityTarget]) -> Dict[str, Dict[str, float]]:
    """Evaluate probabilities for cuts that have already occurred.
    
    For past cuts:
    - Players who made the cut: 100% probability
    - Players who didn't make the cut: 0% probability
    """
    past_probabilities = {}
    current_round = tour_state.current_round.overall_round
    
    # Get all players (active + eliminated)
    all_players = tour_state.players + tour_state.eliminated_players
    
    for target in probability_targets:
        if target.type != "made_cut":
            continue
            
        # Find which cut round this target corresponds to using round_structure
        target_cut_round = None
        if tour_format.round_structure:
            for round_info in tour_format.round_structure:
                if (round_info.post_round_actions.cut and 
                    round_info.post_round_actions.cut_to == target.players_remaining):
                    target_cut_round = round_info.overall_round
                    break
        
        # Fallback to old cut_rules format if round_structure doesn't have the info
        if target_cut_round is None and hasattr(tour_format, 'cut_rules') and tour_format.cut_rules:
            for cut_rule in tour_format.cut_rules:
                if cut_rule.players_remaining == target.players_remaining:
                    target_cut_round = cut_rule.after_round
                    break
        
        # Only process if this cut has already occurred
        if target_cut_round is None or target_cut_round >= current_round:
            continue
            
        # Determine who made this cut
        target_results = {}
        for player in all_players:
            # Player made the cut if they're still active OR were eliminated after this cut round
            if not player.is_eliminated:
                # Still active = made all past cuts
                target_results[player.name] = 1.0
            else:
                # Check when they were eliminated
                eliminated_round = player.eliminated_at.overall_round if player.eliminated_at else 0
                # The cut happens after target_cut_round, so players eliminated in target_cut_round + 1
                # were eliminated BY this cut and didn't make it
                cut_elimination_round = target_cut_round + 1
                if eliminated_round > cut_elimination_round:
                    # Eliminated after this cut = made this cut
                    target_results[player.name] = 1.0
                else:
                    # Eliminated at or before this cut = didn't make this cut
                    target_results[player.name] = 0.0
        
        past_probabilities[target.probability_name] = target_results
    
    return past_probabilities

def evaluate_probability_targets(final_standings: List[Player], eliminated_players: List[Player], sim_settings: SimSettings, cut_history: Dict[int, List[Player]] = None) -> Dict[str, Dict[str, bool]]:
    """Evaluate all probability targets for each player based on final tournament results."""
    results = {}
    
    # Create mapping of player to their final rank
    player_rankings = {player.id: i + 1 for i, player in enumerate(final_standings)}
    
    # Get all players (active + eliminated) for complete evaluation
    all_players = final_standings + eliminated_players
    
    for target in sim_settings.probability_targets:
        target_results = {}
        
        # Determine which players to evaluate based on target type
        if target.type == "made_cut":
            # For cut probabilities, evaluate all players (active + eliminated)
            # A player who made a cut but was later eliminated should still get credit for making that cut
            players_to_evaluate = all_players
        else:
            # For final standings, tournament winner, etc., evaluate all players
            players_to_evaluate = all_players
        
        for player in players_to_evaluate:
            player_result = False
            
            if target.type == "tournament_winner":
                # Winner is 1st place
                player_result = player_rankings.get(player.id, len(final_standings) + 1) == 1
                
            elif target.type == "overall_standing":
                # Get player rank, defaulting to worse than last place if eliminated
                player_rank = player_rankings.get(player.id, len(final_standings) + 1)
                
                if target.comparison == "at":
                    player_result = player_rank == target.threshold
                elif target.comparison == "above":
                    player_result = player_rank < target.threshold  # Lower rank number = better
                elif target.comparison == "below":
                    player_result = player_rank > target.threshold  # Higher rank number = worse
                elif target.comparison == "at_or_above":
                    player_result = player_rank <= target.threshold
                elif target.comparison == "at_or_below":
                    player_result = player_rank >= target.threshold
                    
            elif target.type == "made_cut":
                # Check if player made it to the cut (i.e., wasn't eliminated before reaching target.players_remaining)
                if cut_history and target.players_remaining in cut_history:
                    # Player made the cut if they're in the list of players who survived to this cut
                    player_result = player in cut_history[target.players_remaining]
                else:
                    # Fallback: if they finished in top N positions, they made the cut
                    player_rank = player_rankings.get(player.id, len(final_standings) + 1)
                    player_result = player_rank <= target.players_remaining
            
            target_results[player.name] = player_result
        
        # Note: No longer need to explicitly set eliminated players to False for made_cut targets
        # since we now evaluate all players properly for cut probabilities
        
        results[target.probability_name] = target_results
    
    return results

def accumulate_final_results(current_state: TourState, results: Dict, tour_format: TourFormat, sim_settings: SimSettings = None, cut_history: Dict[int, List] = None):
    """Step 7: Add final tournament results to accumulated data."""
    if not sim_settings or not sim_settings.probability_targets:
        return
    
    # Get final standings (silently during simulation)
    final_standings = determine_final_standings(current_state, silent=True)
    
    # Evaluate probability targets for this simulation run
    target_results = evaluate_probability_targets(final_standings, current_state.eliminated_players, sim_settings, cut_history)
    
    # Accumulate results
    if "probability_results" not in results:
        results["probability_results"] = {}
        
    for target_name, target_results_dict in target_results.items():
        if target_name not in results["probability_results"]:
            results["probability_results"][target_name] = {}
            
        for player_name, achieved_target in target_results_dict.items():
            if player_name not in results["probability_results"][target_name]:
                results["probability_results"][target_name][player_name] = {"count": 0, "total": 0}
            
            results["probability_results"][target_name][player_name]["total"] += 1
            if achieved_target:
                results["probability_results"][target_name][player_name]["count"] += 1

def calculate_cut_threshold_statistics(results: Dict) -> Dict:
    """Calculate statistics for cut thresholds (mean, distribution, etc.)."""
    cut_stats = {}
    
    if "cut_thresholds" not in results:
        return cut_stats
    
    for cut_name, thresholds in results["cut_thresholds"].items():
        if not thresholds:
            continue
            
        # Basic statistics
        stats = {
            "mean": sum(thresholds) / len(thresholds),
            "min": min(thresholds),
            "max": max(thresholds),
            "count": len(thresholds)
        }
        
        # Count cut types: clean cuts (half-point) vs tiebreaker cuts (whole-point)
        clean_cuts = 0
        tiebreaker_cuts = 0
        
        for threshold in thresholds:
            if threshold % 1 == 0.5:  # Half-point threshold = clean cut
                clean_cuts += 1
            else:  # Whole-point threshold = tiebreaker cut
                tiebreaker_cuts += 1
        
        total_cuts = len(thresholds)
        stats["cut_types"] = {
            "clean_cuts": {
                "count": clean_cuts,
                "percentage": (clean_cuts / total_cuts) * 100 if total_cuts > 0 else 0
            },
            "tiebreaker_cuts": {
                "count": tiebreaker_cuts,
                "percentage": (tiebreaker_cuts / total_cuts) * 100 if total_cuts > 0 else 0
            }
        }
        
        # Count distribution of thresholds
        threshold_counts = {}
        for threshold in thresholds:
            threshold_counts[threshold] = threshold_counts.get(threshold, 0) + 1
        
        # Convert to probability distribution
        threshold_distribution = {
            threshold: count / total_cuts 
            for threshold, count in threshold_counts.items()
        }
        
        # Find most common threshold
        most_common_threshold = max(threshold_counts.items(), key=lambda x: x[1])
        stats["most_common"] = {
            "threshold": most_common_threshold[0],
            "probability": most_common_threshold[1] / total_cuts,
            "count": most_common_threshold[1]
        }
        
        stats["distribution"] = threshold_distribution
        cut_stats[cut_name] = stats
    
    return cut_stats

def organize_probabilities_by_player(results: Dict, tour_state: TourState = None, tour_format: TourFormat = None) -> Dict:
    """Reorganize probability results to be structured by player first, then by probability type."""
    if "probability_results" not in results:
        return {}
    
    # Calculate probabilities for all results
    final_probabilities = calculate_final_probabilities(results)
    
    # Get all tiebreakers from tour format
    tiebreaker_order = []
    if tour_format and hasattr(tour_format, 'tiebreaker_order') and tour_format.tiebreaker_order:
        # Skip "points" as it's handled separately, get all other tiebreakers
        tiebreaker_order = [tb for tb in tour_format.tiebreaker_order if tb != "points"]
    
    # Create a mapping of player names to their current stats
    player_stats = {}
    if tour_state:
        all_players = tour_state.players + tour_state.eliminated_players
        for player in all_players:
            # Get tiebreakers
            tb = player.tiebreakers
            player_tiebreakers = {}
            
            # Extract all tiebreakers based on the tour format order
            for tiebreaker_name in tiebreaker_order:
                if isinstance(tb, dict):
                    tiebreaker_value = tb.get(tiebreaker_name, 0)
                else:
                    tiebreaker_value = getattr(tb, tiebreaker_name, 0) if hasattr(tb, tiebreaker_name) else 0
                player_tiebreakers[tiebreaker_name] = tiebreaker_value
            
            player_stats[player.name] = {
                "current_points": player.points,
                "tiebreakers": player_tiebreakers,
                "tiebreaker_order": tiebreaker_order
            }
    
    # Reorganize by player
    player_probabilities = {}
    
    for target_name, target_data in final_probabilities.items():
        for player_name, player_data in target_data.items():
            if player_name not in player_probabilities:
                player_probabilities[player_name] = {}
                
                # Add current stats if available
                if player_name in player_stats:
                    player_probabilities[player_name]["current_points"] = player_stats[player_name]["current_points"]
                    player_probabilities[player_name]["tiebreakers"] = player_stats[player_name]["tiebreakers"]
                    player_probabilities[player_name]["tiebreaker_order"] = player_stats[player_name]["tiebreaker_order"]
            
            player_probabilities[player_name][target_name] = {
                "probability": player_data["probability"],
                "count": player_data["count"],
                "total": player_data["total"]
            }
    
    return player_probabilities

def calculate_final_probabilities(results: Dict) -> Dict:
    """Calculate final probabilities from accumulated results."""
    if "probability_results" not in results:
        return {}
    
    probabilities = {}
    
    for target_name, target_data in results["probability_results"].items():
        probabilities[target_name] = {}
        
        for player_name, player_data in target_data.items():
            if player_data["total"] > 0:
                probability = player_data["count"] / player_data["total"]
                probabilities[target_name][player_name] = {
                    "probability": probability,
                    "count": player_data["count"],
                    "total": player_data["total"]
                }
    
    return probabilities

def determine_final_standings(current_state: TourState, silent: bool = False) -> List[Player]:
    """Determine final tournament standings by sorting all players (active + eliminated)."""
    all_players = current_state.players + current_state.eliminated_players
    final_standings = sort_players_by_standing(all_players)
    
    if not silent:
        print("\n" + "=" * 50)
        print("FINAL TOURNAMENT STANDINGS")
        print("=" * 50)
        
        for i, player in enumerate(final_standings):
            place = i + 1
            status = "✓ Active" if not player.is_eliminated else f"✗ Eliminated (Round {player.eliminated_at.overall_round})"
            
            # Format tiebreakers display
            tb = player.tiebreakers
            if isinstance(tb, dict):
                firsts = tb.get('firsts', 0)
                top4s = tb.get('top4s', 0)
            else:
                firsts = tb.firsts
                top4s = tb.top4s
            
            print(f"{place:2d}. {player.name:<20} - {player.points:3d} pts (avg: {player.avg_placement:.2f}) | {firsts} firsts, {top4s} top4s | {status}")
        
        print("=" * 50)
    
    return final_standings

def is_tournament_complete(current_state: TourState, tour_format: TourFormat) -> bool:
    """Step 5: Check if the tournament is finished."""
    current_round = current_state.current_round.overall_round
    
    # Check if we've reached the total rounds
    if current_round > tour_format.total_rounds:
        # print(f"Tournament complete: Reached maximum rounds ({tour_format.total_rounds})")
        # Determine final standings when tournament ends normally
        # determine_final_standings(current_state)
        return True
    
    # Check for checkmate conditions (early tournament ending)
    if tour_format.checkmate_conditions and tour_format.checkmate_conditions.get('points_threshold'):
        threshold = tour_format.checkmate_conditions['points_threshold']
        for player in current_state.players:
            if player.points >= threshold:
                # print(f"Tournament complete: {player.name} reached checkmate threshold ({player.points} >= {threshold} points)")
                # Determine final standings when tournament ends via checkmate
                # determine_final_standings(current_state)
                return True
    
    # Note: end_tournament flag is now handled in process_post_round_actions()
    # to ensure cuts are processed before tournament ends
    
    return False

def check_victory_conditions(current_state: TourState, tour_format: TourFormat, completed_round: int) -> bool:
    """Check if any victory conditions are met after completing a round."""
    # Check if this round has victory checking enabled
    if tour_format.round_structure:
        for round_info in tour_format.round_structure:
            if round_info.overall_round == completed_round:
                if round_info.post_round_actions.check_victory:
                    # print(f"Checking victory conditions after round {completed_round}")
                    
                    # Check for mathematical elimination scenarios
                    if len(current_state.players) == 1:
                        winner = current_state.players[0]
                        # print(f"Victory condition met: {winner.name} is the sole remaining player!")
                        # Determine final standings when only one player remains
                        # determine_final_standings(current_state)
                        return True
                    
                    # Check for insurmountable point leads
                    if len(current_state.players) > 1:
                        sorted_players = sort_players_by_standing(current_state.players)
                        leader = sorted_players[0]
                        second = sorted_players[1]
                        
                        # Calculate max possible points for remaining rounds
                        remaining_rounds = tour_format.total_rounds - completed_round
                        max_points_per_round = 8  # Maximum points possible in TFT
                        max_possible_points = remaining_rounds * max_points_per_round
                        
                        if leader.points > second.points + max_possible_points:
                            # print(f"Victory condition met: {leader.name} has insurmountable lead!")
                            # print(f"  Leader: {leader.points} points")
                            # print(f"  Second: {second.points} points (max possible: {second.points + max_possible_points})")
                            # Determine final standings when insurmountable lead is achieved
                            # determine_final_standings(current_state)
                            return True
                
                break
    
    return False

def should_continue_simulation(sim_count: int, start_time: float, sim_settings: SimSettings) -> bool:
    """Check if simulation should continue based on settings."""
    elapsed_time = time.time() - start_time
    
    if sim_settings.mode == SimulationMode.ITERATIONS_ONLY:
        return sim_count < sim_settings.max_iterations
    elif sim_settings.mode == SimulationMode.TIME_ONLY:
        return elapsed_time < sim_settings.max_time_seconds
    elif sim_settings.mode == SimulationMode.WHICHEVER_FIRST:
        return (sim_count < sim_settings.max_iterations and 
                elapsed_time < sim_settings.max_time_seconds)
    
    return False

def print_status(sim_count: int, sim_settings: SimSettings, elapsed_time: float):
    """Print status update showing iteration progress."""
    if sim_settings.mode in [SimulationMode.ITERATIONS_ONLY, SimulationMode.WHICHEVER_FIRST]:
        progress = sim_count / sim_settings.max_iterations * 100
        print(f"Progress: {sim_count}/{sim_settings.max_iterations} ({progress:.1f}%) - {elapsed_time:.1f}s elapsed")
    else:
        print(f"Completed: {sim_count} simulations - {elapsed_time:.1f}s elapsed")

def simulate_tournament(tour_format: TourFormat, tour_state: TourState, sim_settings: SimSettings, test_single_round: bool = False) -> tuple[Dict, int]:
    """Main simulation function."""
    results = initialize_results(tour_format)  # Step 0
    
    # DEBUG: Check initial player points
    print("DEBUG: Initial player points at start of simulation:")
    for i, player in enumerate(tour_state.players[:5]):  # Show first 5 players
        print(f"  {player.name}: points={player.points}, total_points={player.total_points}")
    
    # Filter probability targets to only include future events
    original_targets = sim_settings.probability_targets.copy() if sim_settings.probability_targets else []
    if sim_settings.probability_targets:
        future_targets = filter_future_probability_targets(
            sim_settings.probability_targets, 
            tour_state.current_round.overall_round, 
            tour_format
        )
        sim_settings.probability_targets = future_targets
        
        print(f"Filtered to {len(future_targets)} future probability targets (from {len(original_targets)} total)")
    
    start_time = time.time()
    last_status_time = start_time
    sim_count = 0
    
    while should_continue_simulation(sim_count, start_time, sim_settings):
        current_state = validate_and_load_state(tour_state)  # Step 1
        cut_history = {}  # Track cuts that happen during this simulation
        
        # Test single round mode - just simulate one round and exit
        if test_single_round:
            print(f"TEST MODE: Simulating single round {current_state.current_round.overall_round}")
            
            # Capture the round number before it gets incremented
            round_being_simulated = current_state.current_round.overall_round
            
            current_state = simulate_next_round(current_state, tour_format)  # Step 2
            
            # Export to CSV after simulating the round
            print(f"Exporting CSV after round {round_being_simulated} simulation...")
            pydantic_tourstate_to_csv(current_state, f"test_single_round_{round_being_simulated}_result.csv")
            
            print(f"Single round test complete. Check test_single_round_{round_being_simulated}_result.csv")
            return results, 1  # Return early after one round
        
        # Normal tournament mode
        while not is_tournament_complete(current_state, tour_format):  # Step 5/6
            current_state = simulate_next_round(current_state, tour_format)  # Step 2
            
            # Export to CSV after simulating the round (for testing)
            # round_num = current_state.current_round.overall_round - 1  # -1 because we just completed this round
            # if sim_count == 0:  # Only export for the first simulation to avoid too many files
            #     print(f"Exporting CSV after round {round_num} simulation...")
            #     pydantic_tourstate_to_csv(current_state, f"test_after_round_{round_num}.csv")
            
            current_state, round_cut_history = process_post_round_actions(current_state, tour_format, results)  # Step 3
            # Merge any cuts from this round into the overall cut history
            cut_history.update(round_cut_history)
            record_simulation_data(current_state, results, tour_format)  # Step 4
        
        accumulate_final_results(current_state, results, tour_format, sim_settings, cut_history)  # Step 7
        sim_count += 1
        
        # Status updates every 10 seconds instead of every second
        current_time = time.time()
        if current_time - last_status_time >= 10.0:
            print_status(sim_count, sim_settings, current_time - start_time)
            last_status_time = current_time
    
    # Final status
    total_time = time.time() - start_time
    print(f"Simulation complete: {sim_count} iterations in {total_time:.1f}s")
    
    # Calculate and organize final probabilities without printing detailed results
    if original_targets:  # Use original targets for final processing
        final_probabilities = calculate_final_probabilities(results)
        
        # Get past cut probabilities (deterministic)
        past_probabilities = evaluate_past_cut_probabilities(tour_state, tour_format, original_targets)
        
        # Organize future probabilities by player
        future_player_probabilities = organize_probabilities_by_player(results, tour_state, tour_format)
        
        # Combine past and future probabilities
        combined_player_probabilities = {}
        all_players = tour_state.players + tour_state.eliminated_players
        
        for player in all_players:
            player_data = future_player_probabilities.get(player.name, {})
            
            # Add past cut probabilities
            for target_name, target_results in past_probabilities.items():
                if player.name in target_results:
                    probability = target_results[player.name]
                    player_data[target_name] = {
                        "probability": probability,
                        "count": int(probability * sim_count),  # Convert to count format
                        "total": sim_count
                    }
            
            if player_data:  # Only include players with probability data
                combined_player_probabilities[player.name] = player_data
        
        # Calculate cut threshold statistics
        cut_stats = calculate_cut_threshold_statistics(results)
        
        # Replace the complex structure with clean player-organized data
        results = {
            "player_probabilities": combined_player_probabilities,
            "cut_threshold_statistics": cut_stats,
            "simulation_metadata": {
                "total_simulations": sim_count,
                "simulation_time_seconds": total_time,
                "probability_targets": [target.model_dump() for target in original_targets],
                "tournament_title": getattr(tour_format, 'tournament_name', 'TFT Tournament'),
                "current_round": {
                    "overall_round": tour_state.current_round.overall_round,
                    "day": tour_state.current_round.day,
                    "round_in_day": tour_state.current_round.round_in_day,
                    "round_status": tour_state.current_round.round_status
                }
            }
        }
    
    return results, sim_count

def print_probability_results(probabilities: Dict):
    """Print formatted probability results."""
    if not probabilities:
        return
        
    print("\n" + "=" * 60)
    print("PROBABILITY ANALYSIS RESULTS")
    print("=" * 60)
    
    for target_name, target_data in probabilities.items():
        print(f"\n{target_name.upper().replace('_', ' ')}:")
        print("-" * 40)
        
        # Sort players by probability (descending)
        sorted_players = sorted(target_data.items(), key=lambda x: x[1]['probability'], reverse=True)
        
        for player_name, data in sorted_players:
            probability = data['probability']
            count = data['count']
            total = data['total']
            print(f"{player_name:<25} {probability:>6.1%} ({count:>4}/{total:<4})")
    
    print("=" * 60)

def test_post_round_actions(tour_state_file: str = "tour_state.json"):
    """Test function to demonstrate post-round actions including cuts."""
    print("=" * 50)
    print("POST-ROUND ACTIONS TEST MODE")
    print("=" * 50)
    
    # Load tour state
    tour_state = load_tour_state_from_json(tour_state_file)
    
    print(f"Starting with {len(tour_state.players)} active players")
    
    # Create tour format with a cut after the current round
    current_round = tour_state.current_round.overall_round
    tour_format = TourFormat(
        total_rounds=8,
        cut_rules=[CutRule(after_round=current_round, players_remaining=4)]  # Cut to top 4 after current round
    )
    
    print(f"Tournament format: Cut to {tour_format.cut_rules[0].players_remaining} players after round {current_round}")
    
    # Create minimal sim settings for just one iteration
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Run simulation that will trigger post-round actions
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=False)
    
    print("=" * 50)
    print("Post-round actions test completed!")
    print("=" * 50)

def test_no_show_simulation(tour_state_file: str = "tour_state.json"):
    """Test function to demonstrate no-show functionality."""
    print("=" * 50)
    print("NO-SHOW TEST MODE")
    print("=" * 50)
    
    # Load tour state
    tour_state = load_tour_state_from_json(tour_state_file)
    
    # Mark the first player as no-show for the current round
    current_round = tour_state.current_round.overall_round
    if tour_state.players:
        first_player = tour_state.players[0]
        success = mark_player_no_show(tour_state, first_player.id, current_round)
        if success:
            print(f"Marked {first_player.name} (ID: {first_player.id}) as no-show for round {current_round}")
        else:
            print(f"Failed to mark {first_player.name} as no-show")
    
    # Create minimal tour format
    tour_format = TourFormat(total_rounds=8)
    
    # Create minimal sim settings
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Run single round test
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=True)
    
    print("=" * 50)
    print("No-show test completed!")
    print("=" * 50)

def test_single_round_simulation(tour_state_file: str = "tour_state.json"):
    """Simple function to test a single round simulation."""
    print("=" * 50)
    print("SINGLE ROUND TEST MODE")
    print("=" * 50)
    
    # Load tour state
    tour_state = load_tour_state_from_json(tour_state_file)
    
    # Create minimal tour format
    tour_format = TourFormat(total_rounds=8)
    
    # Create minimal sim settings
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Run single round test
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=True)
    
    print("=" * 50)
    print("Single round test completed!")
    print("=" * 50)

def test_multi_round_simulation(tour_state_file: str, num_rounds: int, tour_format_file: str = None):
    """Test function to simulate multiple rounds and show progression."""
    print("=" * 50)
    print(f"MULTI-ROUND TEST MODE ({num_rounds} rounds)")
    print("=" * 50)
    
    # Load tour state
    tour_state = load_tour_state_from_json(tour_state_file)
    
    starting_round = tour_state.current_round.overall_round
    print(f"Starting at round {starting_round} with {len(tour_state.players)} active players")
    
    # Load tour format from JSON file if provided, otherwise create default
    if tour_format_file:
        print(f"Loading tour format from: {tour_format_file}")
        tour_format = load_tour_format_from_json(tour_format_file)
        print(f"Tournament format: {len(tour_format.cut_rules)} cut rule(s)")
        for rule in tour_format.cut_rules:
            print(f"  Cut to {rule.players_remaining} players after round {rule.after_round}")
    else:
        # Create tour format with a cut rule for testing (fallback)
        cut_round = starting_round + 1  # Cut after the second round we simulate
        tour_format = TourFormat(
            total_rounds=8,
            cut_rules=[CutRule(after_round=cut_round, players_remaining=4)]
        )
        print(f"Using default tournament format: Cut to 4 players after round {cut_round}")
    
    # Create sim settings for exactly one iteration
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Simulate the specified number of rounds
    current_state = validate_and_load_state(tour_state)
    
    for round_num in range(num_rounds):
        current_round = current_state.current_round.overall_round
        print(f"\n{'='*30}")
        print(f"ROUND {current_round} ({round_num + 1}/{num_rounds})")
        print(f"{'='*30}")
        print(f"Active players: {len(current_state.players)}")
        
        # Simulate the round
        current_state = simulate_next_round(current_state, tour_format)
        
        # Export CSV after each round for inspection
        csv_filename = f"test_multi_round_{current_round}_result.csv"
        print(f"Exporting CSV: {csv_filename}")
        pydantic_tourstate_to_csv(current_state, csv_filename)
        
        # Process post-round actions
        current_state, _ = process_post_round_actions(current_state, tour_format)
        
        # Check if tournament is complete or no players left
        if is_tournament_complete(current_state, tour_format):
            print(f"Tournament completed after round {current_round}")
            break
        
        if len(current_state.players) == 0:
            print(f"No players remaining after round {current_round}")
            break
    
    final_round = current_state.current_round.overall_round - 1
    print(f"\n{'='*50}")
    print(f"Multi-round test complete!")
    print(f"Simulated rounds {starting_round} through {final_round}")
    print(f"Final state: {len(current_state.players)} active, {len(current_state.eliminated_players)} eliminated")
    print(f"{'='*50}")

def test_snake_shuffle_demo():
    """Demonstrate snake shuffle with multiple lobbies."""
    print("=" * 50)
    print("SNAKE SHUFFLE DEMO")
    print("=" * 50)
    
    # Create 8 mock players with different point totals
    players = [
        Player(id=1, name="Player1", points=50, tiebreakers=Tiebreakers()),
        Player(id=2, name="Player2", points=45, tiebreakers=Tiebreakers()),  
        Player(id=3, name="Player3", points=40, tiebreakers=Tiebreakers()),
        Player(id=4, name="Player4", points=35, tiebreakers=Tiebreakers()),
        Player(id=5, name="Player5", points=30, tiebreakers=Tiebreakers()),
        Player(id=6, name="Player6", points=25, tiebreakers=Tiebreakers()),
        Player(id=7, name="Player7", points=20, tiebreakers=Tiebreakers()),
        Player(id=8, name="Player8", points=15, tiebreakers=Tiebreakers()),
    ]
    
    print("Testing with 8 players, 4 players per lobby (2 lobbies):")
    
    # Test snake shuffle with 4 players per lobby (creates 2 lobbies)
    snake_lobbies = assign_lobbies_snake_shuffle(players, players_per_lobby=4)
    
    print("\nSnake shuffle result:")
    for lobby_name, lobby_players in snake_lobbies.items():
        points = [f"{p.name}({p.points})" for p in lobby_players]
        print(f"  {lobby_name}: {points}")
    
    print("\nRandom shuffle result (for comparison):")
    random_lobbies = assign_lobbies_random_shuffle(players, players_per_lobby=4)
    for lobby_name, lobby_players in random_lobbies.items():
        points = [f"{p.name}({p.points})" for p in lobby_players]
        print(f"  {lobby_name}: {points}")
    
    print("=" * 50)

def test_victory_conditions():
    """Test function to demonstrate victory condition checking."""
    print("=" * 50)
    print("VICTORY CONDITIONS TEST MODE")
    print("=" * 50)
    
    # Create a mock tournament state with a clear leader
    from models import Player, TourState, CurrentRound, RoundStatus, RoundHistory, Tiebreakers
    
    # Create players with different point totals
    players = [
        Player(id=1, name="Leader", points=50, tiebreakers=Tiebreakers()),  # High points - potential checkmate
        Player(id=2, name="SecondPlace", points=25, tiebreakers=Tiebreakers()),
        Player(id=3, name="ThirdPlace", points=20, tiebreakers=Tiebreakers()),
        Player(id=4, name="FourthPlace", points=15, tiebreakers=Tiebreakers()),
    ]
    
    # Create tournament state
    current_round = CurrentRound(
        overall_round=5,
        day=1, 
        round_in_day=5,
        round_status=RoundStatus.COMPLETED
    )
    
    tour_state = TourState(
        current_round=current_round,
        players=players,
        eliminated_players=[]
    )
    
    print("Testing Scenario 1: Checkmate threshold victory")
    # Test checkmate threshold (50 points)
    tour_format_checkmate = TourFormat(
        total_rounds=8,
        checkmate_conditions={"points_threshold": 50}
    )
    
    print(f"Current leader: {players[0].name} with {players[0].points} points")
    print(f"Checkmate threshold: 50 points")
    
    is_complete = is_tournament_complete(tour_state, tour_format_checkmate)
    print(f"Tournament complete: {is_complete}")
    
    print("\n" + "=" * 30)
    print("Testing Scenario 2: Insurmountable lead victory")
    
    # Test insurmountable lead (need victory checking enabled)
    from models import PostRoundActions, RoundStructure
    
    victory_round = RoundStructure(
        overall_round=5,
        day=1,
        round_in_day=5,
        post_round_actions=PostRoundActions(check_victory=True)
    )
    
    tour_format_victory = TourFormat(
        total_rounds=8,
        round_structure=[victory_round]
    )
    
    print(f"Leader: {players[0].name} - {players[0].points} points")
    print(f"Second: {players[1].name} - {players[1].points} points")
    remaining_rounds = tour_format_victory.total_rounds - 5
    max_possible = players[1].points + (remaining_rounds * 8)
    print(f"Remaining rounds: {remaining_rounds}")
    print(f"Second place max possible: {max_possible} points")
    
    victory_met = check_victory_conditions(tour_state, tour_format_victory, 5)
    print(f"Victory condition met: {victory_met}")
    
    print("=" * 50)
    print("Victory conditions test completed!")
    print("=" * 50)

def test_probability_tracking():
    """Test function to demonstrate probability tracking functionality."""
    print("=" * 50)
    print("PROBABILITY TRACKING TEST MODE")
    print("=" * 50)
    
    # Load tour state and format
    tour_state = load_tour_state_from_json(
        "Example_Data/16_Player_Examples/Mid_Second_Round/tftodds_sample_data_16_halfwaythrusecondround.json"
    )
    tour_format = load_tour_format_from_json(
        "Example_Data/16_Player_Examples/tour_format_16players_8rounds_cutafter4.json"
    )
    
    # Create simulation settings with probability targets
    probability_targets = [
        ProbabilityTarget(
            probability_name="made_top_8_cut",
            type="made_cut",
            players_remaining=8
        ),
        ProbabilityTarget(
            probability_name="finished_top_3",
            type="overall_standing",
            comparison="at_or_above",
            threshold=3
        ),
        ProbabilityTarget(
            probability_name="won_tournament",
            type="tournament_winner"
        ),
        ProbabilityTarget(
            probability_name="finished_bottom_half",
            type="overall_standing",
            comparison="below",
            threshold=8
        )
    ]
    
    sim_settings = SimSettings(
        max_iterations=100000,  # Run 10000 simulations for comprehensive analysis
        mode=SimulationMode.ITERATIONS_ONLY,
        probability_targets=probability_targets
    )
    
    print(f"Running {sim_settings.max_iterations} simulations with {len(probability_targets)} probability targets...")
    
    # Run simulation
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings)
    
    # Save results to JSON file
    save_results_to_json(results, "test_probabilities.json")
    print("Probability results saved to: test_probabilities.json")
    
    print("=" * 50)
    print("Probability tracking test completed!")
    print("=" * 50)

def load_tour_state_from_csv(csv_file: str, tour_format_file: str = None) -> TourState:
    """Load tournament state from CSV file by converting it to JSON format first."""
    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_json_path = temp_file.name
    
    try:
        # Convert CSV to JSON with optional tour format for point reset handling
        parse_csv_to_tourstate(csv_file, temp_json_path, tour_format_file)
        
        # Load the JSON as TourState
        tour_state = load_tour_state_from_json(temp_json_path)
        
        return tour_state
    finally:
        # Clean up temporary file
        if os.path.exists(temp_json_path):
            os.unlink(temp_json_path)

def test_single_round_simulation_csv(csv_file: str, tour_format_file: str = None):
    """Test function to simulate a single round from CSV input."""
    print("=" * 50)
    print("SINGLE ROUND TEST MODE (CSV INPUT)")
    print("=" * 50)
    
    # Load tour state from CSV with optional tour format
    tour_state = load_tour_state_from_csv(csv_file, tour_format_file)
    
    # Create minimal tour format
    tour_format = TourFormat(total_rounds=8)
    
    # Create minimal sim settings
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Run single round test
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=True)
    
    print("=" * 50)
    print("Single round test (CSV) completed!")
    print("=" * 50)

def test_post_round_actions_csv(csv_file: str, tour_format_file: str = None):
    """Test function to demonstrate post-round actions including cuts from CSV input."""
    print("=" * 50)
    print("POST-ROUND ACTIONS TEST MODE (CSV INPUT)")
    print("=" * 50)
    
    # Load tour state from CSV with optional tour format
    tour_state = load_tour_state_from_csv(csv_file, tour_format_file)
    
    print(f"Starting with {len(tour_state.players)} active players")
    
    # Create tour format with a cut after the current round
    current_round = tour_state.current_round.overall_round
    tour_format = TourFormat(
        total_rounds=8,
        cut_rules=[CutRule(after_round=current_round, players_remaining=4)]  # Cut to top 4 after current round
    )
    
    print(f"Tournament format: Cut to {tour_format.cut_rules[0].players_remaining} players after round {current_round}")
    
    # Create minimal sim settings for just one iteration
    sim_settings = SimSettings(max_iterations=1, mode=SimulationMode.ITERATIONS_ONLY)
    
    # Run simulation that will trigger post-round actions
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings, test_single_round=False)
    
    print("=" * 50)
    print("Post-round actions test (CSV) completed!")
    print("=" * 50)

def test_multi_round_simulation_csv(csv_file: str, num_rounds: int, tour_format_file: str = None):
    """Test function to simulate multiple rounds from CSV input."""
    print("=" * 50)
    print(f"MULTI-ROUND TEST MODE (CSV INPUT) - {num_rounds} rounds")
    print("=" * 50)
    
    # Load tour state from CSV with optional tour format
    tour_state = load_tour_state_from_csv(csv_file, tour_format_file)
    
    # Load tour format
    if tour_format_file:
        tour_format = load_tour_format_from_json(tour_format_file)
    else:
        # Create default tour format
        tour_format = TourFormat(
            total_rounds=8,
            cut_rules=[CutRule(after_round=4, players_remaining=8)]
        )
    
    # Create sim settings
    sim_settings = SimSettings(max_iterations=1000, mode=SimulationMode.ITERATIONS_ONLY)
    
    print(f"Starting tournament simulation from CSV...")
    print(f"Current round: {tour_state.current_round.overall_round}")
    print(f"Active players: {len(tour_state.players)}")
    
    # Run simulation
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings)
    
    # Save results
    save_results_to_json(results, f"multi_round_csv_results_{num_rounds}rounds.json")
    print(f"Results saved to: multi_round_csv_results_{num_rounds}rounds.json")
    
    print("=" * 50)
    print("Multi-round test (CSV) completed!")
    print("=" * 50)

def load_sim_settings_from_json(json_file: str) -> SimSettings:
    """Load simulation settings from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)
    return SimSettings(**data)

def test_probability_tracking_csv(csv_file: str, tour_format_file: str = None, sim_settings_file: str = None, output_file: str = "test_probabilities_csv.json"):
    """Test function to demonstrate probability tracking functionality from CSV input."""
    print("=" * 50)
    print("PROBABILITY TRACKING TEST MODE (CSV INPUT)")
    print("=" * 50)
    
    # Load tour state from CSV with optional tour format for point reset handling
    tour_state = load_tour_state_from_csv(csv_file, tour_format_file)
    
    # Load tour format
    if tour_format_file:
        tour_format = load_tour_format_from_json(tour_format_file)
    else:
        # Create default tour format based on current state
        tour_format = TourFormat(
            total_rounds=8,
            cut_rules=[CutRule(after_round=4, players_remaining=8)]
        )
    
    # Load sim settings
    if sim_settings_file:
        sim_settings = load_sim_settings_from_json(sim_settings_file)
    else:
        # Create default simulation settings with probability targets
        probability_targets = [
            ProbabilityTarget(
                probability_name="made_top_8_cut",
                type="made_cut",
                players_remaining=8
            ),
            ProbabilityTarget(
                probability_name="finished_top_3",
                type="overall_standing",
                comparison="at_or_above",
                threshold=3
            ),
            ProbabilityTarget(
                probability_name="won_tournament",
                type="tournament_winner"
            ),
            ProbabilityTarget(
                probability_name="finished_bottom_half",
                type="overall_standing",
                comparison="below",
                threshold=len(tour_state.players) // 2
            )
        ]
        
        sim_settings = SimSettings(
            max_iterations=10000,  # Run 10000 simulations for comprehensive analysis
            mode=SimulationMode.ITERATIONS_ONLY,
            probability_targets=probability_targets
        )
    
    print(f"Running {sim_settings.max_iterations} simulations with {len(sim_settings.probability_targets)} probability targets...")
    print(f"Current round: {tour_state.current_round.overall_round}")
    print(f"Active players: {len(tour_state.players)}")
    
    # Run simulation
    results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings)
    
    # Save results to JSON file
    save_results_to_json(results, output_file)
    print(f"Probability results saved to: {output_file}")
    
    print("=" * 50)
    print("Probability tracking test (CSV) completed!")
    print("=" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run TFT tournament simulation from CSV input')
    
    # Add arguments for CSV mode
    parser.add_argument('--csv', type=str, help='Path to input CSV file')
    parser.add_argument('--tour-format', type=str, help='Path to tour format JSON file')
    parser.add_argument('--sim-settings', type=str, help='Path to simulation settings JSON file')
    parser.add_argument('--output', type=str, default='probabilities.json', help='Output filename for results (default: probabilities.json)')
    
    # Add test mode arguments (for backward compatibility)
    parser.add_argument('--single-round', action='store_true', help='Run single round test')
    parser.add_argument('--post-round', action='store_true', help='Run post-round actions test')
    parser.add_argument('--multi-round', action='store_true', help='Run multi-round test')
    parser.add_argument('--probability', action='store_true', help='Run probability tracking test')
    parser.add_argument('--victory', action='store_true', help='Run victory conditions test')
    parser.add_argument('--snake-shuffle', action='store_true', help='Run snake shuffle demo')
    parser.add_argument('--no-show', action='store_true', help='Run no-show test')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If CSV file is provided, run CSV mode
    if args.csv:
        print("=" * 60)
        print("RUNNING SIMULATION WITH CSV INPUT")
        print("=" * 60)
        print(f"CSV Input: {args.csv}")
        print(f"Tour Format: {args.tour_format}")
        print(f"Sim Settings: {args.sim_settings}")
        print(f"Output: {args.output}")
        print("=" * 60)
        
        # Run probability tracking with CSV input
        test_probability_tracking_csv(args.csv, args.tour_format, args.sim_settings, args.output)
        
    # Otherwise, run legacy test modes based on flags
    elif args.victory:
        test_victory_conditions()
    elif args.snake_shuffle:
        test_snake_shuffle_demo()
    elif args.probability:
        test_probability_tracking()
    elif args.multi_round:
        test_multi_round_simulation(
            "Example_Data/16_Player_Examples/Mid_Second_Round/tftodds_sample_data_16_halfwaythrusecondround.json", 
            7,  # ROUNDS_TO_TEST
            "Example_Data/16_Player_Examples/tour_format_16players_8rounds_cutafter4.json"
        )
    elif args.post_round:
        test_post_round_actions("Example_Data/16_Player_Examples/Mid_Second_Round/tftodds_sample_data_16_halfwaythrusecondround.json")
    elif args.no_show:
        test_no_show_simulation("Example_Data/16_Player_Examples/Mid_Second_Round/tftodds_sample_data_16_halfwaythrusecondround.json")
    elif args.single_round:
        test_single_round_simulation("Example_Data/16_Player_Examples/Mid_Second_Round/tftodds_sample_data_16_halfwaythrusecondround.json")
    else:
        # Default behavior - show help
        print("No operation specified. Use --help to see available options.")
        print("\nExample CSV usage:")
        print("python simulation.py --csv tour_state.csv --tour-format format.json --sim-settings settings.json --output results.json")
        parser.print_help() 
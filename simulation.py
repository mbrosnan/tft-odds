import time
import random
from typing import Dict, List, Set
from models import TourFormat, TourState, SimSettings, SimulationMode, CutRule, RoundHistory, RoundStatus
from utils import load_tour_state_from_json, save_results_to_json, save_json
from tourstate_to_csv import tourstate_to_csv, pydantic_tourstate_to_csv

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
    """Convert placement to points using standard TFT scoring, adjusted for lobby size."""
    if lobby_size == 8:
        # Standard 8-player scoring
        points_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
        return points_map.get(placement, 0)
    else:
        # For smaller lobbies, scale points proportionally
        # 1st place always gets lobby_size points, last place gets 1 point
        return max(1, lobby_size + 1 - placement)

def calculate_tiebreakers(round_history: List[RoundHistory]) -> Dict[str, int]:
    """Calculate tiebreaker statistics from round history."""
    tiebreakers = {
        "firsts": 0, "seconds": 0, "thirds": 0, "fourths": 0,
        "fifths": 0, "sixths": 0, "sevenths": 0, "eighths": 0,
        "top4s": 0
    }
    
    for round_data in round_history:
        placement = round_data.placement
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
            
    return tiebreakers

def update_player_stats(player, round_history: List[RoundHistory]):
    """Update player's overall stats based on their round history."""
    total_points = 0
    total_placement = 0
    completed_rounds = 0
    
    for round_data in round_history:
        if round_data.placement is not None and round_data.points is not None:
            total_points += round_data.points
            total_placement += round_data.placement
            completed_rounds += 1
    
    player.points = total_points
    player.completed_rounds = completed_rounds
    player.avg_placement = round(total_placement / completed_rounds, 2) if completed_rounds > 0 else 0.0
    player.tiebreakers = calculate_tiebreakers(round_history)

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
    # print(f"Simulating round {current_state.current_round.overall_round}") made it here
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
                # print(f"Found current round entry for {player.name} and it is {current_round_entry.placement}")
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
        print(f"Lobby {lobby_name}: {lobby_stats['active']} active players, {lobby_stats['no_shows']} no-shows")
        
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
        
        # Calculate available placements based on lobby size
        # If there are no-shows, the lobby plays with fewer players
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
                        points = get_points_for_placement(placement, active_players_count)
                        print(f"Player {player.name} placed {placement} and earned {points} points")
                        
                        # Update the round entry
                        round_entry.placement = placement
                        round_entry.points = points
        
        # Log no-shows
        for player, round_entry in no_show_players:
            print(f"Player {player.name} was a no-show and earned 0 points")
    
    # Update all player stats after round completion
    for player in current_state.players:
        update_player_stats(player, player.round_history)
    
    # Mark current round as completed.  DO NOT advance to the next round.  that will be a separate item.
    current_state.current_round.round_status = RoundStatus.COMPLETED

    
    return current_state

def process_post_round_actions(current_state: TourState, tour_format: TourFormat) -> TourState:
    """Step 3: Handle cuts, shuffles, and other post-round actions."""
    # TODO: Implement post-round processing
    pass

def record_simulation_data(current_state: TourState, results: Dict, tour_format: TourFormat):
    """Step 4: Record relevant data during the simulation."""
    # TODO: Implement data recording
    pass

def accumulate_final_results(current_state: TourState, results: Dict, tour_format: TourFormat):
    """Step 7: Add final tournament results to accumulated data."""
    # TODO: Implement final results accumulation
    pass

def is_tournament_complete(current_state: TourState, tour_format: TourFormat) -> bool:
    """Step 5: Check if the tournament is finished."""
    # Tournament is complete if we've reached the total rounds
    return current_state.current_round.overall_round > tour_format.total_rounds

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
    
    start_time = time.time()
    last_status_time = start_time
    sim_count = 0
    
    while should_continue_simulation(sim_count, start_time, sim_settings):
        current_state = validate_and_load_state(tour_state)  # Step 1
        
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
            round_num = current_state.current_round.overall_round - 1  # -1 because we just completed this round
            if sim_count == 0:  # Only export for the first simulation to avoid too many files
                print(f"Exporting CSV after round {round_num} simulation...")
                pydantic_tourstate_to_csv(current_state, f"test_after_round_{round_num}.csv")
            
            current_state = process_post_round_actions(current_state, tour_format)  # Step 3
            record_simulation_data(current_state, results, tour_format)  # Step 4
        
        accumulate_final_results(current_state, results, tour_format)  # Step 7
        sim_count += 1
        
        # Status updates every second
        current_time = time.time()
        if current_time - last_status_time >= 1.0:
            print_status(sim_count, sim_settings, current_time - start_time)
            last_status_time = current_time
    
    # Final status
    total_time = time.time() - start_time
    print(f"Simulation complete: {sim_count} iterations in {total_time:.1f}s")
    
    # Save Pydantic object to JSON
    tour_state_dict = tour_state.model_dump()
    save_json(tour_state_dict, "temp_tour_state.json")

    # Convert JSON to CSV
    tourstate_to_csv("temp_tour_state.json", "output.csv")
    
    return results, sim_count

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

if __name__ == "__main__":
    # Toggle between different test modes
    SINGLE_ROUND_TEST = False  # Change this to False for full simulation
    NO_SHOW_TEST = True       # Change this to True to test no-show functionality
    
    if NO_SHOW_TEST:
        # Test no-show functionality
        test_no_show_simulation("Example_Data/16_Player_Examples/Mid_Fifth_Round/tour_state_16players_8rounds_midfifthround_newstuff.json")
    elif SINGLE_ROUND_TEST:
        # Test single round
        test_single_round_simulation("Example_Data/16_Player_Examples/Mid_Fifth_Round/tour_state_16players_8rounds_midfifthround_newstuff.json")
    else:
        # Full simulation
        tour_format = TourFormat(
            total_rounds=8,
            cut_rules=[CutRule(after_round=4, players_remaining=8)]
        )
        
        tour_state = load_tour_state_from_json("tour_state.json")
        
        sim_settings = SimSettings(
            max_iterations=10000,
            mode=SimulationMode.ITERATIONS_ONLY
        )
        
        results, sim_count = simulate_tournament(tour_format, tour_state, sim_settings)
        save_results_to_json(results, "probabilities.json") 
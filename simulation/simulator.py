from typing import List, Dict, Set, Optional
import random
import time
from dataclasses import dataclass
from .tournament_state import TournamentState, Player, RoundResult, ActionType, ShuffleType
import json

@dataclass
class SimulationResult:
    player_name: str
    made_cuts: Dict[int, Set[str]]  # cut_size -> set of player names who made the cut
    won_tournament: bool

class TournamentSimulator:
    def __init__(self, tournament_state: TournamentState):
        self.state = tournament_state
        self.results: List[SimulationResult] = []
        # Initialize remaining_players with all players since we're mid-round
        self.remaining_players: Set[str] = set(p.name for p in tournament_state.players)
        # Initialize cut_results as empty - cuts will be recorded as they happen
        self.cut_results: Dict[int, Set[str]] = {}
        # For any cut stages that are larger than our current player count,
        # everyone automatically makes those cuts
        for cut_size in tournament_state.cut_stages:
            if cut_size >= len(tournament_state.players):
                self.cut_results[cut_size] = self.remaining_players.copy()
        # Validate lobby placements
        self.validate_lobby_placements()
    
    def validate_lobby_placements(self) -> None:
        """Validate that each lobby in completed rounds has exactly one player in each placement."""
        # Group players by round and lobby
        rounds_lobbies = {}
        for player in self.state.players:
            for round_result in player.rounds:
                if round_result.placement > 0:  # Only check completed rounds/placements
                    key = (round_result.round, round_result.lobby)
                    if key not in rounds_lobbies:
                        rounds_lobbies[key] = []
                    rounds_lobbies[key].append(round_result.placement)
        
        # Check each lobby
        for (round_num, lobby), placements in rounds_lobbies.items():
            # If we have any placements for this lobby, we should have all 1-8
            if placements:
                # Convert to set and check if it matches {1,2,3,4,5,6,7,8} or is a subset
                placement_set = set(placements)
                valid_placements = set(range(1, 9))
                if not placement_set.issubset(valid_placements):
                    raise ValueError(f"Invalid placements in round {round_num} lobby {lobby}: {placement_set}")
                # If we have more than one of any placement, that's an error
                if len(placements) != len(placement_set):
                    raise ValueError(f"Duplicate placements in round {round_num} lobby {lobby}: {placements}")
    
    def simulate_round(self) -> None:
        """Simulate a single round of the tournament."""
        # Get current standings and create lobbies
        standings = self.state.get_player_standings()
        remaining = [p for p in standings if p.name in self.remaining_players]
        
        # Create lobbies of 8 players
        lobbies = []
        current_lobby = []
        for player in remaining:
            current_lobby.append(player)
            if len(current_lobby) == 8:
                lobbies.append(current_lobby)
                current_lobby = []
        if current_lobby:  # Handle remaining players
            lobbies.append(current_lobby)
        
        # Simulate each lobby
        for i, lobby in enumerate(lobbies):
            lobby_letter = chr(65 + i)  # A, B, C, etc.
            # Randomly assign placements
            placements = list(range(1, len(lobby) + 1))
            random.shuffle(placements)
            
            for player, place in zip(lobby, placements):
                # Add points (8 for 1st, 7 for 2nd, etc.)
                points_earned = max(9 - place, 1)
                player.points += points_earned
                
                # Record round result
                player.rounds.append(RoundResult(
                    round=self.state.current_round,  # Use current round number directly
                    lobby=lobby_letter,
                    placement=place
                ))
                
                # Update tiebreakers
                if place == 1:
                    player.tiebreakers["firsts"] = player.tiebreakers.get("firsts", 0) + 1
                if place <= 4:
                    player.tiebreakers["top4s"] = player.tiebreakers.get("top4s", 0) + 1
    
    def apply_cut(self, cut_to: int) -> None:
        """Apply a cut to the tournament."""
        standings = self.state.get_player_standings()
        # First record who made this cut (before updating remaining_players)
        self.cut_results[cut_to] = set(p.name for p in standings[:cut_to])
        # Then update remaining players
        self.remaining_players = self.cut_results[cut_to].copy()
        
        # For any cut stages that are larger than our current cut,
        # everyone who made this cut also makes those cuts
        for cut_size in self.state.cut_stages:
            if cut_size > cut_to:
                if cut_size not in self.cut_results:
                    self.cut_results[cut_size] = self.cut_results[cut_to].copy()
    
    def shuffle_lobbies_snake(self, players: List[Player]) -> List[List[Player]]:
        """Perform snake-style lobby assignment."""
        num_players = len(players)
        lobby_size = 8
        num_lobbies = (num_players + lobby_size - 1) // lobby_size
        
        # Initialize empty lobbies
        lobbies = [[] for _ in range(num_lobbies)]
        
        # Snake pattern assignment
        forward = True
        player_idx = 0
        while player_idx < num_players:
            if forward:
                for i in range(num_lobbies):
                    if player_idx < num_players:
                        lobbies[i].append(players[player_idx])
                        player_idx += 1
            else:
                for i in range(num_lobbies - 1, -1, -1):
                    if player_idx < num_players:
                        lobbies[i].append(players[player_idx])
                        player_idx += 1
            forward = not forward
        
        return lobbies
    
    def shuffle_lobbies_random(self, players: List[Player]) -> List[List[Player]]:
        """Perform random lobby assignment."""
        shuffled = players.copy()
        random.shuffle(shuffled)
        
        lobbies = []
        for i in range(0, len(shuffled), 8):
            lobbies.append(shuffled[i:i+8])
        
        return lobbies
    
    def simulate_tournament(self) -> SimulationResult:
        """Simulate the remainder of the tournament."""
        # Initialize empty cut tracking
        self.cut_results = {}
        # For any cut stages that are larger than our current player count,
        # everyone automatically makes those cuts
        for cut_size in self.state.cut_stages:
            if cut_size >= len(self.state.players):
                self.cut_results[cut_size] = self.remaining_players.copy()
        
        while not self.state.is_tournament_complete():
            # Get next action before simulating the round
            action, params = self.state.get_next_action()
            
            # Simulate current round
            self.simulate_round()
            
            # Apply action
            if action == ActionType.CUT:
                self.apply_cut(params["cut_to"])
            elif action == ActionType.SHUFFLE:
                standings = self.state.get_player_standings()
                remaining = [p for p in standings if p.name in self.remaining_players]
                
                if params["shuffle_type"] == ShuffleType.SNAKE:
                    self.shuffle_lobbies_snake(remaining)
                else:
                    self.shuffle_lobbies_random(remaining)
            elif action == ActionType.CHECKMATE:
                # Check if any player has reached checkmate points
                standings = self.state.get_player_standings()
                if standings[0].points >= 20:  # Checkmate threshold
                    break
            elif action == ActionType.END:
                break
            
            # Increment round number after applying action
            self.state.current_round += 1
        
        # Record results
        final_standings = self.state.get_player_standings()
        winner = final_standings[0] if final_standings else None
        
        return SimulationResult(
            player_name=winner.name if winner else "",
            made_cuts=self.cut_results,
            won_tournament=True if winner else False
        )

def run_simulations(
    format_file: str,
    state_file: str,
    sim_settings_file: str,
    output_file: str
) -> None:
    """Run multiple tournament simulations and aggregate results."""
    # Load simulation settings
    with open(sim_settings_file, 'r') as f:
        settings = json.load(f)
    
    num_sims = settings["num_simulations"]
    
    # Initialize counters
    player_stats: Dict[str, Dict] = {}
    cut_distributions: Dict[int, Dict[int, int]] = {}
    
    # Load initial state to get player info
    initial_state = TournamentState(format_file, state_file)
    
    # Initialize player stats with all cut stages
    for player in initial_state.players:
        player_stats[player.name] = {
            "wins": 0,
            "cuts": {cut: 0 for cut in initial_state.cut_stages},
            "total_placement": 0
        }
    
    # Run simulations
    for sim_count in range(num_sims):
        # Run simulation
        state = TournamentState(format_file, state_file)
        simulator = TournamentSimulator(state)
        result = simulator.simulate_tournament()
        
        # Record results
        for player in state.players:
            if result.player_name == player.name:
                player_stats[player.name]["wins"] += 1
            
            # Record cut results - note that we check all cut stages
            for cut_size in state.cut_stages:
                if cut_size in result.made_cuts and player.name in result.made_cuts[cut_size]:
                    player_stats[player.name]["cuts"][cut_size] += 1
            
            # Track final placement for average
            player_stats[player.name]["total_placement"] += player.avg_placement
        
        # Log progress every 1000 simulations
        if (sim_count + 1) % 1000 == 0:
            print(f"Completed {sim_count + 1} simulations")
    
    # Calculate probabilities and prepare output
    output_data = {
        "players": [
            {
                "name": name,
                "current_points": next(p.points for p in initial_state.players if p.name == name),
                "average_placement": stats["total_placement"] / num_sims,
                "prob_to_win": stats["wins"] / num_sims,
                "cut_probabilities": {
                    f"top{cut}": stats["cuts"][cut] / num_sims
                    for cut in stats["cuts"]
                }
            }
            for name, stats in player_stats.items()
        ]
    }
    
    # Add cut distributions if requested
    if settings["output_settings"]["include_cut_probabilities"]:
        output_data["cut_distributions"] = {
            f"top{cut}": [
                {
                    "points": points,
                    "probability": count / num_sims
                }
                for points, count in distributions.items()
            ]
            for cut, distributions in cut_distributions.items()
        }
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2) 
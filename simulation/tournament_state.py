from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

class ShuffleType(Enum):
    SNAKE = "snake"
    RANDOM = "random"

class ActionType(Enum):
    NOTHING = "nothing"
    SHUFFLE = "shuffle"
    CUT = "cut"
    CHECKMATE = "checkmate"
    END = "end"

@dataclass
class RoundResult:
    round: int
    lobby: str
    placement: int

@dataclass
class Player:
    name: str
    points: int
    rounds: List[RoundResult]
    tiebreakers: Dict[str, int]
    
    @property
    def avg_placement(self) -> float:
        if not self.rounds:
            return 0.0
        return sum(r.placement for r in self.rounds) / len(self.rounds)
    
    @property
    def completed_rounds(self) -> int:
        return len(self.rounds)

@dataclass
class TournamentRound:
    overall_round: int
    day: int
    round_in_day: int
    after_round: ActionType
    shuffle_type: Optional[ShuffleType] = None
    cut_to: Optional[int] = None

class TournamentState:
    def __init__(self, format_file: str, state_file: str):
        self.players: List[Player] = []
        self.rounds: List[TournamentRound] = []
        self.current_round: int = 0
        self.load_format(format_file)
        self.load_state(state_file)
    
    def load_format(self, format_file: str) -> None:
        """Load tournament format from JSON file."""
        with open(format_file, 'r') as f:
            data = json.load(f)
            
        self.tournament_name = data["tournament_name"]
        self.tiebreaker_order = data["tiebreaker_order"]
        self.cut_stages = data.get("cut_stages", [])
        
        for round_data in data["round_structure"]:
            self.rounds.append(TournamentRound(
                overall_round=round_data["overall_round"],
                day=round_data["day"],
                round_in_day=round_data["round_in_day"],
                after_round=ActionType(round_data["after_round"]),
                shuffle_type=ShuffleType(round_data["shuffle_type"]) if "shuffle_type" in round_data else None,
                cut_to=round_data.get("cut_to")
            ))
    
    def load_state(self, state_file: str) -> None:
        """Load current tournament state from JSON file."""
        with open(state_file, 'r') as f:
            data = json.load(f)
            
        for player_data in data["players"]:
            rounds = [
                RoundResult(
                    round=r["round"],
                    lobby=r["lobby"],
                    placement=r.get("placement", 0)  # Use 0 for unfinished rounds
                )
                for r in player_data["rounds"]
            ]
            
            player = Player(
                name=player_data["name"],
                points=player_data["points"],
                rounds=rounds,
                tiebreakers=player_data["tiebreakers"]
            )
            self.players.append(player)
        
        # Set current round to one less than the maximum round number
        # since we're in the middle of that round
        self.current_round = data.get("current_round", 0)
    
    def get_player_standings(self) -> List[Player]:
        """Get current player standings sorted by points and tiebreakers."""
        def tiebreaker_key(player: Player) -> Tuple:
            return tuple(
                player.tiebreakers.get(tb, 0) if tb != "avg_placement" else player.avg_placement
                for tb in self.tiebreaker_order
            )
        
        return sorted(
            self.players,
            key=lambda p: (p.points, tiebreaker_key(p)),
            reverse=True
        )
    
    def get_next_action(self) -> Tuple[ActionType, Optional[Dict]]:
        """Get the next action to be performed after the current round."""
        # Adjust for 1-based round numbers
        round_idx = self.current_round - 1
        if round_idx >= len(self.rounds):
            return ActionType.END, None
            
        current = self.rounds[round_idx]
        return current.after_round, {
            "shuffle_type": current.shuffle_type,
            "cut_to": current.cut_to
        }
    
    def is_tournament_complete(self) -> bool:
        """Check if the tournament is complete."""
        # Adjust for 1-based round numbers
        round_idx = self.current_round - 1
        return round_idx >= len(self.rounds) or (
            round_idx >= 0 and
            self.rounds[round_idx].after_round == ActionType.END
        )
    
    def save_state(self, output_file: str) -> None:
        """Save current tournament state to JSON file."""
        data = {
            "players": [
                {
                    "name": p.name,
                    "points": p.points,
                    "rounds": [
                        {
                            "round": r.round,
                            "lobby": r.lobby,
                            "placement": r.placement
                        }
                        for r in p.rounds
                    ],
                    "tiebreakers": p.tiebreakers
                }
                for p in self.players
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2) 
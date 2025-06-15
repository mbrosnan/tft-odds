from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator

class RoundStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"

class CurrentRound(BaseModel):
    overall_round: int
    day: int
    round_in_day: int
    round_status: RoundStatus

class RoundHistory(BaseModel):
    overall_round: int
    day: Optional[int] = None
    round_in_day: Optional[int] = None
    lobby: str
    placement: Optional[int] = None
    points: Optional[int] = None
    no_show: bool = False  # True if player didn't show up for this round

class Tiebreakers(BaseModel):
    firsts: int = 0
    seconds: int = 0
    thirds: int = 0
    fourths: int = 0
    fifths: int = 0
    sixths: int = 0
    sevenths: int = 0
    eighths: int = 0
    top4s: int = 0
    firsts_plus_top4s: int = 0
    total_points: int = 0  # Points that survive point resets

class EliminatedAt(BaseModel):
    overall_round: int
    reason: str

class Player(BaseModel):
    id: int
    name: str
    points: int = 0
    total_points: int = 0  # Cumulative points that survive resets
    avg_placement: float = 0.0
    completed_rounds: int = 0
    round_history: List[RoundHistory] = []
    tiebreakers: Tiebreakers = Field(default_factory=Tiebreakers)
    is_eliminated: bool = False
    eliminated_at: Optional[EliminatedAt] = None

class TourState(BaseModel):
    current_round: CurrentRound
    players: List[Player] = []
    eliminated_players: List[Player] = []

class CutRule(BaseModel):
    after_round: int
    players_remaining: int

class PostRoundActions(BaseModel):
    cut: bool = False
    cut_to: Optional[int] = None
    snake_shuffle: bool = False
    random_shuffle: bool = False
    check_victory: bool = False
    end_tournament: bool = False
    point_reset: bool = False

class RoundStructure(BaseModel):
    overall_round: int
    day: int
    round_in_day: int
    post_round_actions: PostRoundActions

class TourFormat(BaseModel):
    tournament_name: Optional[str] = None
    starting_players: Optional[int] = None
    total_rounds: Optional[int] = None
    round_structure: Optional[List[RoundStructure]] = None
    cut_rules: List[CutRule] = []
    tiebreaker_order: Optional[List[str]] = None
    checkmate_conditions: Optional[Dict] = None
    track_placement_probabilities: bool = True
    track_points_distribution: bool = True
    track_elimination_probabilities: bool = True
    
    @model_validator(mode='after')
    def convert_round_structure_to_cut_rules(self):
        """Convert round_structure to cut_rules if needed for backward compatibility."""
        # Set total_rounds from round_structure if not explicitly set
        if self.round_structure and self.total_rounds is None:
            self.total_rounds = len(self.round_structure)
        
        if self.round_structure and not self.cut_rules:
            self.cut_rules = []
            for round_info in self.round_structure:
                if round_info.post_round_actions.cut and round_info.post_round_actions.cut_to:
                    cut_rule = CutRule(
                        after_round=round_info.overall_round,
                        players_remaining=round_info.post_round_actions.cut_to
                    )
                    self.cut_rules.append(cut_rule)
            
        return self

class SimulationMode(str, Enum):
    ITERATIONS_ONLY = "iterations_only"
    TIME_ONLY = "time_only" 
    WHICHEVER_FIRST = "whichever_first"

class ProbabilityTarget(BaseModel):
    probability_name: str
    type: str  # "overall_standing", "made_cut", "tournament_winner"
    
    # For overall_standing
    comparison: Optional[str] = None  # "at", "above", "below", "at_or_above", "at_or_below"
    threshold: Optional[int] = None   # The ranking threshold
    
    # For made_cut
    players_remaining: Optional[int] = None  # Number of players in the cut

class SimSettings(BaseModel):
    max_iterations: Optional[int] = 1000
    max_time_seconds: Optional[float] = None
    mode: SimulationMode = SimulationMode.ITERATIONS_ONLY
    
    # Probability tracking configuration
    probability_targets: List[ProbabilityTarget] = [] 
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

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

class EliminatedAt(BaseModel):
    overall_round: int
    reason: str

class Player(BaseModel):
    id: int
    name: str
    points: int = 0
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

class TourFormat(BaseModel):
    total_rounds: int
    cut_rules: List[CutRule] = []
    track_placement_probabilities: bool = True
    track_points_distribution: bool = True
    track_elimination_probabilities: bool = True

class SimulationMode(str, Enum):
    ITERATIONS_ONLY = "iterations_only"
    TIME_ONLY = "time_only" 
    WHICHEVER_FIRST = "whichever_first"

class SimSettings(BaseModel):
    max_iterations: Optional[int] = 1000
    max_time_seconds: Optional[float] = None
    mode: SimulationMode = SimulationMode.ITERATIONS_ONLY 
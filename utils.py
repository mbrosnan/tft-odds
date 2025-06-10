import json
from typing import Dict
from models import TourState

def load_tour_state_from_json(file_path: str) -> TourState:
    """Load tournament state from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return TourState(**data)

def save_results_to_json(results: Dict, file_path: str):
    """Save simulation results to probabilities.json file."""
    with open(file_path, 'w') as f:
        json.dump(results, f, indent=2)

def load_json(file_path: str) -> Dict:
    """Load any JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data: Dict, file_path: str):
    """Save any data to JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2) 
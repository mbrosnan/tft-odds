import json
import os
from pathlib import Path
from typing import Dict, Any

def get_test_data_dir() -> Path:
    """Get the path to the test data directory."""
    return Path(__file__).parent / 'test_data'

def load_test_csv(filename: str) -> str:
    """Load a test CSV file from the test_data directory."""
    csv_path = get_test_data_dir() / filename
    if not csv_path.exists():
        raise FileNotFoundError(f"Test CSV file not found: {filename}")
    return str(csv_path.absolute())

def load_expected_json(filename: str) -> Dict[str, Any]:
    """Load an expected JSON output file from test_data/expected_outputs."""
    json_path = get_test_data_dir() / 'expected_outputs' / filename
    if not json_path.exists():
        raise FileNotFoundError(f"Expected JSON file not found: {filename}")
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_json_outputs(actual: Dict[str, Any], expected: Dict[str, Any]) -> bool:
    """
    Compare generated JSON with expected output.
    Returns True if they match, raises AssertionError with details if they don't.
    """
    try:
        assert actual.keys() == expected.keys(), "Top-level keys don't match"
        
        # Compare current round data
        assert actual['current_round'] == expected['current_round'], "Current round data mismatch"
        
        # Compare players
        assert len(actual['players']) == len(expected['players']), "Number of active players mismatch"
        for actual_player, expected_player in zip(
            sorted(actual['players'], key=lambda x: x['name']),
            sorted(expected['players'], key=lambda x: x['name'])
        ):
            assert actual_player == expected_player, f"Player data mismatch for {actual_player['name']}"
            
        # Compare eliminated players
        assert len(actual['eliminated_players']) == len(expected['eliminated_players']), "Number of eliminated players mismatch"
        for actual_player, expected_player in zip(
            sorted(actual['eliminated_players'], key=lambda x: x['name']),
            sorted(expected['eliminated_players'], key=lambda x: x['name'])
        ):
            assert actual_player == expected_player, f"Eliminated player data mismatch for {actual_player['name']}"
            
        return True
    except AssertionError as e:
        raise AssertionError(f"JSON comparison failed: {str(e)}") 
import unittest
import tempfile
import json
from pathlib import Path

from csv_to_tourstate import parse_csv_to_tourstate
from .test_utils import load_test_csv, load_expected_json, compare_json_outputs

class TestCSVToTourState(unittest.TestCase):
    def setUp(self):
        """Set up temporary directory for test outputs."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_path = Path(self.temp_dir.name) / "output.json"

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def _run_conversion(self, input_csv: str) -> dict:
        """Helper to run conversion and load result."""
        parse_csv_to_tourstate(input_csv, str(self.output_path))
        with open(self.output_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_in_progress_round(self):
        """Test handling of current in-progress round."""
        input_csv = load_test_csv("in_progress_round.csv")
        actual_output = self._run_conversion(input_csv)
        expected_output = load_expected_json("in_progress_round.json")
        
        self.assertTrue(compare_json_outputs(actual_output, expected_output))
        
        # Additional specific checks for in-progress round
        current_round = actual_output["current_round"]
        self.assertEqual(current_round["round_status"], "in_progress")
        
        # Check that completed games in current round are included
        for player in actual_output["players"]:
            if len(player["round_history"]) == current_round["overall_round"]:
                # This player has completed their current round game
                latest_round = player["round_history"][-1]
                self.assertEqual(latest_round["overall_round"], current_round["overall_round"])

    def test_eliminations(self):
        """Test proper handling of eliminated players."""
        input_csv = load_test_csv("with_eliminations.csv")
        actual_output = self._run_conversion(input_csv)
        expected_output = load_expected_json("with_eliminations.json")
        
        self.assertTrue(compare_json_outputs(actual_output, expected_output))
        
        # Additional checks for eliminated players
        for player in actual_output["eliminated_players"]:
            # Check that eliminated_at round is one less than the round with "cut"
            cut_round = None
            for idx, round_data in enumerate(player["round_history"]):
                if idx + 1 < len(player["round_history"]):
                    next_round = player["round_history"][idx + 1]
                    if next_round.get("lobby", "").lower() == "cut":
                        cut_round = round_data["overall_round"]
                        break
            
            self.assertIsNotNone(cut_round)
            self.assertEqual(player["eliminated_at"]["overall_round"], cut_round)
            self.assertEqual(player["eliminated_at"]["reason"], "cut")

    def test_lobby_validation(self):
        """Test lobby size and placement validation."""
        input_csv = load_test_csv("in_progress_round.csv")
        actual_output = self._run_conversion(input_csv)
        
        # Check completed rounds for lobby validation
        current_round = actual_output["current_round"]["overall_round"]
        for round_num in range(1, current_round):
            lobbies = {}
            # Gather all players in each lobby for the round
            for player in actual_output["players"] + actual_output["eliminated_players"]:
                for round_data in player["round_history"]:
                    if round_data["overall_round"] == round_num:
                        lobby = round_data["lobby"]
                        if lobby not in lobbies:
                            lobbies[lobby] = []
                        lobbies[lobby].append(round_data["placement"])
            
            # Check each lobby
            for lobby, placements in lobbies.items():
                self.assertEqual(len(placements), 8, f"Lobby {lobby} in round {round_num} doesn't have 8 players")
                self.assertEqual(len(set(placements)), 8, f"Lobby {lobby} in round {round_num} has duplicate placements")
                self.assertEqual(sorted(placements), list(range(1, 9)), f"Lobby {lobby} in round {round_num} has invalid placements")

    def test_point_calculations(self):
        """Test point calculations and averages."""
        input_csv = load_test_csv("in_progress_round.csv")
        actual_output = self._run_conversion(input_csv)
        
        # Test each player's point calculations
        for player in actual_output["players"] + actual_output["eliminated_players"]:
            # Calculate expected points
            expected_points = 0
            total_placement = 0
            for round_data in player["round_history"]:
                placement = round_data["placement"]
                points = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}[placement]
                expected_points += points
                total_placement += placement
            
            self.assertEqual(player["points"], expected_points, f"Points mismatch for {player['name']}")
            self.assertEqual(
                player["avg_placement"],
                round(total_placement / len(player["round_history"]), 2),
                f"Average placement mismatch for {player['name']}"
            )

if __name__ == '__main__':
    unittest.main() 
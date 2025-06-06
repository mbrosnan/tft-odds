import unittest
from csv_to_tourstate import get_points_for_placement, calculate_tiebreakers

class TestPointCalculations(unittest.TestCase):
    def test_points_for_placement(self):
        """Test point calculation for each placement."""
        expected_points = {
            1: 8,  # 1st place
            2: 7,  # 2nd place
            3: 6,  # 3rd place
            4: 5,  # 4th place
            5: 4,  # 5th place
            6: 3,  # 6th place
            7: 2,  # 7th place
            8: 1   # 8th place
        }
        
        for placement, expected in expected_points.items():
            self.assertEqual(
                get_points_for_placement(placement),
                expected,
                f"Wrong points for {placement}th place"
            )
    
    def test_invalid_placement_points(self):
        """Test point calculation for invalid placements."""
        invalid_placements = [0, 9, -1, 100]
        for placement in invalid_placements:
            self.assertEqual(
                get_points_for_placement(placement),
                0,
                f"Invalid placement {placement} should return 0 points"
            )
    
    def test_tiebreaker_calculation(self):
        """Test tiebreaker statistics calculation."""
        round_history = [
            {"placement": 1},  # 1st
            {"placement": 1},  # 1st
            {"placement": 3},  # 3rd
            {"placement": 4},  # 4th
            {"placement": 8},  # 8th
        ]
        
        expected_tiebreakers = {
            "firsts": 2,
            "seconds": 0,
            "thirds": 1,
            "fourths": 1,
            "fifths": 0,
            "sixths": 0,
            "sevenths": 0,
            "eighths": 1,
            "top4s": 4  # 2 firsts + 1 third + 1 fourth
        }
        
        actual_tiebreakers = calculate_tiebreakers(round_history)
        self.assertEqual(actual_tiebreakers, expected_tiebreakers)
    
    def test_empty_round_history(self):
        """Test tiebreaker calculation with empty round history."""
        expected_tiebreakers = {
            "firsts": 0,
            "seconds": 0,
            "thirds": 0,
            "fourths": 0,
            "fifths": 0,
            "sixths": 0,
            "sevenths": 0,
            "eighths": 0,
            "top4s": 0
        }
        
        actual_tiebreakers = calculate_tiebreakers([])
        self.assertEqual(actual_tiebreakers, expected_tiebreakers)
    
    def test_invalid_placement_in_history(self):
        """Test tiebreaker calculation with invalid placement in history."""
        round_history = [
            {"placement": 1},
            {"placement": None},  # Invalid placement
            {"placement": 3}
        ]
        
        expected_tiebreakers = {
            "firsts": 1,
            "seconds": 0,
            "thirds": 1,
            "fourths": 0,
            "fifths": 0,
            "sixths": 0,
            "sevenths": 0,
            "eighths": 0,
            "top4s": 2
        }
        
        actual_tiebreakers = calculate_tiebreakers(round_history)
        self.assertEqual(actual_tiebreakers, expected_tiebreakers)

if __name__ == '__main__':
    unittest.main() 
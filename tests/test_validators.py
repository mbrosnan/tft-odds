import unittest
from csv_to_tourstate import validate_lobby_data

class TestValidators(unittest.TestCase):
    def test_valid_lobby(self):
        """Test validation of a valid lobby."""
        lobby_data = {
            "A": [
                {"placement": 1}, {"placement": 2},
                {"placement": 3}, {"placement": 4},
                {"placement": 5}, {"placement": 6},
                {"placement": 7}, {"placement": 8}
            ]
        }
        # Should not raise any exceptions
        validate_lobby_data(lobby_data, 1)

    def test_invalid_lobby_size(self):
        """Test validation of a lobby with wrong number of players."""
        lobby_data = {
            "A": [
                {"placement": 1}, {"placement": 2},
                {"placement": 3}, {"placement": 4},
                {"placement": 5}, {"placement": 6},
                {"placement": 7}  # Only 7 players
            ]
        }
        with self.assertRaises(ValueError) as context:
            validate_lobby_data(lobby_data, 1)
        self.assertIn("has 7 players, expected 8", str(context.exception))

    def test_duplicate_placements(self):
        """Test validation of a lobby with duplicate placements."""
        lobby_data = {
            "A": [
                {"placement": 1}, {"placement": 2},
                {"placement": 2}, {"placement": 4},  # Duplicate 2nd place
                {"placement": 5}, {"placement": 6},
                {"placement": 7}, {"placement": 8}
            ]
        }
        with self.assertRaises(ValueError) as context:
            validate_lobby_data(lobby_data, 1)
        self.assertIn("has duplicate placements", str(context.exception))

    def test_multiple_lobbies(self):
        """Test validation of multiple lobbies."""
        lobby_data = {
            "A": [
                {"placement": 1}, {"placement": 2},
                {"placement": 3}, {"placement": 4},
                {"placement": 5}, {"placement": 6},
                {"placement": 7}, {"placement": 8}
            ],
            "B": [
                {"placement": 1}, {"placement": 2},
                {"placement": 3}, {"placement": 4},
                {"placement": 5}, {"placement": 6},
                {"placement": 7}, {"placement": 8}
            ]
        }
        # Should not raise any exceptions
        validate_lobby_data(lobby_data, 1)

    def test_empty_lobby(self):
        """Test validation of an empty lobby."""
        lobby_data = {
            "A": []
        }
        # Should not raise any exceptions as empty lobbies are skipped
        validate_lobby_data(lobby_data, 1)

if __name__ == '__main__':
    unittest.main() 
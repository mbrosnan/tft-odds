# Bug Fix Summary: Unrealistic Probabilities After Point Reset

## Issue Description
Players who won just the first round (8 points) were showing unrealistically high probabilities:
- 40+% chance at top 4 
- 95+% chance at making top 16

This was happening in tournaments with point resets (e.g., after round 6 in the TT3 tournament format).

## Root Cause
The simulation was incorrectly handling tiebreakers after point resets:

1. When a point reset occurs (e.g., after round 6), the simulation correctly:
   - Resets player points to 0 ✓
   - Resets tiebreakers to 0 ✓

2. However, when the next round is simulated:
   - `simulate_next_round()` calls `update_player_stats()`
   - `update_player_stats()` calls `calculate_tiebreakers()`
   - `calculate_tiebreakers()` was recalculating tiebreakers from the ENTIRE round history
   - This effectively undid the tiebreaker reset!

3. Result: Players who performed well in rounds 1-6 kept their tiebreaker advantage even after the reset, giving them unfairly high probabilities of making future cuts.

## Fix Applied
Modified two functions in `simulation.py`:

1. **`calculate_tiebreakers()`**: Added a `last_reset_round` parameter to only count rounds after the most recent point reset for tiebreaker calculations.

2. **`update_player_stats()`**: Added logic to determine the last reset round and pass it to `calculate_tiebreakers()`.

3. **`get_last_reset_round()`**: Added new helper function to find the most recent point reset.

## Code Changes
```python
# Old: Counted all rounds for tiebreakers
def calculate_tiebreakers(round_history: List[RoundHistory]) -> Dict[str, int]:
    # ... counted all rounds ...

# New: Only counts rounds after the last reset
def calculate_tiebreakers(round_history: List[RoundHistory], last_reset_round: int = 0) -> Dict[str, int]:
    # ... only counts rounds where round_data.overall_round > last_reset_round ...
```

## Impact
After the fix:
- Tiebreakers are correctly reset and only accumulate from rounds after the reset
- Players with early success don't have an unfair advantage after point resets
- Probabilities should be more realistic and reflect the actual tournament dynamics

## Testing
Created `test_point_reset_fix.py` to verify the fix works correctly. The test creates a scenario with players at different point levels and verifies that their probabilities are reasonable after the point reset.
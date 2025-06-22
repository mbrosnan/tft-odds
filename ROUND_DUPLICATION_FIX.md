# Round Duplication Fix Summary

## Problem
When simulating round 2, the placements from round 1 were being duplicated into round 2, causing all players to have exactly double their round 1 points after round 2.

## Root Cause
The `update_player_stats` function in `simulation.py` was not correctly identifying which rounds came from the CSV file vs which rounds were being simulated. It was incorrectly calculating that all rounds should be included in the "new simulation points" calculation.

## Solution
1. **Added tracking in CSV parser**: Modified `csv_to_tourstate.py` to track the highest round that has placement data from the CSV file by adding a `max_csv_round` field to each player.

2. **Added field to Player model**: Updated `models.py` to include the `max_csv_round` field in the Player model so it persists through JSON serialization.

3. **Fixed header parsing**: Corrected the logic for detecting the "Prior Day Points" column by checking the actual header row (line 7, index 6) instead of the first player data row.

4. **Updated simulation logic**: Modified `update_player_stats` in `simulation.py` to use `max_csv_round` to correctly identify which rounds are new simulation rounds vs existing CSV data.

## Files Modified
1. `csv_to_tourstate.py`:
   - Added `max_csv_round` tracking when parsing player data
   - Fixed prior_day_points column detection logic

2. `models.py`:
   - Added `max_csv_round: Optional[int] = Field(default=None)` to Player model

3. `simulation.py`:
   - Updated `update_player_stats` to check for `max_csv_round` field
   - Improved fallback logic for cases where the field isn't set

## Testing
Created test scripts to verify:
- CSV parsing correctly sets `max_csv_round` 
- Round 2 simulation generates new random placements
- Points are correctly calculated as sum of R1 + R2, not 2×R1

## Result
Players now correctly accumulate points from each round, with each round having independent placements.
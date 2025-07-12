# Split Cut Implementation

## Overview
The split cut feature has been successfully implemented, allowing tournaments to have more complex advancement patterns where:
- Top X players can advance directly to a future round (skipping intermediate rounds)
- Bottom Y players are eliminated
- The remaining players continue to the next round
- X + Y must be divisible by 8 to maintain full lobbies

## Changes Made

### 1. Data Model Changes (models.py)
- Added new fields to `PostRoundActions`:
  - `top_x_advance`: Number of top players advancing to a future round
  - `advance_to_round`: Target round for advancement
  - `bottom_y_eliminated`: Number of bottom players eliminated
- Added validation to ensure X + Y is divisible by 8
- Added `advancing_players` field to `TourState` to track players advancing to future rounds
- Added `advancing_to_round` field to `Player` to mark advancing players

### 2. Simulation Logic (simulation.py)
- Created `apply_split_cuts()` function to handle split cut logic
- Modified `process_post_round_actions()` to check for and apply split cuts
- Updated `advance_to_next_round()` to re-integrate advancing players when their target round is reached
- Added proper round history tracking for advancing players with "advancing" lobby indicator

### 3. Backward Compatibility
- The existing `cut` and `cut_to` fields remain functional for simple cuts
- Split cuts are only applied when `top_x_advance` is specified
- Existing tournament formats continue to work without modification

## Usage Example

```json
{
  "overall_round": 6,
  "day": 1,
  "round_in_day": 6,
  "post_round_actions": {
    "cut": true,
    "cut_to": null,
    "top_x_advance": 4,
    "advance_to_round": 9,
    "bottom_y_eliminated": 4,
    "snake_shuffle": true,
    "random_shuffle": false,
    "check_victory": false,
    "end_tournament": false,
    "point_reset": false
  }
}
```

This configuration will:
1. Take the top 4 players and advance them directly to round 9
2. Eliminate the bottom 4 players
3. The remaining 24 players (32 - 4 - 4 = 24) continue to round 7

## Implementation Details

### Player Tracking
- Advancing players are stored in `TourState.advancing_players[round_number]`
- They have placeholder "advancing" lobby entries for skipped rounds
- When the target round is reached, they're re-integrated into the active player pool

### Cut Threshold
- The cut threshold is calculated between continuing and eliminated players
- Advancing players are not considered in the cut threshold calculation

### Final Positions
- Eliminated players receive final positions starting after continuing + advancing players
- This ensures proper tournament standings

## Testing
A test script (`test_split_cuts.py`) has been created to verify the functionality. The test confirms:
- Correct player distribution (advancing, continuing, eliminated)
- Proper round history tracking
- Validation of X + Y divisibility by 8
- Re-integration of advancing players

## Future Considerations
- UI components would need to be added if a tournament configuration interface is desired
- Currently, tournament formats must be edited manually in JSON files
- The feature could be extended to support multiple advancement targets in a single round
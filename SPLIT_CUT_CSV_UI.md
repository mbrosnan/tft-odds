# Split Cut CSV and UI Documentation

## CSV File Representation

### How Advancing Players are Shown in CSV

When a player advances to a future round (skipping intermediate rounds), the CSV file will show:

1. **Lobby Column**: "advancing" - This special lobby name indicates the player is advancing to a future round
2. **Placement Column**: Empty - No placement since they're not playing these rounds

Example CSV structure for a split cut at Round 6 where top 4 advance to Round 9:

```
Round:        6      7      8      9
Player_1:  1,3    advancing advancing 2,5
Player_2:  1,4    advancing advancing 2,6
Player_3:  2,1    advancing advancing 1,7
Player_4:  2,2    advancing advancing 1,8
Player_5:  3,5    4,2      3,4      2,1
...
Player_29: 4,5    cut      cut      cut
Player_30: 4,6    cut      cut      cut
```

In this example:
- Players 1-4 finished in the top 4 of Round 6 and advance directly to Round 9
- Players 5-28 continue playing in Rounds 7 and 8
- Players 29-32 were eliminated after Round 6

### Reading Split Cuts from CSV

When importing a CSV with split cuts:
- The system recognizes "advancing" as a special lobby indicator
- Players with "advancing" status are tracked separately until their target round
- The round where they return to normal lobbies indicates their advancement target

## Streamlit UI Display

### Cut Probabilities Tab Enhancement

The Cut Probabilities tab now shows split cuts with separate sections:

1. **Split Cut Header**: "Round X - Split Cut"

2. **Three-Column Summary**:
   - 🚀 **Top X advance** to Round Y
   - ➡️ **Z continue** to next round  
   - ❌ **Bottom W eliminated**

3. **Advancement Threshold Section**:
   - Shows statistics for the threshold between advancing and continuing players
   - Mean, most common, range, and distribution
   - Clean advance vs tiebreaker advance percentages

4. **Elimination Threshold Section**:
   - Shows statistics for the threshold between continuing and eliminated players
   - Same metrics as advancement threshold
   - Clean cut vs tiebreaker cut percentages

### Example UI Display

```
### Round 6 - Split Cut

🚀 Top 4 advance to Round 9 | ➡️ 24 continue to next round | ❌ Bottom 4 eliminated

#### 🎯 Advancement Threshold (Top Players)
Mean: 28.5 | Most Common: 28.5 | Range: 27.0 - 30.0 | Most Common %: 45.2%

🎯 Clean advances: 78.3% | ⚔️ Tiebreaker advances: 21.7%

#### 💀 Elimination Threshold (Bottom Players)  
Mean: 12.5 | Most Common: 12.5 | Range: 11.0 - 14.0 | Most Common %: 52.1%

🎯 Clean cuts: 82.5% | ⚔️ Tiebreaker cuts: 17.5%
```

## Implementation Details

### Tracking in Simulation

The simulation now tracks:
- `advancement_thresholds`: Points needed to advance to future round
- `cut_thresholds`: Points needed to avoid elimination
- Both are calculated and stored separately for split cuts

### Statistics Calculation

For split cuts, the system calculates:
1. **Advancement statistics**: Based on the threshold between top X and continuing players
2. **Elimination statistics**: Based on the threshold between continuing and bottom Y players
3. Both include mean, range, distribution, and cut type analysis

### Backward Compatibility

- Regular cuts continue to work as before
- Split cuts are only processed when `top_x_advance` is specified
- UI automatically detects cut type and displays appropriately
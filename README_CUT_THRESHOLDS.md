# Cut Threshold Tracking Feature

## Overview
The simulation now tracks cut thresholds for each elimination cut that occurs during tournaments. This provides valuable insights into the point requirements needed to advance through cuts.

## How It Works

### Cut Threshold Calculation
For each cut, the system calculates a threshold value:

1. **Tiebreaker Situations (Whole Numbers)**: When multiple players have the same point total at the cut line, tiebreakers are used to determine who advances. The threshold is set to the whole number point value.
   - Example: 8th place has 17 points, 9th place has 17 points → Cut threshold: **17.0 points** (tiebreakers used)

2. **Clean Cuts (Half Numbers)**: When there's a clear point gap between the last advancing player and first eliminated player, no tiebreakers are needed. The threshold is set to the midpoint.
   - Example: 8th place has 20 points, 9th place has 17 points → Cut threshold: **18.5 points** (clean cut)

### Data Collection
During simulation runs, the system:
- Tracks every cut threshold across all simulations
- Calculates statistical distributions (mean, min, max, most common)
- Analyzes the frequency of clean cuts vs tiebreaker cuts
- Stores results in the JSON output file

## Usage

### Running Simulations
Cut thresholds are automatically tracked when running probability simulations:

```python
# Enable probability tracking in simulation.py
PROBABILITY_TRACKING_TEST = True

# Run simulation
python simulation.py
```

### Viewing Results

#### Console Output
During simulation, cut information is displayed:
```
Cut threshold: 17 points (tiebreakers used)
Cut threshold: 18.5 points (clean cut)
```

#### JSON Results
Cut statistics are saved in `test_probabilities.json`:
```json
{
  "cut_threshold_statistics": {
    "round_4_cut_to_8": {
      "mean": 18.1,
      "min": 16.0,
      "max": 21.0,
      "count": 100,
      "most_common": {
        "threshold": 18.0,
        "probability": 0.34,
        "count": 34
      },
      "distribution": {
        "17.5": 0.13,
        "18.5": 0.18,
        "18.0": 0.34
      }
    }
  }
}
```

#### Web Interface
View cut analysis in the Streamlit app:
```bash
streamlit run app.py
```

Navigate to the "🔪 Cut Thresholds" tab to see:
- Mean threshold values
- Distribution charts
- Clean cut vs tiebreaker analysis
- Detailed breakdown tables

## Interpretation

### Key Metrics
- **Mean Threshold**: Average points needed to survive the cut
- **Most Common**: The threshold value that occurs most frequently
- **Distribution**: Shows variability in cut requirements
- **Clean Cut %**: Percentage of cuts that didn't require tiebreakers

### Strategic Insights
- **High Variability**: Wide threshold ranges indicate unpredictable cut lines
- **Frequent Tiebreakers**: Many whole-number thresholds suggest tight competition
- **Safe Targets**: Use upper range values for conservative advancement strategies

## Example Analysis
From a 100-simulation run:
- **Round 4 cut to 8 players**:
  - Mean threshold: 18.1 points
  - Range: 16.0 - 21.0 points
  - Most common: 18.0 points (34% of simulations)
  - Clean cuts: 35% of scenarios
  - Tiebreaker cuts: 65% of scenarios

This suggests that scoring 18+ points provides good odds of making top 8, but the high frequency of tiebreakers (65%) indicates very competitive cuts where placement averages matter significantly. 
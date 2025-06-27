#!/usr/bin/env python3
"""Test to verify the round 12 cut threshold bug"""

import json
from csv_to_tourstate import parse_csv_to_tourstate
from simulation import simulate_tournament, load_tour_format_from_json, load_sim_settings_from_json
from models import SimSettings, SimulationMode

# Convert CSV to tour state
parse_csv_to_tourstate(
    "s14_na_gs/test/tour_state_pre_round1.csv",
    "temp_tour_state.json",
    "s14_na_gs/tour_format.json"
)

# Load tour state
with open("temp_tour_state.json", 'r') as f:
    tour_state_data = json.load(f)
    
from models import TourState
tour_state = TourState(**tour_state_data)

# Load tour format
tour_format = load_tour_format_from_json("s14_na_gs/tour_format.json")

# Create minimal sim settings for one iteration
sim_settings = SimSettings(
    max_iterations=1,
    mode=SimulationMode.ITERATIONS_ONLY,
    debug_enabled=True
)

print("Running one simulation iteration with debug enabled...")
print("Check simulation_debug.txt for round 12 details")

# Run simulation
results, _ = simulate_tournament(tour_format, tour_state, sim_settings)

# Check cut thresholds
if "cut_thresholds" in results:
    print("\nCut thresholds found:")
    for cut_name, thresholds in results["cut_thresholds"].items():
        if thresholds:
            print(f"  {cut_name}: {thresholds[0]}")

# Clean up
import os
os.remove("temp_tour_state.json")
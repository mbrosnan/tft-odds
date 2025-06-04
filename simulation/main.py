import argparse
import os
from .simulator import run_simulations

def main():
    parser = argparse.ArgumentParser(description="Run TFT tournament simulations")
    parser.add_argument("--format", required=True, help="Path to tournament format JSON file")
    parser.add_argument("--state", required=True, help="Path to tournament state JSON file")
    parser.add_argument("--settings", required=True, help="Path to simulation settings JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    
    args = parser.parse_args()
    
    # Validate file paths
    for path in [args.format, args.state, args.settings]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
    
    # Run simulations
    run_simulations(
        format_file=args.format,
        state_file=args.state,
        sim_settings_file=args.settings,
        output_file=args.output
    )

if __name__ == "__main__":
    main() 
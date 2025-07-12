#!/usr/bin/env python3
"""
process_round.py - Streamlined workflow for processing tournament rounds

This script automates the entire local workflow:
1. Takes a CSV file with tournament results
2. Runs simulation with appropriate settings
3. Moves results from staging to live
4. Optionally shows a preview of changes
"""

import argparse
import os
import sys
import subprocess
import json
import shutil
from pathlib import Path

# Default paths for NA Golden Spatula tournament
DEFAULT_TOUR_FORMAT = "s14_crown/tour_format.json"
DEFAULT_SIM_SETTINGS = "s14_crown/sim_settings.json"


def get_python_command():
    """Get the correct python command for this system."""
    # Try python3 first (common on Linux/Mac)
    try:
        subprocess.run(['python3', '--version'], capture_output=True, check=True)
        return 'python3'
    except:
        pass
    
    # Fall back to python
    try:
        subprocess.run(['python', '--version'], capture_output=True, check=True)
        return 'python'
    except:
        pass
    
    # Last resort - use sys.executable
    return sys.executable


def run_command(cmd, description, show_output=False):
    """Run a shell command and handle errors."""
    print(f"\n{description}...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        if show_output:
            # Show real-time output for long-running commands
            result = subprocess.run(cmd, text=True, check=True)
            return True
        else:
            # Capture output for short commands
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout:
                print(result.stdout)
            return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed!")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Error message: {e.stderr}")
        return False


def validate_files(csv_path, tour_format_path, sim_settings_path):
    """Validate that all required files exist."""
    files_to_check = [
        ("CSV file", csv_path),
        ("Tour format", tour_format_path),
        ("Sim settings", sim_settings_path)
    ]
    
    all_valid = True
    for file_type, file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"ERROR: {file_type} not found: {file_path}")
            all_valid = False
        else:
            print(f"✓ {file_type}: {file_path}")
    
    return all_valid


def get_round_info(csv_path):
    """Try to extract round information from CSV filename."""
    filename = os.path.basename(csv_path)
    # Common patterns: round_1.csv, r1.csv, after_r1.csv, etc.
    import re
    match = re.search(r'r(?:ound)?[\s_-]?(\d+)', filename, re.IGNORECASE)
    if match:
        return f"round {match.group(1)}"
    return "current round"


def preview_changes():
    """Show a preview of what will be deployed."""
    print("\n" + "="*60)
    print("PREVIEW OF CHANGES")
    print("="*60)
    
    # Check if probabilities.json exists in staging
    prob_file = "staging/probabilities.json"
    if os.path.exists(prob_file):
        with open(prob_file, 'r') as f:
            data = json.load(f)
        
        # Show simulation info
        if "simulation_info" in data:
            info = data["simulation_info"]
            print(f"\nSimulation completed:")
            print(f"  - Iterations: {info.get('total_iterations', 'N/A')}")
            print(f"  - Current round: {info.get('current_round', 'N/A')}")
            print(f"  - Active players: {info.get('active_players', 'N/A')}")
        
        # Show top 5 players by first probability target
        if "player_probabilities" in data:
            players = data["player_probabilities"]
            if players:
                # Find first actual probability target (skip metadata fields)
                first_target = None
                first_player = next(iter(players.values()))
                for key, value in first_player.items():
                    if isinstance(value, dict) and "probability" in value:
                        first_target = key
                        break
                
                if first_target:
                    print(f"\nTop 5 players by '{first_target}':")
                    
                    # Sort players by this probability
                    player_probs = []
                    for name, probs in players.items():
                        if first_target in probs and isinstance(probs[first_target], dict):
                            prob = probs[first_target].get("probability", 0)
                            player_probs.append((name, prob))
                    
                    player_probs.sort(key=lambda x: x[1], reverse=True)
                    for i, (name, prob) in enumerate(player_probs[:5]):
                        print(f"  {i+1}. {name}: {prob:.1%}")
    else:
        print("WARNING: No probabilities.json found in staging/")
    
    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Process a tournament round: run simulation and deploy results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process round 1 with default NA GS settings
  python process_round.py round_1.csv
  
  # Process with custom tournament format
  python process_round.py round_3.csv --tour-format tc3day3/tour_format.json
  
  # Skip deployment to live (stay in staging)
  python process_round.py round_5.csv --no-deploy
  
  # Skip preview before deployment
  python process_round.py round_2.csv --no-preview
  
  # Auto-deploy to EC2 after going live
  python process_round.py round_4.csv --auto-deploy
        """
    )
    
    parser.add_argument('csv_file', help='Path to CSV file with tournament results')
    parser.add_argument('--tour-format', default=DEFAULT_TOUR_FORMAT,
                        help=f'Path to tour format JSON (default: {DEFAULT_TOUR_FORMAT})')
    parser.add_argument('--sim-settings', default=DEFAULT_SIM_SETTINGS,
                        help=f'Path to simulation settings JSON (default: {DEFAULT_SIM_SETTINGS})')
    parser.add_argument('--no-deploy', action='store_true',
                        help='Skip deployment to live folder (keep in staging only)')
    parser.add_argument('--no-preview', action='store_true',
                        help='Skip preview of changes before deployment')
    parser.add_argument('--auto-deploy', action='store_true',
                        help='Automatically run deploy.py to push to EC2 after going live')
    parser.add_argument('--output', default='staging/probabilities.json',
                        help='Output path for probabilities (default: staging/probabilities.json)')
    
    args = parser.parse_args()
    
    # Validate all files exist
    print("Validating input files...")
    if not validate_files(args.csv_file, args.tour_format, args.sim_settings):
        sys.exit(1)
    
    # Get round info for display
    round_info = get_round_info(args.csv_file)
    
    print(f"\n{'='*60}")
    print(f"PROCESSING {round_info.upper()}")
    print(f"{'='*60}")
    
    # Step 1: Run simulation
    python_cmd = get_python_command()
    sim_cmd = [
        python_cmd, 'simulation.py',
        '--csv', args.csv_file,
        '--tour-format', args.tour_format,
        '--sim-settings', args.sim_settings,
        '--output', args.output
    ]
    
    if not run_command(sim_cmd, "Running simulation", show_output=True):
        print("\nSimulation failed! Aborting.")
        sys.exit(1)
    
    # Step 2: Convert tour state to CSV for staging
    print("\nPreparing tour state CSV...")
    
    # We need to get the tour state from the CSV file
    # The simulation doesn't output a tour_state.json, so we'll copy the input CSV
    staging_csv = "staging/tour_state.csv"
    os.makedirs("staging", exist_ok=True)
    
    try:
        shutil.copy2(args.csv_file, staging_csv)
        print(f"✓ Copied tour state to {staging_csv}")
    except Exception as e:
        print(f"ERROR: Failed to copy CSV to staging: {e}")
        sys.exit(1)
    
    # Step 3: Show preview if requested
    if not args.no_preview:
        preview_changes()
    
    # Step 4: Deploy to live if requested
    if not args.no_deploy:
        # Check which go_live script to use
        if sys.platform.startswith('win'):
            go_live_cmd = ['cmd', '/c', 'go_live.bat']
        else:
            go_live_cmd = ['./go_live.sh']
        
        if not run_command(go_live_cmd, "Deploying to live"):
            print("\nWARNING: Deployment to live failed!")
            print("Results are still available in staging/")
            sys.exit(1)
        
        print("\n✅ SUCCESS! Results are now live.")
        
        # Auto-deploy to EC2 if requested
        if args.auto_deploy:
            print("\n" + "="*60)
            print("AUTO-DEPLOYING TO EC2")
            print("="*60)
            
            # Get the correct python command
            python_cmd = get_python_command()
            deploy_cmd = [python_cmd, 'deploy.py']
            
            if run_command(deploy_cmd, "Deploying to EC2", show_output=True):
                print("\n✅ DEPLOYMENT COMPLETE! Results are live on EC2.")
            else:
                print("\n⚠️  WARNING: EC2 deployment failed!")
                print("You can manually run 'python deploy.py' to retry.")
        else:
            print("\nNext steps:")
            print("  1. Run 'streamlit run app.py' to preview locally")
            print("  2. Run 'python deploy.py' to push to production server")
    else:
        print("\n✅ Simulation complete! Results saved to staging/")
        print("Run './go_live.sh' (or .\\go_live.bat on Windows) when ready to deploy.")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
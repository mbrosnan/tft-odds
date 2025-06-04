from simulation.simulator import run_simulations
import sys

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python run_sim.py <format_file> <state_file> <settings_file> <output_file>")
        sys.exit(1)
        
    format_file = sys.argv[1]
    state_file = sys.argv[2]
    settings_file = sys.argv[3]
    output_file = sys.argv[4]
    
    run_simulations(
        format_file=format_file,
        state_file=state_file,
        sim_settings_file=settings_file,
        output_file=output_file
    ) 
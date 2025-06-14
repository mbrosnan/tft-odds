import streamlit as st
import pandas as pd
import json
import argparse
import sys
from typing import Dict, Any, List
import csv

def load_probability_data(filename: str = "probabilities.json") -> Dict[str, Any]:
    """Load probability data from the new JSON format."""
    try:
        with open(filename) as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Could not find {filename}. Please run the simulation first to generate probability data.")
        return None
    except json.JSONDecodeError:
        st.error(f"Invalid JSON format in {filename}")
        return None

def get_points_for_placement(placement: int) -> int:
    """Convert placement to points using standard TFT scoring."""
    points_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
    return points_map.get(placement, 0)

def load_csv_results(csv_file: str) -> pd.DataFrame:
    """Load current tournament results from CSV file."""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = list(csv.reader(f))
        
        # Parse metadata
        current_round = int(lines[0][1])
        
        # Parse round structure from header rows
        day_row = lines[3]  # Day header row
        round_row = lines[4]  # Round header row
        
        player_start = 7
        
        # Process player data
        results_data = []
        
        for row in lines[player_start:]:
            if not row[1]:  # Skip empty rows
                continue
            
            player_data = {
                "Player": row[1],
                "Current Points": 0,
                "Completed Rounds": 0,
                "Average Placement": 0.0,
                "Is Eliminated": False,
                "Round History": []
            }
            
            # Process each round
            total_points = 0
            total_placement = 0
            completed_rounds = 0
            
            # Each round has 3 columns (Lobby, Placement, spacer)
            for round_num in range(1, current_round + 1):
                col_offset = (round_num * 3) - 1  # Starting column for round data
                
                if col_offset >= len(row):
                    break
                    
                lobby = row[col_offset] if col_offset < len(row) else ""
                placement_str = row[col_offset + 1] if col_offset + 1 < len(row) else ""
                
                # Check for cut marker
                if lobby.lower() == 'cut':
                    player_data["Is Eliminated"] = True
                    continue
                
                # Skip if no lobby data for this round
                if not lobby:
                    continue
                
                # Handle in-progress rounds (lobby exists but no placement)
                if not placement_str:
                    player_data["Round History"].append({
                        "Round": round_num,
                        "Lobby": lobby,
                        "Placement": None,
                        "Points": None,
                        "Status": "In Progress"
                    })
                    continue
                
                # Handle no-show entries
                if placement_str.lower() == "no-show":
                    player_data["Round History"].append({
                        "Round": round_num,
                        "Lobby": lobby,
                        "Placement": "No-Show",
                        "Points": 0,
                        "Status": "No-Show"
                    })
                    continue
                
                try:
                    placement = int(placement_str)
                    points = get_points_for_placement(placement)
                    total_points += points
                    total_placement += placement
                    completed_rounds += 1
                    
                    player_data["Round History"].append({
                        "Round": round_num,
                        "Lobby": lobby,
                        "Placement": placement,
                        "Points": points,
                        "Status": "Completed"
                    })
                    
                except ValueError:
                    continue
            
            player_data["Current Points"] = total_points
            player_data["Completed Rounds"] = completed_rounds
            player_data["Average Placement"] = round(total_placement / completed_rounds, 2) if completed_rounds > 0 else 0.0
            
            results_data.append(player_data)
        
        # Convert to DataFrame and sort by points (descending), then by average placement (ascending)
        df = pd.DataFrame(results_data)
        if not df.empty:
            df = df.sort_values(["Current Points", "Average Placement"], ascending=[False, True])
            df.reset_index(drop=True, inplace=True)
            df.index += 1  # Start ranking from 1
        
        return df
        
    except Exception as e:
        st.error(f"Error loading CSV file: {str(e)}")
        return pd.DataFrame()

def enhance_results_with_probabilities(results_df: pd.DataFrame, player_probabilities: Dict) -> pd.DataFrame:
    """Add probability data to the results dataframe."""
    if results_df.empty or not player_probabilities:
        return results_df
    
    enhanced_df = results_df.copy()
    
    # Add tiebreaker columns
    first_player_probs = next(iter(player_probabilities.values()), {})
    if "tiebreakers" in first_player_probs:
        tiebreaker_order = first_player_probs.get("tiebreaker_order", [])
        
        # Add tiebreaker columns
        for tiebreaker in tiebreaker_order:
            enhanced_df[tiebreaker] = 0
        
        # Fill in tiebreaker data
        for idx, row in enhanced_df.iterrows():
            player_name = row["Player"]
            if player_name in player_probabilities:
                player_data = player_probabilities[player_name]
                if "tiebreakers" in player_data:
                    for tiebreaker in tiebreaker_order:
                        if tiebreaker in player_data["tiebreakers"]:
                            enhanced_df.at[idx, tiebreaker] = player_data["tiebreakers"][tiebreaker]
    
    # Add key probability columns
    prob_columns_to_add = ["won_tournament", "finished_top_4", "finished_top_54"]
    
    for prob_col in prob_columns_to_add:
        enhanced_df[f"{prob_col}_probability"] = 0.0
        
        for idx, row in enhanced_df.iterrows():
            player_name = row["Player"]
            if player_name in player_probabilities and prob_col in player_probabilities[player_name]:
                prob_value = player_probabilities[player_name][prob_col]["probability"] * 100
                enhanced_df.at[idx, f"{prob_col}_probability"] = prob_value
    
    return enhanced_df

# Parse command line arguments
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='TFT Tournament Probability Viewer')
    parser.add_argument('--probabilities', type=str, default='probabilities.json', 
                       help='Path to probabilities JSON file (default: probabilities.json)')
    parser.add_argument('--csv', type=str, help='Path to tournament CSV file for current results')
    return parser.parse_known_args()[0]  # Use parse_known_args to ignore streamlit args

# Parse arguments
args = parse_args()

# Load probability data
player_probabilities = {}
cut_threshold_stats = {}

if args.probabilities:
    data = load_probability_data(args.probabilities)
    if data:
        player_probabilities = data.get("player_probabilities", {})
        cut_threshold_stats = data.get("cut_threshold_statistics", {})

# Load CSV results if provided
csv_results_df = pd.DataFrame()
if args.csv:
    csv_results_df = load_csv_results(args.csv)

def create_player_dataframe(player_probabilities: Dict[str, Dict[str, Dict[str, float]]], max_tiebreakers: int = 3) -> pd.DataFrame:
    """Convert player probabilities to a pandas DataFrame for display."""
    table_data = []
    
    # Get tiebreaker order from the first player (they should all have the same order)
    tiebreaker_order = []
    first_player_data = next(iter(player_probabilities.values()), {})
    if "tiebreaker_order" in first_player_data:
        tiebreaker_order = first_player_data["tiebreaker_order"][:max_tiebreakers]
    
    for player_name, probabilities in player_probabilities.items():
        row = {"Player": player_name}
        
        # Add current points if available
        if "current_points" in probabilities:
            row["Current Points"] = probabilities["current_points"]
        
        # Add tiebreakers if available
        if "tiebreakers" in probabilities and tiebreaker_order:
            player_tiebreakers = probabilities["tiebreakers"]
            for tiebreaker_name in tiebreaker_order:
                # Create a readable column name for the tiebreaker
                tiebreaker_display_name = tiebreaker_name.replace("_", " ").title()
                tiebreaker_value = player_tiebreakers.get(tiebreaker_name, 0)
                row[tiebreaker_display_name] = tiebreaker_value
        
        # Extract probability values (keep as numeric for sorting)
        for prob_name, prob_data in probabilities.items():
            # Skip the metadata fields we already processed
            if prob_name in ["current_points", "tiebreakers", "tiebreaker_order"]:
                continue
                
            if isinstance(prob_data, dict) and "probability" in prob_data:
                percentage = prob_data.get("probability", 0) * 100
                clean_name = prob_name.replace("_", " ").title()
                row[clean_name] = percentage  # Store as numeric for proper sorting
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    
    # Sort by current points first (if available), then by the first probability column
    if "Current Points" in df.columns:
        df = df.sort_values(by="Current Points", ascending=False).reset_index(drop=True)
    elif len(df.columns) > 1:
        # Find first probability column (skip Player, Current Points, and tiebreaker columns)
        prob_columns = [col for col in df.columns if col not in ["Player", "Current Points"] and not any(keyword in col.lower() for keyword in ["firsts", "top4s", "seconds", "thirds", "fourths", "fifths", "sixths", "sevenths", "eighths"])]
        if prob_columns:
            first_prob_col = prob_columns[0]
            df = df.sort_values(by=first_prob_col, ascending=False).reset_index(drop=True)
    
    # Don't format here - keep numeric for interactive sorting
    return df

def get_probability_charts_data(player_probabilities: Dict[str, Dict[str, Dict[str, float]]], prob_type: str) -> pd.DataFrame:
    """Extract data for a specific probability type for charting."""
    chart_data = []
    
    for player_name, probabilities in player_probabilities.items():
        if prob_type in probabilities:
            prob_data = probabilities[prob_type]
            # Skip metadata fields - only process actual probability data
            if isinstance(prob_data, dict) and "probability" in prob_data:
                chart_data.append({
                    "Player": player_name,
                    "Probability": prob_data.get("probability", 0) * 100,
                    "Count": prob_data.get("count", 0),
                    "Total": prob_data.get("total", 0)
                })
    
    # Sort by probability descending
    chart_data.sort(key=lambda x: x["Probability"], reverse=True)
    return pd.DataFrame(chart_data)

# Streamlit App
st.set_page_config(page_title="TFT Tournament Probabilities", page_icon="🎯", layout="wide")

# Load data first to get tournament info
data = load_probability_data(args.probabilities)

if data is not None:
    metadata = data.get("simulation_metadata", {})
    
    # Display tournament title and round info
    tournament_title = metadata.get("tournament_title", "Set 14 NA Tacticians Trials #3")
    current_round_info = metadata.get("current_round", {})
    
    st.title(f" {tournament_title}")
    
    if current_round_info:
        round_num = current_round_info.get("overall_round", "?")
        round_status = current_round_info.get("round_status", "unknown")
        day = current_round_info.get("day", "?")
        round_in_day = current_round_info.get("round_in_day", "?")
        
        # Format round status for display
        status_display = round_status.replace("_", " ").title()
        
        st.subheader(f"Round {round_num} (Day {day}, Round {round_in_day}) - {status_display}")
    
    st.markdown("---")

else:
    st.title("🎯 TFT Tournament Probability Analysis")
    st.markdown("---")

# Load data (keeping original structure for rest of code)
if data is not None:
    player_probabilities = data.get("player_probabilities", {})
    cut_threshold_stats = data.get("cut_threshold_statistics", {})
    
    # Sidebar with simulation info
    st.sidebar.header("Simulation Info")
    if metadata:
        st.sidebar.metric("Total Simulations", metadata.get("total_simulations", "N/A"))
        st.sidebar.metric("Simulation Time", f"{metadata.get('simulation_time_seconds', 0):.1f}s")
        
        targets = metadata.get("probability_targets", [])
        if targets:
            st.sidebar.subheader("Tracked Probabilities")
            for target in targets:
                st.sidebar.write(f"• {target.get('probability_name', '').replace('_', ' ').title()}")
        
        if cut_threshold_stats:
            st.sidebar.subheader("Cut Analysis Available")
            for cut_name in cut_threshold_stats.keys():
                clean_name = cut_name.replace("_", " ").replace("round ", "Round ").replace("cut to", "→")
                st.sidebar.write(f"• {clean_name}")
    
    # Create tabs
    tab_names = []
    if player_probabilities:
        # Get available probability types for tabs (exclude metadata fields)
        first_player = next(iter(player_probabilities.values()))
        probability_types = [key for key in first_player.keys() 
                           if key not in ["current_points", "tiebreakers", "tiebreaker_order"]
                           and isinstance(first_player[key], dict) and "probability" in first_player[key]]
        
        # Build tab names
        tab_names = ["Player Probabilities"]
        
        # Add current results tab if CSV data is available
        if not csv_results_df.empty:
            tab_names.append("Current Results")
        
        # Add cut threshold tab if we have cut data
        if cut_threshold_stats:
            tab_names.append("Cut Probabilities")
        
        tabs = st.tabs(tab_names)
        
        current_tab_index = 0
        
        # Tab 1: Player Overview Table
        with tabs[current_tab_index]:
            st.subheader("Player Probability Overview")
            
            # Get tiebreaker info and initialize session state
            tiebreaker_order = first_player.get("tiebreaker_order", [])
            
            # Initialize session state for tiebreaker count if not exists
            if 'tiebreaker_count' not in st.session_state:
                st.session_state.tiebreaker_count = min(1, len(tiebreaker_order)) if tiebreaker_order else 0
            
            df = create_player_dataframe(player_probabilities, st.session_state.tiebreaker_count)
            
            # Create column configuration for display
            column_config = {
                "Player": st.column_config.TextColumn("Player", width="medium")
            }
            
            # Configure Current Points column if it exists
            if "Current Points" in df.columns:
                column_config["Current Points"] = st.column_config.NumberColumn(
                    "Current Points",
                    format="%d",
                    min_value=0,
                    width="small"
                )
            
            # Configure tiebreaker columns (look for columns that might be tiebreakers)
            tiebreaker_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ["firsts", "top4s", "seconds", "thirds", "fourths", "fifths", "sixths", "sevenths", "eighths"])]
            for col in tiebreaker_columns:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    format="%d",
                    min_value=0,
                    width="small"
                )
            
            # Configure all probability columns as percentages
            for col in df.columns:
                if col not in ["Player", "Current Points"] and col not in tiebreaker_columns:
                    column_config[col] = st.column_config.NumberColumn(
                        col,
                        format="%.1f%%",
                        min_value=0,
                        max_value=100
                    )
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
            
            # Add tiebreaker display control under the table
            if tiebreaker_order:
                new_tiebreaker_count = st.slider(
                    "Number of Tiebreakers to Display",
                    min_value=0,
                    max_value=len(tiebreaker_order),
                    value=st.session_state.tiebreaker_count,
                    help="Adjust this slider to change the number of tiebreaker columns displayed in the table above.",
                    key="tiebreaker_slider"
                )
                
                # Update session state if slider value changed
                if new_tiebreaker_count != st.session_state.tiebreaker_count:
                    st.session_state.tiebreaker_count = new_tiebreaker_count
                    st.rerun()
        
        current_tab_index += 1
        
        # Current Results Tab (if CSV data available)
        if not csv_results_df.empty:
            with tabs[current_tab_index]:
                st.subheader("Current Tournament Results")
                st.markdown("Detailed round-by-round results with current standings.")
                
                # Round-by-Round Details (no sub-tabs needed)
                st.subheader("Round-by-Round Details")
                
                # Create detailed round history table - one row per player
                round_details = []
                
                # First, determine how many rounds we have
                max_rounds = 0
                for idx, player_row in csv_results_df.iterrows():
                    round_history = player_row["Round History"]
                    if round_history:
                        max_rounds = max(max_rounds, max([r["Round"] for r in round_history]))
                
                for idx, player_row in csv_results_df.iterrows():
                    player_name = player_row["Player"]
                    round_history = player_row["Round History"]
                    
                    # Get tiebreaker data for this player
                    player_tiebreakers = {}
                    if player_name in player_probabilities and "tiebreakers" in player_probabilities[player_name]:
                        player_tiebreakers = player_probabilities[player_name]["tiebreakers"]
                    
                    # Create base row with player info
                    detail_row = {
                        "Player": player_name,
                        "Total Points": player_row["Current Points"],
                        "Avg Placement": player_row["Average Placement"],
                        "Completed Rounds": player_row["Completed Rounds"],
                        "Status": "Eliminated" if player_row["Is Eliminated"] else "Active"
                    }
                    
                    # Add current tiebreaker values
                    for tiebreaker_name, tiebreaker_value in player_tiebreakers.items():
                        detail_row[f"{tiebreaker_name.replace('_', ' ').title()}"] = tiebreaker_value
                    
                    # Create a lookup for round data
                    round_lookup = {}
                    for round_entry in round_history:
                        round_num = round_entry["Round"]
                        round_lookup[round_num] = round_entry
                    
                    # Add columns for each round
                    for round_num in range(1, max_rounds + 1):
                        if round_num in round_lookup:
                            round_entry = round_lookup[round_num]
                            lobby = round_entry["Lobby"]
                            placement = round_entry["Placement"]
                            points = round_entry["Points"]
                            status = round_entry["Status"]
                            
                            # Format the display value
                            if status == "No-Show":
                                display_value = "No-Show"
                            elif status == "In Progress":
                                display_value = f"{lobby} (In Progress)"
                            elif placement is not None and points is not None:
                                display_value = f"{lobby}-{placement} ({points}pts)"
                            else:
                                display_value = f"{lobby}-?"
                            
                            detail_row[f"R{round_num} Lobby"] = lobby
                            # Convert placement to string to avoid mixed types
                            if placement == "No-Show":
                                detail_row[f"R{round_num} Place"] = "NS"
                            elif placement is not None:
                                detail_row[f"R{round_num} Place"] = str(placement)
                            else:
                                detail_row[f"R{round_num} Place"] = ""
                            detail_row[f"R{round_num} Points"] = points if points is not None else 0
                            detail_row[f"R{round_num} Result"] = display_value
                        else:
                            # Player didn't participate in this round
                            detail_row[f"R{round_num} Lobby"] = ""
                            detail_row[f"R{round_num} Place"] = ""
                            detail_row[f"R{round_num} Points"] = 0
                            detail_row[f"R{round_num} Result"] = ""
                    
                    round_details.append(detail_row)
                
                # Convert to DataFrame
                round_details_df = pd.DataFrame(round_details)
                
                if not round_details_df.empty:
                    # Sort by total points (descending), then by average placement (ascending)
                    round_details_df = round_details_df.sort_values(
                        ["Total Points", "Avg Placement"], 
                        ascending=[False, True]
                    )
                    
                    # Create column configuration for round details
                    round_details_config = {
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "Total Points": st.column_config.NumberColumn("Total Pts", format="%d", width="small"),
                        "Avg Placement": st.column_config.NumberColumn("Avg Place", format="%.2f", width="small"),
                        "Completed Rounds": st.column_config.NumberColumn("Rounds", format="%d", width="small"),
                        "Status": st.column_config.TextColumn("Status", width="small")
                    }
                    
                    # Configure tiebreaker columns
                    tiebreaker_columns = [col for col in round_details_df.columns if any(keyword in col.lower() for keyword in ["firsts", "top4s", "seconds", "thirds", "fourths", "fifths", "sixths", "sevenths", "eighths"]) and not col.startswith("R")]
                    for col in tiebreaker_columns:
                        round_details_config[col] = st.column_config.NumberColumn(
                            col,
                            format="%d",
                            min_value=0,
                            width="small"
                        )
                    
                    # Configure round columns
                    for round_num in range(1, max_rounds + 1):
                        round_details_config[f"R{round_num} Lobby"] = st.column_config.TextColumn(
                            f"R{round_num} Lobby", 
                            width="small"
                        )
                        # Use TextColumn for placement to handle mixed types (numbers and "NS")
                        round_details_config[f"R{round_num} Place"] = st.column_config.TextColumn(
                            f"R{round_num} Place", 
                            width="small"
                        )
                        round_details_config[f"R{round_num} Points"] = st.column_config.NumberColumn(
                            f"R{round_num} Pts", 
                            format="%d",
                            width="small"
                        )
                        round_details_config[f"R{round_num} Result"] = st.column_config.TextColumn(
                            f"R{round_num} Result", 
                            width="medium"
                        )
                    
                    # Allow user to choose which columns to display
                    st.subheader("📋 Display Options")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        show_individual_columns = st.checkbox(
                            "Show Individual Round Columns", 
                            value=False,
                            help="Show separate columns for lobby, placement, and points for each round"
                        )
                    
                    with col2:
                        show_tiebreakers = st.checkbox(
                            "Show Tiebreakers", 
                            value=True,
                            help="Show tiebreaker columns (firsts, top4s, etc.)"
                        )
                    
                    # Build display columns based on user selection
                    display_columns = ["Player", "Total Points", "Avg Placement", "Completed Rounds", "Status"]
                    
                    # Add tiebreakers if requested
                    if show_tiebreakers:
                        display_columns.extend(tiebreaker_columns)
                    
                    # Add round columns
                    for round_num in range(1, max_rounds + 1):
                        if show_individual_columns:
                            display_columns.extend([
                                f"R{round_num} Lobby",
                                f"R{round_num} Place", 
                                f"R{round_num} Points"
                            ])
                        else:
                            display_columns.append(f"R{round_num} Result")
                    
                    # Filter to only show columns that exist
                    display_columns = [col for col in display_columns if col in round_details_df.columns]
                    
                    # Display the round details table
                    st.dataframe(
                        round_details_df[display_columns],
                        use_container_width=True,
                        hide_index=True,
                        column_config=round_details_config
                    )
            
            current_tab_index += 1
        
        # Cut Threshold Analysis Tab
        if cut_threshold_stats:
            with tabs[current_tab_index]:  # Use current_tab_index instead of hardcoded -1
                st.subheader("Cut Probability Analysis")
                st.markdown("Analysis of point thresholds needed to survive cuts across all simulations.")
                
                # Add explanation about cut types
                st.info("""
                **Understanding Cut Thresholds:**
                
                • **Half-Point Cut (e.g., 12.5 points):** A "clean cut" where all players above the threshold advance and all below are eliminated. No tiebreakers needed.
                
                • **Whole-Point Cut (e.g., 12 points):** A "tiebreaker cut" where multiple players have exactly the threshold score. Tiebreakers (placement history) determine who advances.
                """)
                
                for cut_name, stats in cut_threshold_stats.items():
                    if stats["count"] == 0:
                        continue
                    
                    # Clean up cut name for display
                    clean_name = cut_name.replace("_", " ").replace("round ", "Round ").replace("cut to", "→")
                    
                    st.markdown(f"### {clean_name}")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Mean Threshold", f"{stats['mean']:.1f}")
                    with col2:
                        st.metric("Most Common", f"{stats['most_common']['threshold']:.1f}")
                    with col3:
                        st.metric("Range", f"{stats['min']:.1f} - {stats['max']:.1f}")
                    with col4:
                        most_common_pct = stats['most_common']['probability'] * 100
                        st.metric("Most Common %", f"{most_common_pct:.1f}%")
                    
                    # Cut type analysis using the new data structure
                    if "cut_types" in stats:
                        cut_types = stats["cut_types"]
                        clean_pct = cut_types["clean_cuts"]["percentage"]
                        tiebreaker_pct = cut_types["tiebreaker_cuts"]["percentage"]
                        
                        st.subheader("💡 Cut Type Analysis")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"🎯 **Clean cuts:** {clean_pct:.1f}% of simulations ({cut_types['clean_cuts']['count']} times)")
                        with col2:
                            st.warning(f"⚔️ **Tiebreaker cuts:** {tiebreaker_pct:.1f}% of simulations ({cut_types['tiebreaker_cuts']['count']} times)")
                    
                    # Distribution analysis
                    distribution = stats["distribution"]
                    threshold_values = list(distribution.keys())
                    probabilities = [distribution[thresh] * 100 for thresh in threshold_values]
                    
                    # Sort by threshold value for display
                    sorted_data = sorted(zip(threshold_values, probabilities), key=lambda x: float(x[0]))
                    sorted_thresholds, sorted_probs = zip(*sorted_data)
                    
                    # Create DataFrame for chart
                    chart_df = pd.DataFrame({
                        "Threshold": sorted_thresholds,
                        "Probability": sorted_probs
                    })
                    
                    st.subheader("Threshold Distribution")
                    st.bar_chart(chart_df.set_index("Threshold"))
                    
                    # Detailed table
                    st.subheader("Detailed Breakdown")
                    display_df = chart_df.copy()
                    display_df["Type"] = display_df["Threshold"].apply(
                        lambda x: "Clean Cut" if float(x) % 1 == 0.5 else "Tiebreakers"
                    )
                    display_df["Count"] = display_df.index.map(
                        lambda i: int(chart_df.iloc[i]["Probability"] * stats["count"] / 100)
                    )
                    
                    # Create column configuration for cut threshold table
                    cut_column_config = {
                        "Threshold": st.column_config.NumberColumn(
                            "Threshold",
                            format="%.1f",
                            min_value=0
                        ),
                        "Probability": st.column_config.NumberColumn(
                            "Probability",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100
                        ),
                        "Type": st.column_config.TextColumn("Type", width="medium"),
                        "Count": st.column_config.NumberColumn("Count", format="%d")
                    }
                    
                    st.dataframe(
                        display_df[["Threshold", "Probability", "Type", "Count"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config=cut_column_config
                    )
                    
                    st.markdown("---")
    
    else:
        st.error("No player probability data found in the file.")
        
else:
    st.info("👆 Please ensure you have run the simulation to generate probability data.")
    st.markdown("""
    **To generate probability data:**
    1. Set `PROBABILITY_TRACKING_TEST = True` in `simulation.py`
    2. Run `python simulation.py`
    3. This will create `test_probabilities.json` with the analysis data
    """)

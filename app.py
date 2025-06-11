import streamlit as st
import pandas as pd
import json
from typing import Dict, Any

def load_probability_data(filename: str = "test_probabilities.json") -> Dict[str, Any]:
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

def create_player_dataframe(player_probabilities: Dict[str, Dict[str, Dict[str, float]]]) -> pd.DataFrame:
    """Convert player probabilities to a pandas DataFrame for display."""
    table_data = []
    
    for player_name, probabilities in player_probabilities.items():
        row = {"Player": player_name}
        
        # Extract probability values (keep as numeric for sorting)
        for prob_name, prob_data in probabilities.items():
            percentage = prob_data.get("probability", 0) * 100
            clean_name = prob_name.replace("_", " ").title()
            row[clean_name] = percentage  # Store as numeric for proper sorting
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    
    # Sort by the first probability column (usually most important)
    if len(df.columns) > 1:
        first_prob_col = df.columns[1]  # Skip "Player" column
        df = df.sort_values(by=first_prob_col, ascending=False).reset_index(drop=True)
    
    # Don't format here - keep numeric for interactive sorting
    return df

def get_probability_charts_data(player_probabilities: Dict[str, Dict[str, Dict[str, float]]], prob_type: str) -> pd.DataFrame:
    """Extract data for a specific probability type for charting."""
    chart_data = []
    
    for player_name, probabilities in player_probabilities.items():
        if prob_type in probabilities:
            prob_data = probabilities[prob_type]
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

st.title("🎯 TFT Tournament Probability Analysis")
st.markdown("---")

# Load data
data = load_probability_data()

if data is not None:
    player_probabilities = data.get("player_probabilities", {})
    cut_threshold_stats = data.get("cut_threshold_statistics", {})
    metadata = data.get("simulation_metadata", {})
    
    # Sidebar with simulation info
    st.sidebar.header("📊 Simulation Info")
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
        # Get available probability types for tabs
        first_player = next(iter(player_probabilities.values()))
        probability_types = list(first_player.keys())
        
        # Main tabs
        tab_names = ["📋 Player Overview"] + [f"📈 {prob_type.replace('_', ' ').title()}" for prob_type in probability_types]
        
        # Add cut threshold tab if we have cut data
        if cut_threshold_stats:
            tab_names.append("🔪 Cut Thresholds")
        
        tabs = st.tabs(tab_names)
        
        # Tab 1: Player Overview Table
        with tabs[0]:
            st.subheader("Player Probability Overview")
            df = create_player_dataframe(player_probabilities)
            
            # Create column configuration for percentage display
            column_config = {
                "Player": st.column_config.TextColumn("Player", width="medium")
            }
            
            # Configure all probability columns as percentages
            for col in df.columns:
                if col != "Player":
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
            
            # Summary statistics
            st.subheader("📊 Summary Statistics")
            cols = st.columns(len(probability_types))
            
            for i, prob_type in enumerate(probability_types):
                with cols[i]:
                    chart_data = get_probability_charts_data(player_probabilities, prob_type)
                    if not chart_data.empty:
                        avg_prob = chart_data["Probability"].mean()
                        max_prob = chart_data["Probability"].max()
                        min_prob = chart_data["Probability"].min()
                        
                        st.metric(
                            label=prob_type.replace("_", " ").title(),
                            value=f"{avg_prob:.1f}%",
                            help=f"Range: {min_prob:.1f}% - {max_prob:.1f}%"
                        )
        
        # Individual probability type tabs
        for i, prob_type in enumerate(probability_types):
            with tabs[i + 1]:
                st.subheader(f"{prob_type.replace('_', ' ').title()} Analysis")
                
                chart_data = get_probability_charts_data(player_probabilities, prob_type)
                
                if not chart_data.empty:
                    # Display chart
                    st.bar_chart(chart_data.set_index("Player")["Probability"])
                    
                    # Display detailed table
                    st.subheader("Detailed Breakdown")
                    display_data = chart_data.copy()
                    display_data["Probability"] = display_data["Probability"].apply(lambda x: f"{x:.1f}%")
                    display_data["Success Rate"] = display_data.apply(
                        lambda row: f"{row['Count']}/{row['Total']}", axis=1
                    )
                    
                    st.dataframe(
                        display_data[["Player", "Probability", "Success Rate"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Insights
                    st.subheader("💡 Key Insights")
                    best_player = chart_data.iloc[0]
                    worst_player = chart_data.iloc[-1]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.success(f"🏆 **Best odds:** {best_player['Player']} ({best_player['Probability']:.1f}%)")
                    with col2:
                        st.info(f"📉 **Lowest odds:** {worst_player['Player']} ({worst_player['Probability']:.1f}%)")
                else:
                    st.warning("No data available for this probability type.")
        
        # Cut Threshold Analysis Tab
        if cut_threshold_stats:
            with tabs[-1]:  # Last tab
                st.subheader("🔪 Cut Threshold Analysis")
                st.markdown("Analysis of point thresholds needed to survive cuts across all simulations.")
                
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
                    display_df["Probability"] = display_df["Probability"].apply(lambda x: f"{x:.1f}%")
                    display_df["Type"] = display_df["Threshold"].apply(
                        lambda x: "Clean Cut" if "." in str(x) and float(x) % 1 == 0.5 else "Tiebreakers"
                    )
                    display_df["Count"] = display_df.index.map(
                        lambda i: int(chart_df.iloc[i]["Probability"] * stats["count"] / 100)
                    )
                    
                    st.dataframe(
                        display_df[["Threshold", "Probability", "Type", "Count"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Analysis insights
                    clean_cuts = sum(1 for thresh in threshold_values if "." in str(thresh) and float(thresh) % 1 == 0.5)
                    tiebreaker_cuts = len(threshold_values) - clean_cuts
                    clean_cut_pct = (clean_cuts / len(threshold_values)) * 100 if threshold_values else 0
                    
                    st.subheader("💡 Cut Analysis")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"🎯 **Clean cuts:** {clean_cut_pct:.1f}% of scenarios")
                    with col2:
                        st.warning(f"⚔️ **Tiebreaker cuts:** {100-clean_cut_pct:.1f}% of scenarios")
                    
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

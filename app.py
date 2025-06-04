import streamlit as st
import pandas as pd
import json
from typing import List, Dict
from pydantic import BaseModel

# Define Pydantic schema
class CutDistributionEntry(BaseModel):
    points: float
    probability: float

class PlayerProbabilities(BaseModel):
    name: str
    current_points: float
    average_placement: float
    prob_to_win: float
    cut_probabilities: Dict[str, float]

class Probabilities(BaseModel):
    players: List[PlayerProbabilities]
    cut_distributions: Dict[str, List[CutDistributionEntry]]

# Page config
st.set_page_config(
    page_title="TFT Tournament Odds",
    page_icon="🎲",
    layout="wide"
)

# Load JSON data
try:
    with open("probabilities.json") as f:
        data = Probabilities.model_validate_json(f.read())
except FileNotFoundError:
    st.error("Could not find probabilities.json file.")
    st.stop()
except json.JSONDecodeError:
    st.error("Invalid JSON format in probabilities.json file.")
    st.stop()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Player Info", "🎯 Cut Info", "🧪 TBD"])

# Tab 1: Player Table
with tab1:
    st.subheader("Player Probabilities Table")
    
    # Create filter columns
    col1, _ = st.columns([1, 2])
    
    with col1:
        # Search by player name
        search_term = st.text_input("Search by player name", "")
    
    # Prepare table data
    table_data = []
    for p in data.players:
        table_data.append({
            "Name": p.name,
            "Points": p.current_points,
            "Avg Placement": round(p.average_placement, 2),
            "Top 16 %": round(p.cut_probabilities.get("top16", 0) * 100, 2),
            "Top 8 %": round(p.cut_probabilities.get("top8", 0) * 100, 2),
            "Win %": round(p.prob_to_win * 100, 2),
        })
    
    df = pd.DataFrame(table_data)
    
    # Apply filters
    if search_term:
        df = df[df["Name"].str.contains(search_term, case=False)]
    
    # Sort by points by default
    df = df.sort_values("Points", ascending=False)
    
    # Display metrics
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    with metrics_col1:
        st.metric("Total Players", len(df))
    with metrics_col2:
        st.metric("Avg Points", f"{df['Points'].mean():.1f}")
    with metrics_col3:
        st.metric("Max Points", f"{df['Points'].max():.1f}")
    with metrics_col4:
        st.metric("Min Points", f"{df['Points'].min():.1f}")
    
    # Display table with highlights
    st.dataframe(
        df.style
        .background_gradient(subset=["Top 16 %", "Top 8 %", "Win %"], cmap="RdYlGn")
        .format({
            "Points": "{:.0f}",
            "Avg Placement": "{:.2f}",
            "Top 16 %": "{:.1f}%",
            "Top 8 %": "{:.1f}%",
            "Win %": "{:.1f}%"
        }),
        use_container_width=True
    )

# Tab 2: Cut Info Charts
with tab2:
    st.subheader("Cut Point Distributions")
    
    # Add explanation at the top
    st.markdown("""
    **Understanding the Distribution:**
    - Whole numbers (e.g., 32) indicate split cuts: some players at this point total make the cut, others don't
    - Half numbers (e.g., 32.5) indicate clean cuts: all players above this point total make the cut, all below don't
    - Bar height shows the probability of each cut point
    """)
    
    st.markdown("---")  # Add separator

    for i, (stage, dist) in enumerate(data.cut_distributions.items()):
        if i > 0:
            st.markdown("---")  # Add separator between cuts
            
        st.markdown(f"### {stage.upper()} Cut")
        df_cut = pd.DataFrame([d.model_dump() for d in dist])
        
        # Calculate statistics
        most_likely = df_cut.loc[df_cut["probability"].idxmax()]
        mean_cut = (df_cut["points"] * df_cut["probability"]).sum()
        weighted_std = ((df_cut["points"] - mean_cut) ** 2 * df_cut["probability"]).sum() ** 0.5
        
        # Create columns for metrics and chart
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Display key statistics
            st.metric("Most Likely Cut", f"{most_likely['points']:.1f} pts")
            st.metric("Probability", f"{most_likely['probability'] * 100:.1f}%")
            st.metric("Mean Cut", f"{mean_cut:.1f} pts")
            st.metric("Standard Deviation", f"±{weighted_std:.1f} pts")
        
        with col2:
            # Enhance the bar chart
            chart_data = df_cut.copy()
            chart_data["probability"] = chart_data["probability"] * 100  # Convert to percentage
            
            # Create a more detailed chart using st.plotly_chart
            import plotly.graph_objects as go
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=chart_data["points"],
                y=chart_data["probability"],
                text=chart_data["probability"].apply(lambda x: f"{x:.1f}%"),
                textposition="outside",
                name="Probability"
            ))
            
            fig.update_layout(
                title=f"{stage.upper()} Cut Distribution",
                xaxis_title="Points",
                yaxis_title="Probability (%)",
                showlegend=False,
                hovermode="x",
                height=400,
                margin=dict(t=30, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add horizontal line for mean
            st.markdown(f"The mean cut point is shown above at **{mean_cut:.1f}** points. "
                       f"There is a **{weighted_std:.1f}** point standard deviation, meaning most cuts "
                       f"will fall between **{mean_cut - weighted_std:.1f}** and **{mean_cut + weighted_std:.1f}** points.")

# Tab 3: Placeholder
with tab3:
    st.subheader("Coming soon...")
    st.write("This tab will include future simulation settings or comparison tools.")

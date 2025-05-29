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

# Load JSON data
with open("probabilities.json") as f:
    data = Probabilities.model_validate_json(f.read())

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Player Info", "🎯 Cut Info", "🧪 TBD"])

# Tab 1: Player Table
with tab1:
    st.subheader("Player Probabilities Table")
    table_data = []
    for p in data.players:
        table_data.append({
            "Name": p.name,
            "Points": p.current_points,
            "Avg Placement": p.average_placement,
            "Top 16 %": round(p.cut_probabilities.get("top16", 0) * 100, 2),
            "Top 8 %": round(p.cut_probabilities.get("top8", 0) * 100, 2),
            "Win %": round(p.prob_to_win * 100, 2),
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

# Tab 2: Cut Info Charts
with tab2:
    st.subheader("Cut Point Distributions")

    for stage, dist in data.cut_distributions.items():
        st.markdown(f"### {stage.upper()} Cut")
        df_cut = pd.DataFrame([d.model_dump() for d in dist])
        most_likely = df_cut.loc[df_cut["probability"].idxmax()]
        st.write(f"Most likely cut: **{most_likely['points']} pts** "
                 f"({most_likely['probability'] * 100:.1f}%)")
        st.bar_chart(df_cut.set_index("points"))

# Tab 3: Placeholder
with tab3:
    st.subheader("Coming soon...")
    st.write("This tab will include future simulation settings or comparison tools.")

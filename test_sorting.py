import json
import pandas as pd

def test_dataframe_sorting():
    """Test if the DataFrame sorting is working correctly."""
    
    # Load test data
    with open('test_probabilities.json') as f:
        data = json.load(f)
    
    player_probabilities = data.get("player_probabilities", {})
    
    # Create test data similar to our app
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
    print("Original DataFrame:")
    print(df[["Player", "Made Top 8 Cut"]].head(10))
    
    # Sort by the first probability column
    if len(df.columns) > 1:
        first_prob_col = df.columns[1]  # Skip "Player" column
        df_sorted = df.sort_values(by=first_prob_col, ascending=False).reset_index(drop=True)
    
    print(f"\nSorted by {first_prob_col} (descending):")
    print(df_sorted[["Player", "Made Top 8 Cut"]].head(10))
    
    # Now format for display
    df_formatted = df_sorted.copy()
    for col in df_formatted.columns:
        if col != "Player":
            df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.1f}%")
    
    print(f"\nFormatted with percentages:")
    print(df_formatted[["Player", "Made Top 8 Cut"]].head(10))

if __name__ == "__main__":
    test_dataframe_sorting() 
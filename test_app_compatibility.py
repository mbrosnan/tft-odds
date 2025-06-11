#!/usr/bin/env python3
"""
Test script to verify app.py compatibility with new JSON format
"""

import json
import pandas as pd

def test_json_loading():
    """Test if the new JSON format can be loaded and processed."""
    print("🧪 Testing JSON compatibility...")
    
    try:
        # Load the new JSON format
        with open('test_probabilities.json') as f:
            data = json.load(f)
        
        player_probabilities = data.get('player_probabilities', {})
        metadata = data.get('simulation_metadata', {})
        
        print("✅ JSON loaded successfully!")
        print(f"📊 Players found: {len(player_probabilities)}")
        print(f"🔄 Simulations run: {metadata.get('total_simulations', 'N/A')}")
        print(f"⏱️  Simulation time: {metadata.get('simulation_time_seconds', 0):.1f}s")
        
        return True, data
        
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False, None

def test_dataframe_creation(data):
    """Test creating DataFrame from the new format."""
    print("\n🧪 Testing DataFrame creation...")
    
    try:
        player_probabilities = data.get('player_probabilities', {})
        
        # Test the same logic as in app.py
        table_data = []
        for player_name, probabilities in player_probabilities.items():
            row = {"Player": player_name}
            
            # Extract probability percentages from each target
            for prob_name, prob_data in probabilities.items():
                percentage = prob_data.get("probability", 0) * 100
                row[prob_name.replace("_", " ").title()] = f"{percentage:.1f}%"
            
            table_data.append(row)
        
        df = pd.DataFrame(table_data)
        print("✅ DataFrame created successfully!")
        print(f"📋 Columns: {list(df.columns)}")
        print(f"📏 Rows: {len(df)}")
        
        # Show sample data
        print("\n📄 Sample data (first 3 players):")
        print(df.head(3).to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating DataFrame: {e}")
        return False

def test_chart_data_extraction(data):
    """Test extracting data for charts."""
    print("\n🧪 Testing chart data extraction...")
    
    try:
        player_probabilities = data.get('player_probabilities', {})
        
        # Test extracting data for the first probability type
        first_player = next(iter(player_probabilities.values()))
        first_prob_type = next(iter(first_player.keys()))
        
        chart_data = []
        for player_name, probabilities in player_probabilities.items():
            if first_prob_type in probabilities:
                prob_data = probabilities[first_prob_type]
                chart_data.append({
                    "Player": player_name,
                    "Probability": prob_data.get("probability", 0) * 100,
                    "Count": prob_data.get("count", 0),
                    "Total": prob_data.get("total", 0)
                })
        
        # Sort by probability descending
        chart_data.sort(key=lambda x: x["Probability"], reverse=True)
        chart_df = pd.DataFrame(chart_data)
        
        print(f"✅ Chart data extracted for '{first_prob_type}'!")
        print(f"📊 Top 3 players:")
        print(chart_df.head(3)[["Player", "Probability"]].to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"❌ Error extracting chart data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing app.py compatibility with new JSON format")
    print("=" * 50)
    
    # Test 1: JSON Loading
    success, data = test_json_loading()
    if not success:
        print("❌ Cannot proceed - JSON loading failed")
        exit(1)
    
    # Test 2: DataFrame Creation
    success = test_dataframe_creation(data)
    if not success:
        print("❌ Cannot proceed - DataFrame creation failed")
        exit(1)
    
    # Test 3: Chart Data Extraction
    success = test_chart_data_extraction(data)
    if not success:
        print("❌ Cannot proceed - Chart data extraction failed")
        exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! app.py should work with the new JSON format!")
    print("🚀 You can now run: streamlit run app.py") 
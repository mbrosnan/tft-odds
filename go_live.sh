#!/bin/bash

echo "Copying files from staging to live..."

# Create live directory if it doesn't exist
mkdir -p live

# Copy tour_state.csv if it exists
if [ -f "staging/tour_state.csv" ]; then
    cp "staging/tour_state.csv" "live/tour_state.csv"
    echo "Copied tour_state.csv"
else
    echo "Warning: staging/tour_state.csv not found"
fi

# Copy probabilities.json if it exists
if [ -f "staging/probabilities.json" ]; then
    cp "staging/probabilities.json" "live/probabilities.json"
    echo "Copied probabilities.json"
else
    echo "Warning: staging/probabilities.json not found"
fi

# Copy tournament_notes.md if it exists
if [ -f "staging/tournament_notes.md" ]; then
    cp "staging/tournament_notes.md" "live/tournament_notes.md"
    echo "Copied tournament_notes.md"
else
    echo "Warning: staging/tournament_notes.md not found"
fi

echo ""
echo "Files are now live!"
echo "You can run: streamlit run app.py" 
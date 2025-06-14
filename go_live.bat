@echo off
echo Copying files from staging to live...

REM Create live directory if it doesn't exist
if not exist "live" mkdir live

REM Copy tour_state.csv if it exists
if exist "staging\tour_state.csv" (
    copy "staging\tour_state.csv" "live\tour_state.csv"
    echo Copied tour_state.csv
) else (
    echo Warning: staging\tour_state.csv not found
)

REM Copy probabilities.json if it exists
if exist "staging\probabilities.json" (
    copy "staging\probabilities.json" "live\probabilities.json"
    echo Copied probabilities.json
) else (
    echo Warning: staging\probabilities.json not found
)

REM Copy tournament_notes.md if it exists
if exist "staging\tournament_notes.md" (
    copy "staging\tournament_notes.md" "live\tournament_notes.md"
    echo Copied tournament_notes.md
) else (
    echo Warning: staging\tournament_notes.md not found
)

echo.
echo Files are now live!
echo You can run: streamlit run app.py
pause 
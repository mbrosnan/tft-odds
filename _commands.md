going into venv:
.\.venv\Scripts\activate

running the simulation: 
python simulation.py --csv "s14tt3/before_r02/TT3_Live_beforer2.csv" --tour-format "s14tt3/tour_format_Set14_NA_TacTrials3.json" --sim-settings "s14tt3/sim_settings_Set14_NA_TacTrials3.json" --output "staging/probabilities.json"

copy from staging to live:
./go_live.sh #not windows
.\go_live.bat #windows

run streamlit locally
streamlit run app.py


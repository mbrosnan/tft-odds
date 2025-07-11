going into venv:
.\.venv\Scripts\activate

running the simulation: 
python simulation.py --csv "s14tt3/before_r02/TT3_Live_beforer2.csv" --tour-format "s14tt3/tour_format_Set14_NA_TacTrials3.json" --sim-settings "s14tt3/sim_settings_Set14_NA_TacTrials3.json" --output "staging/probabilities.json"

copy from staging to live:
./go_live.sh #not windows
.\go_live.bat #windows

run streamlit locally
streamlit run app.py



python simulation.py --csv "tc3day3/tour_state_initial.csv" --tour-format "tc3day3/tour_format_Set14_NA_TacCup3Day3.json" --sim-settings "tc3day3/sim_settings_Set14_NA_TacCup3Day3.json" --output "staging/probabilities.json"


SSH: ssh -i "C:\Users\mitch\Desktop\tft-odds-key.pem" ubuntu@ec2-3-14-29-73.us-east-2.compute.amazonaws.com

stop streamlit in EC2: sudo systemctl stop streamlit.service

start streamlit in EC2: sudo systemctl start streamlit.service


post-round unified:  python3 process_round.py s14_na_gs/tour_state_pre_round1.csv --no-preview --auto-deploy
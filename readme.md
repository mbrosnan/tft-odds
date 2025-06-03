# General Description
tft-odds.com is a webapp that takes in information on Teamfight Tactics tournaments and calculates odds for various tournament related items.  This includes player odds, cut odds, and tournament info.

## UI

### Player Odds Tab
Player odds is primarily a table where each player has a row.  There are columns for various tournament statistics like their current points, average placement, and top few tiebreakers.  There are also columns for their odds, such as "Make 16 cut", "Make 8 cut", and "Win Tournament" (these will change depending on the tournament format).

### Cut Odds Tab
Cut odds is comprised of a section per cut (ie from 48 to 24, 24 to 16, 16 to 8).  Each section will contain information on the likeliest cut and the cut distribution.  

#### Likeliest Cut
The likeliest cut will give the mode of all calculated cuts along with the percent odds that it is the cut.  

#### Cut Distribution 
The cut distribution will be a bar graph with each possible cut along with its likelihood as a percentage.  Note that the convention used here will be that a cut of a whole number will be used if there is at least one player at that number who misses the cut and at least one player at that number who makes the cut.  A half number will be used if every player at one number misses the cut and every player at the next highest number make the cut.

### Tournament Info Tab
Tournament info is comprised of some TBD information on the tournament.  This is unlikely to change based on the probability calculations.

## Probability Calculation
The probabilities will be derived using a monte-carlo style simulation.  

### Inputs
- tour_state.json
   - This contains the tournament results so far.  This should match exactly the current "standings".  For each player, it will have:
       - Total points
       - AVP (average placement)
       - total completed rounds
       - each round which lobby they were in
       - each round what placement they got
       - all tiebreaker info (# firsts, # top 4s, # 2nds, # 3rds, etc)

// tour_state.json
{
  "players": [
    {
      "name": "Player A",
      "points": 26,
      "avg_placement": 3.7,
      "rounds": [
        {"round": 1, "lobby": "A", "placement": 2},
        ...
      ],
      "tiebreakers": {
        "firsts": 2,
        "top4s": 5,
        ...
      }
    }
  ]
}




- tour_format.json
    - This contains info about the tournament.  It will have:
        - Each round of the tournament what happens after.  Could be:
            - nothing
            - evaluate checkmate
            - end tournament
            - shuffle (snake or random)
            - cut to X players
            - note that rounds may be represented as day X, round Y, or overall_round Z (Day 2 round 2 may be overall_round 8)
        - potentially in the future, player info coming INTO the tournament such as qualifier points or similar


{
  "tournament_name": "Mid-Set Finale NA",
  "round_structure": [
    {
      "overall_round": 1,
      "day": 1,
      "round_in_day": 1,
      "after_round": "shuffle",
      "shuffle_type": "snake"
    },
    {
      "overall_round": 2,
      "day": 1,
      "round_in_day": 2,
      "after_round": "nothing"
    },
    {
      "overall_round": 3,
      "day": 1,
      "round_in_day": 3,
      "after_round": "cut",
      "cut_to": 32
    },
    {
      "overall_round": 4,
      "day": 2,
      "round_in_day": 1,
      "after_round": "shuffle",
      "shuffle_type": "random"
    },
    {
      "overall_round": 5,
      "day": 2,
      "round_in_day": 2,
      "after_round": "end"
    }
  ],
  "tiebreaker_order": [
    "points",
    "firsts",
    "top4s",
    "avg_placement"
  ],
  "cut_stages": [32, 16, 8]

- sim_settings.json
    - this shorter JSON will contain the parameters for the individual sim.  It will have:
        - number_of_sims: how many loops of the monte carlo simulation to run through
        - duration_of_sim: how long to loop through the monte carlo simulation before stopping
        - first_or_last: whether to stop when the first criteria (number or duration) is completed, or the last is completed

{
  "number_of_sims": 10000,
  "duration_of_sim": 60,
  "stop_condition": "first", 
  "random_seed": 42,
  "log_every_n_sims": 1000,
  "output_file": "probabilities.json"
}

### Outputs
- probabilities.json
    - this file will contain all simulation outputs.  See UI sections Player Odds Tab and Cut Odds Tab for what info this will have to have


   
### Simulation
With the above inputs, it will randomly assign results of any remaining unfinished games, performing cuts as the tournament would according to the format, and shuffling lobbies as appropriate.  Throughout this and at the end, it will save results such as whether each player made a given cut, whether a player won the tournament, etc.  These will get saved, then the simulation will reset to the current game state and repeat this until either the number of simulations is reached or the time limit from the sim_settings file is reached.  Number of occurrences of a given event will be divided by the number of total simulation loops to achieve probabilities of each event happening.  These will be stored in probabilities.json, which is an input to the UI.  The simulation will be broken into the following modules:

- determine_current_round: look at tour_state and decide where the simulation should start (do we need to complete a round, perform a cut/shuffle, or just start the next round sim)
- simulate_round_results: simulate a round and perform any needed actions
- apply_cut
- shuffle_lobbies
- aggregate_statistics: this will count up all relevant statistics
- simulate_tournament: this will exercise a full tournament sim.  This will be done over and over to get our probabilities
- obtain_probabilities: this will run simulate tournament until the stop condition is satisfied




## Data Import
Data will be imported into the tour_state.json blob, which will be used by the simulation module.  Initially, this blob will be generated or edited semi-manually.  Eventually, there will be code to periodically pull data from a public google sheet that contains the tournament results data.  Note that the automated import is a FUTURE item.


# Tech Stack

UI: Streamlit
Hosting: AWS EC2 ubuntu instance.  Nginx running
Domain: Cloudflare
Simulation: Python
Data Import from Google Sheet: Python

# Implementation order notes

Currently, the UI, hosting, and domain side is concept proved in a running site at tft-odds.com.  It doesn't have real data, simulation, or data import, but currently runs.

The simulation is proved out in a python file that could use significant restructuring and addition/modification.

The data import is not proved out in any way.

Order is planned to be as follows:
1. Get the target, semi-final streamlit UI pulling from a representative probabilities.json, running locally (not on AWS)
2. Refactor/rewrite the simulation piece, pulling from representative sim_settings.json and tour_state.json, outputting to probabilities.json.
3. Move the working UI and simulation piece to AWS/the live site.
4. Implement the import function.

# Future Updates

- Color coding for player likelihoods


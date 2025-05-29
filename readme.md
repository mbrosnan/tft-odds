# General Description
tft-odds.com is a webapp that takes in information on Teamfight Tactics tournaments and calculates odds for various tournament related items.  This includes player odds, cut odds, and tournament info.

## UI

Player odds is primarily a table where each player has a row.  There are columns for various tournament statistics like their current points, average placement, and top few tiebreakers.  There are also columns for their odds, such as "Make 16 cut", "Make 8 cut", and "Win Tournament" (these will change depending on the tournament format).

Cut odds is comprised of a section per cut (ie from 48 to 24, 24 to 16, 16 to 8).  Each section will contain information on the likeliest cut and the cut distribution.  The likeliest cut will give the mode of all calculated cuts along with the percent odds that it is the cut.  The cut distribution will be a bar graph with each possible cut along with its likelihood as a percentage.  Note that the convention used here will be that a cut of a whole number will be used if there is at least one player at that number who misses the cut and at least one player at that number who makes the cut.  A half number will be used if every player at one number misses the cut and every player at the next highest number make the cut.

Tournament info is comprised of some TBD information on the tournament.  This is unlikely to change based on the probability calculations.

## Probability Calculation
The probabilities will be derived using a monte-carlo style simulation.  This simulation will take the current tournament results as an input (tour_state), along with the tournament format (tour_format) and settings for the running of the simulation (sim_settings).  With these inputs, it will randomly assign results of any remaining unfinished games, performing cuts as the tournament would according to the format, and shuffling lobbies as appropriate.  Throughout this and at the end, it will save results such as whether each player made a given cut, whether a player won the tournament, etc.  These will get saved, then the simulation will reset to the current game state and repeat this until either the number of simulations is reached or the time limit from the sim_settings file is reached.  Number of occurrences of a given event will be divided by the number of total simulation loops to achieve probabilities of each event happening.  These will be stored in probabilities.json, which is an input to the UI.

## Data Import
Data will be imported into the tour_state.json blob, which will be used by the simulation module.  Initially, this blob will be generated or edited semi-manually.  Eventually, there will be code to periodically pull data from a public google sheet that contains the tournament results data.


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


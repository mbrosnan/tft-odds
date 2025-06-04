# General Description
tft-odds.com is a webapp that takes in information on Teamfight Tactics tournaments and calculates odds for various tournament related items.  This includes player odds, cut odds, and tournament info.

In general, these tournaments will consist of a certain number of rounds, broken up over a certain number of days (for example 18 rounds over 3 days).  Players get sorted into lobbies of 8 (only having a lobby or two of 7 if people disconnect or no-show).  The player who finishes first gets 8 points, down to the player who finishes last who gets 1 point.

## UI

### UI Specifications
- Simulations run for approximately 30 seconds to generate probability data
- UI updates:
  - Initial page load uses most recent simulation data
  - A notification/button will appear when new simulation data is available
  - Users can manually trigger data refresh
- Primary design focus is for PC monitors, with mobile responsiveness as a secondary consideration
- No specific accessibility requirements in initial version

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

### Tournament Mechanics
#### Tiebreakers
Tiebreakers are handled according to the order specified in the `tour_format.json` file. If players remain tied after all specified tiebreakers are evaluated, the final tiebreaker is always random. This means in simulations, players who are tied on all tiebreaker metrics will have an equal probability of advancing.

#### Lobby Assignment
When shuffling lobbies, two methods are available:

1. **Snake Shuffle**: Players are first sorted by points (using tiebreakers for ties). Then lobbies are assigned in a snake pattern:
   - First pass (top to bottom): Player 1 → Lobby A, Player 2 → Lobby B, Player 3 → Lobby C, etc.
   - Return pass (bottom to top): If 5 lobbies, Player 6 → Lobby E, Player 7 → Lobby D, Player 8 → Lobby C, etc.
   - This continues until all players are assigned

2. **Random Shuffle**: Players are randomly assigned to lobbies

### Simulation Assumptions
- All future game placements are treated as equally random, regardless of player's historical performance
- Probabilities are displayed with single-digit percentage precision (e.g., 45.6%)
- No special handling for edge cases (disconnections, disqualifications) in the current version

### Performance Specifications
- Tournament Size:
    - Maximum supported players: 256
    - Optimized for typical tournament sizes (<256 players)
- Simulation Termination:
    - Controlled by both number of simulations and time-based criteria
    - Parameters specified in sim_settings.json
- Results Storage:
    - Simulation results stored temporarily for probability calculations
    - No long-term caching of simulation results in initial version
    - Each new probability request triggers fresh simulations

### Inputs
- tour_state.json
   - This contains the complete tournament history and current state. For each player, it will have:
       - Total points
       - AVP (average placement)
       - Total completed rounds
       - Complete round history:
           - Which lobby they were in
           - What placement they got
           - Round number when they were cut (if applicable)
       - All tiebreaker info (# firsts, # top 4s, # 2nds, # 3rds, etc)
   - All historical data must be preserved, including:
       - Past lobby assignments
       - Results from all rounds
       - Cut history
       - Tournament progression

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
    - this should throw an error if one round is incomplete but another round has results already
- simulate_round_results: simulate a round and perform any needed actions
- apply_cut
- shuffle_lobbies
- aggregate_statistics: this will count up all relevant statistics
- simulate_tournament: this will exercise a full tournament sim.  This will be done over and over to get our probabilities
- obtain_probabilities: this will run simulate tournament until the stop condition is satisfied




## Data Import
Data will be imported into the tour_state.json blob, which will be used by the simulation module.  Initially, this blob will be generated or edited semi-manually. 

Future automated import will pull from a Google Sheet containing raw tournament data that maps to tour_state.json fields. The sheet will contain:
- Raw tournament results
- Player information
- Round-by-round data
Some fields may require calculation or transformation during import.

The current implementation focuses on the standard tournament format described above. Support for alternative tournament formats may be considered in future updates.

# Tech Stack

UI: Streamlit
Hosting: AWS EC2 ubuntu instance. Nginx running
Domain: Cloudflare
Simulation: Python
Data Import from Google Sheet: Python

# Development Setup

## Environment
- Python (version requirements will be documented per feature if needed)
- Package management: pip with requirements.txt
- Virtual environment: venv
- Configuration files for both local development and production environments

## Local Development
1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\\venv\\Scripts\\activate  # Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment (local vs production settings)
4. Run local development server

## Testing
### Test Data
Sample tournament structure for development and testing:
- 32 player field
- 2 day tournament
- Day 1:
    - Cut to 24 after round 2
    - Cut to 16 after round 4
    - Cut to 8 after round 6
- Day 2:
    - Checkpoint/Checkmate format
    - Victory threshold: 20 points

### Test Suite
- Unit tests for core functionality
- Integration tests for system components
- Test data generators
- Mock tournament scenarios

## Deployment
### Local to AWS Migration
1. Local testing and validation
2. AWS environment setup
3. Deployment scripts and procedures
4. Configuration management
5. Monitoring and logging setup

# Implementation Order
1. Review and enhance existing basic UI
2. Implement simulation engine
3. AWS deployment
4. Data import automation

Each phase will include:
- Core functionality
- Tests
- Documentation
- Error handling
- Logging

# Configuration
The system supports two primary configurations:
1. Local Development:
   - Local file storage
   - Debug logging
   - Development server
   - Mock data support

2. Production (AWS):
   - AWS infrastructure
   - Production logging levels
   - Nginx server
   - Real tournament data

Configuration can be switched via environment variables or config files.

# Future Updates

- Color coding for player likelihoods
- Mobile-first UI optimization
- Accessibility improvements
- Historical data tracking and visualization
- Comprehensive input validation for all JSON files
- Detailed error reporting and recovery options
- Result caching for performance optimization
- Support for alternative tournament formats
- Enhanced logging and monitoring capabilities
- Extended test coverage
- Additional tournament formats
- Production monitoring dashboard

### Error Handling
The system will halt and display an error message in the following scenarios:
- Invalid or inconsistent tournament data (e.g., missing rounds, conflicting results)
- Data format violations
- Logical tournament progression errors

Error messages will include a specific error code for debugging purposes. Initial version will focus on detecting critical errors that would affect simulation accuracy, with more comprehensive validation planned for future updates.

### Logging
The system will support multiple logging levels:
- ERROR: Critical issues that prevent system operation
- INFO: Important system events and state changes
- DEBUG: Detailed information for troubleshooting
    - Simulation progress and intermediate results
    - Data transformation steps
    - Performance metrics
Logging level can be configured to balance between verbose debugging output and concise production logs.


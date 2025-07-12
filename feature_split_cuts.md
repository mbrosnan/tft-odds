# Split cut feature

## Description

This would allow for a cut where X players in a lobby advance to a future round (not playing rounds in between).  Another set of Y players is fully eliminated from the tournament.  X+Y will always add to 8 such that (X+Y)/8 is an integer and integer lobbies are kept.

In this example, there are 16 players going into day 2 round 6.  After round 6, the bottom 4 players are eliminated and the top 4 players are through.  8 players play in day 2 round 7.  After this round, again the top 4 players advance and the bottom 4 are cut, meaning that day 3 round 1 has 8 players.

All cuts can be changed to a version of this cut.  If a cut is now "top X advance to round n, bottom Y are eliminated", if no advancements are there, only Y can be populated.

## Parameters

In the tour_format, after each round, change from "cut_to" to:

- Top X advance
- advancements to round n
- bottom Y eliminated

## Q&A

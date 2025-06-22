#!/usr/bin/env python3
"""Debug CSV parsing."""

import csv
import tempfile

# Create a test CSV
csv_content = """Current Round,2
Round Status,in_progress

Day,,1,1
Round,,1,2
Overall Round,,1,2
PlayerID,Player Name,Lobby,Placement,,Lobby,Placement,
1,Player1,A,1,,B,,
2,Player2,A,2,,B,,
3,Player3,A,3,,B,,
4,Player4,A,4,,B,,
"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    f.write(csv_content)
    csv_file = f.name

# Read and debug
with open(csv_file, 'r', encoding='utf-8') as f:
    lines = list(csv.reader(f))

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[:10]):
    print(f"Line {i}: {line}")

print(f"\nChecking line 7 (index 6) length: {len(lines[6])}")
print(f"Line 7 contents: {lines[6]}")

print(f"\nChecking player data starting at line 8 (index 7):")
player_start = 7
for i, row in enumerate(lines[player_start:player_start+5]):
    print(f"  Row {i}: {row}")
    if len(row) > 1:
        print(f"    Row[0]: '{row[0]}', Row[1]: '{row[1]}'")
        print(f"    Row[1] empty check: {not row[1]}")
# MP Analyzer

Used to analyzer qualifiers MP results from an osu tournament.

Necessary Input Files:
- Create `disconnects.csv`, add any disconnects. If none, include header and leave blank
- Create `matches.txt`, input all matches. Can be in any format as long as it follows `.*/id`
- Create `secrets.txt`. First line is client ID, second is client secret. You will need to get this from osu api
- Create `teams.csv`. This needs at least 2 columns, 1 for the user ID and the second for the team. You may change the names of the corresponding files in main.py

Other input args:
- All at the top of main.py
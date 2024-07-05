import ossapi
import pickle
import pandas as pd
import numpy as np
from ossapi import Ossapi
from tqdm import tqdm
# ----------------------------------------------------------------------------------------------- #
# global variables you have to set
# ----------------------------------------------------------------------------------------------- #
with open('secrets.txt', 'r') as tokens_file:
    client_id = tokens_file.readline().strip()
    client_secret = tokens_file.readline().strip()
    tokens_file.close()

# team csv setup
csv_file = 'teams.csv'
csv_columns = ['User ID', 'Team']

# matches file
matches_file = 'matches.txt'
# disconnects file
dc_file = 'disconnects.csv'

# ----------------------------------------------------------------------------------------------- #
# classes
# ----------------------------------------------------------------------------------------------- #
# id -> user object
class UserCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, user_id):
        if user_id in self.cache:
            return self.cache[user_id]
        else:
            user = api.user(user_id, key=ossapi.UserLookupKey.ID).username
            self.cache[user_id] = user
            return user
    
    def save(self):
        with open('user_cache.pkl', 'wb') as f:
            pickle.dump(self.cache, f)
            f.close()

    def load(self):
        try:
            with open('user_cache.pkl', 'rb') as f:
                self.cache = pickle.load(f)
                f.close()
        except FileNotFoundError: # no cache
            pass

class Teams:
    def __init__(self):
        self.idtoteam = {}
        self.teamtoid = {}
        self.teamscores = {}

    def load_teams(self, team_csv):
        print("Getting teams...")
        data = pd.read_csv(team_csv, sep=',', header=0, keep_default_na=False)
        for i, row in data.iterrows():
            self.idtoteam[row[csv_columns[0]]] = row[csv_columns[1]]
            self.teamtoid[row[csv_columns[1]]] = row[csv_columns[0]]
            if row[csv_columns[1]] not in self.teamscores.keys():
                self.teamscores[row[csv_columns[1]]] = TeamScores(row[csv_columns[1]])

        teamlist = self.get_team_list()
        with tqdm(total=len(teamlist)) as pbar:
            for teamname in teamlist:
                self.teamscores[teamname].set_players([cache.get(user_id) for user_id in self.get_ids(teamname)])
                pbar.update(1)
        print("Teams loaded.")

    def get_team(self, user_id):
        if user_id not in self.idtoteam.keys():
            return None
        return self.idtoteam[user_id]
    
    def get_ids(self, team):
        return [user_id for user_id in self.idtoteam.keys() if self.idtoteam[user_id] == team]
    
    def get_score(self, team):
        if team not in self.teamscores.keys():
            return None
        return self.teamscores[team]
    
    def get_team_list(self):
        return list(self.teamscores.keys())
    
    def add_score(self, user_id, map_id, score):
        team = self.get_team(user_id)
        if team is None:
            return
        self.teamscores[team].add_score(user_id, map_id, score)
        
    def __str__(self):
        return 'Teams OBJ:' + str(self.idtoteam) +'\n'.join([f"{team.get_team()}: {[str(obj) for obj in team.get_scores()]}" for team in self.teamscores.values()])

class TeamScores:
    def __init__(self, team, players=None):
        self.team = team
        self.scores = []
        self.maps = []
        self.players = players if players else []
    
    def add_score(self, user_id, map_id, score):
        if map_id not in self.maps:
            self.maps.append(map_id)
            self.scores.append(MapScores(map_id))
            self.scores[-1].add_score(user_id, score)
        else:
            for map in self.scores:
                if map.get_map() == map_id:
                    map.add_score(user_id, score)
                    break
    
    def set_players(self, players):
        self.players = players

    def get_players(self):
        return self.players

    def get_scores(self):
        return self.scores
    
    def get_sum(self):
        if len(self.maps) == 0:
            return 0
        return sum([map.get_sum() for map in self.scores])
    
    def get_avg(self):
        if len(self.maps) == 0:
            return 0
        return np.mean([map.get_sum() for map in self.scores])
    
    def get_team(self):
        return self.team
    
    def __str__(self):
        return f"{self.team}: {str(self.scores)}"

class MapScores:
    def __init__(self, map_id):
        self.scores = {}
        self.map = map_id

    def add_score(self, user_id, score):
        self.scores[user_id] = score
    
    def get_scores(self):
        return self.scores
    
    def get_map(self):
        return self.map
    
    def get_sum(self):
        if len(self.scores) == 0:
            return 0
        return sum(self.scores.values())
    
    def get_avg(self):
        if len(self.scores) == 0:
            return 0
        return np.mean(list(self.scores.values()))
    
    def __str__(self):
        return f'Map {self.map}: ' + str(self.scores)
# ----------------------------------------------------------------------------------------------- #
# match stuff
# ----------------------------------------------------------------------------------------------- #
def getmatches(input) -> list:
    print("Getting matches...")
    with open(input, 'r') as f:
        lines = f.read().splitlines()
    # get IDs only
    lines = [line.split('/')[-1] for line in lines] 
    
    print("Matches loaded.")
    
    return lines

def api_call(matchlist: list[int]):
    matches_maps = []
    for match in matchlist:
        # get stuff
        match_response = api.match(match)

        # sort into events and users
        all_events = match_response.events
        
        # filter for maps played
        matches_maps.append([(event.game.beatmap_id, event.game.scores) for event in all_events if event.detail.type == ossapi.MatchEventType.OTHER and event.game.scores])
    return matches_maps

def get_data(match_data: list[tuple[int, list[ossapi.Score]]], teams: Teams):
    # process api scores
    for event in match_data:
        beatmap = event[0]
        scores = event[1]
        for score in scores:
            teams.add_score(score.user_id, beatmap, score.score)
    # add disconnect scores
    with open(dc_file, 'r') as f:
        data = pd.read_csv(f, sep=',', header=0, keep_default_na=False)
        for i, row in data.iterrows():
            teams.add_score(row['User ID'], row['Map'], row['Score'])
            
    return teams

def get_stats(teams: Teams):
    stats_df = []

    for team in teams.get_team_list():
        cur_team = teams.teamscores[team]
        # skip empty teams
        if len(cur_team.get_scores()) == 0:
            continue
        stats_df.append([team, ', '.join(cur_team.get_players()), cur_team.get_avg(), cur_team.get_sum()])
    
    stats_df = pd.DataFrame(stats_df, columns=['Team', 'Players', 'Average Score', 'Total Score'])

    stats_df.sort_values(by='Average Score', ascending=False, inplace=True)
    stats_df.to_csv('results.csv', index=False, sep='|', encoding='utf-8', float_format='%.2f')

# ----------------------------------------------------------------------------------------------- #
# driver code
# ----------------------------------------------------------------------------------------------- #

# create api
api = Ossapi(client_id, client_secret)
# cache things
cache = UserCache()

def main():
    teams = Teams()

    cache.load()
    teams.load_teams(csv_file)
    cache.save()
    
    # start processing
    matches = getmatches(matches_file)
    
    match_data = api_call(matches)

    print("Processing matches...")
    with tqdm(total=len(match_data)) as pbar:
        for match in match_data:
            
            get_data(match, teams)
            pbar.update(1)
    print("Matches processed.")
    # do stats
    get_stats(teams)
    # end of program

if __name__ == "__main__":
    main()


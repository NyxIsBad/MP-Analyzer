import ossapi
import pickle
import pandas as pd
import numpy as np
from ossapi import Ossapi
from tqdm import tqdm
import time

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
pool_file = 'pool.txt'
# disconnects file
dc_file = 'disconnects.csv'

# ----------------------------------------------------------------------------------------------- #
# classes
# ----------------------------------------------------------------------------------------------- #
# id -> user object
class UserCache:
    # initialization, with expiry time
    def __init__(self):
        self.cache = {}
        self.last_save = time.time()
    
    # user get. We cache the object because the user object doesn't change too often
    # and would be the most api intensive element otherwise
    def get(self, user_id):
        if user_id in self.cache:
            return self.cache[user_id]
        else:
            user = api.user(user_id, key=ossapi.UserLookupKey.ID).username
            self.cache[user_id] = user
            return user
    
    # simple cache save operation
    def save(self):
        with open('user_cache.pkl', 'wb') as f:
            pickle.dump((self.cache, self.last_save), f)
            f.close()

    # load cache from file
    def load(self):
        try:
            # retrieve the cache
            with open('user_cache.pkl', 'rb') as f:
                self.cache, self.last_save = pickle.load(f)
                # if it's been a week since the last save, clear cache
                # it will be regenerated on the next run
                if time.time() - self.last_save > 60*60*24*7:
                    self.cache = {}
                f.close()
        except FileNotFoundError: # no cache
            pass
            # passing leaves cache empty, which means we regenerate and save it later

# teams is a list of all teams' scores and their player references.
class Teams:
    # initialize
    def __init__(self):
        # references, this can be implemented much better, but dicts are fast lol
        self.idtoteam = {}
        self.teamtoid = {}
        # dict of team name -> teamscores object
        self.teamscores = {}
        self.maplist = getmaps(pool_file)

    # get teams from the team_csv file.
    def load_teams(self, team_csv):
        print("Getting teams...")
        data = pd.read_csv(team_csv, sep='|', header=0, keep_default_na=False)
        # I'm aware that iterrows is a horrible way of treating pandas dataframes
        # However, I choose to believe that the dataset is small enough that it doesn't matter
        # given that we'll never exceed a few hundred players in any one tournament
        for i, row in data.iterrows():
            self.idtoteam[row[csv_columns[0]]] = row[csv_columns[1]]
            self.teamtoid[row[csv_columns[1]]] = row[csv_columns[0]]
            if row[csv_columns[1]] not in self.teamscores.keys():
                self.teamscores[row[csv_columns[1]]] = TeamScores(row[csv_columns[1]], self.maplist)

        teamlist = self.get_team_list()
        with tqdm(total=len(teamlist)) as pbar:
            for teamname in teamlist:
                self.teamscores[teamname].set_players([cache.get(user_id) for user_id in self.get_ids(teamname)])
                pbar.update(1)
        print("Teams loaded.")

    # get methods
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
    
    # add score to the team. we do this by handing it off to the team object
    def add_score(self, user_id, map_id, score):
        team = self.get_team(user_id)
        # if the user is not in a team, we don't care about them
        if team is None:
            print(f"User {user_id} not in a team.")
            return
        if map_id not in self.maplist:
            print(f"Map {map_id} not in pool.")
            return
        self.teamscores[team].add_score(user_id, map_id, score)
    
    # debug print method
    def __str__(self):
        return 'Teams OBJ:' + str(self.idtoteam) +'\n'.join([f"{team.get_team()}: {[str(obj) for obj in team.get_scores()]}" for team in self.teamscores.values()])

# 1 level lower than Teams
class TeamScores:
    # initialization
    def __init__(self, team, maps, players=None):
        self.team = team
        self.scores = []
        self.maps = maps
        self.players = players if players else []
        for map_id in maps:
            self.scores.append(MapScores(map_id))
    
    # add score method, once again handed off to the MapScores object
    def add_score(self, user_id, map_id, score):
        for map_item in self.scores:
            if map_item.get_map() == map_id:
                map_item.add_score(user_id, score)
                break
    
    # setters and getters
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
    
    # method for stats later
    def get_performance(self):
        return [f"{map.get_sum()} - {', '.join(map.get_usernames())}" for map in self.scores]
    
    def get_team(self):
        return self.team
    
    # debug print method
    def __str__(self):
        return f"{self.team}: {str(self.scores)}"

# Last level, has individual maps. Map ID, users, with their scores
class MapScores:
    # initialization
    def __init__(self, map_id: int):
        self.scores = {}
        self.map = map_id

    # add score method
    def add_score(self, user_id, score):
        self.scores[user_id] = score
    
    # getters
    def get_scores(self):
        return self.scores
    
    def get_map(self):
        return self.map
    
    def get_sum(self):
        if len(self.scores) == 0:
            return 0
        return sum(self.scores.values())
    
    # this is the reason why user cache is relevant. Note that this method is only used for loading teams
    def get_usernames(self):
        return [cache.get(user_id) for user_id in self.scores.keys()]
    
    def get_avg(self):
        if len(self.scores) == 0:
            return 0
        return np.mean(list(self.scores.values()))
    
    # Debug print method
    def __str__(self):
        return f'Map {self.map}: ' + str(self.scores)
# ----------------------------------------------------------------------------------------------- #
# match stuff
# ----------------------------------------------------------------------------------------------- #
# Get ids from match file. Easy split method
def getmatches(input) -> list:
    print("Getting matches...")
    with open(input, 'r') as f:
        lines = f.read().splitlines()
    # get IDs only
    lines = [line.split('/')[-1] for line in lines] 
    
    print("Matches loaded.")
    
    return lines

# Get maps from match file. Easy split method
def getmaps(input) -> list:
    print("Getting maps...")
    with open(input, 'r') as f:
        lines = f.read().splitlines()
    print("Maps loaded.")
    lines = [int(line) for line in lines]
    return lines

# API call to get match data
# You could technically cache matches but it's not really worth it given how few calls it takes
def api_call(matchlist: list[int]):
    matches_maps = []
    with tqdm(total=len(matchlist)) as pbar:
        for match in matchlist:
            # get stuff
            match_response = api.match(match, limit=None)

            # sort into events and users
            all_events = match_response.events
            first_id = match_response.events[0].id
            last_id = match_response.events[-1].id

            while True and first_id != match_response.first_event_id:
                first_response = api.match(match, before_id=first_id)
                first_events = first_response.events
                matches_maps.append([(event.game.beatmap_id, event.game.scores) for event in first_events if event.detail.type == ossapi.MatchEventType.OTHER and event.game.scores])
                if len(first_events) == 0:
                    break
                first_id = first_response.events[0].id
            while True and last_id != match_response.latest_event_id:
                last_response = api.match(match, after_id=last_id)
                last_events = last_response.events
                matches_maps.append([(event.game.beatmap_id, event.game.scores) for event in last_events if event.detail.type == ossapi.MatchEventType.OTHER and event.game.scores])
                if len(last_events) == 0:
                    break
                last_id = last_response.events[-1].id
            
            # filter for maps played
            matches_maps.append([(event.game.beatmap_id, event.game.scores) for event in all_events if event.detail.type == ossapi.MatchEventType.OTHER and event.game.scores])
            pbar.update(1)
    return matches_maps

# Extract data from object format provided by ossapi
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
        # I'm aware that iterrows is a horrible way of treating pandas dataframes
        # However, I choose to believe that the dataset is small enough that it doesn't matter
        # given that we'll never exceed a few hundred players in any one tournament
        for i, row in data.iterrows():
            teams.add_score(row['User ID'], row['Map'], row['Score'])
        
    return teams

# get stats by calling methods. This is omegajank because of the way I make it a csv
def get_stats(teams: Teams):
    stats_df = []
    
    for team in teams.get_team_list():
        cur_team = teams.teamscores[team]
        # skip empty teams
        if cur_team.get_avg() == 0:
            continue
        stats_df.append([team, ', '.join(cur_team.get_players()), cur_team.get_avg(), cur_team.get_sum()]+cur_team.get_performance())
    
    stats_df = pd.DataFrame(stats_df, columns=['Team', 'Players', 'Average Score', 'Total Score']+teams.maplist)

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
    print("Stats saved.")
    cache.save()
    # end of program

if __name__ == "__main__":
    main()


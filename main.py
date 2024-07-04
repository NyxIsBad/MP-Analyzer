# Current limitations:
# only works on quals matches where 1 team is in each match, and also when there are no dcs
# Fixing multiple teams seems simple enough, you just need a team indexer
# But fixing dcs is a bit more complicated, you need to make the np array homogenous OR
# use a non np solution


import ossapi
import pickle
import numpy as np
from ossapi import Ossapi
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

client_id = '***REMOVED***'
client_secret = '***REMOVED***'
# create api
api = Ossapi(client_id, client_secret)

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

def getmatches() -> list:
    print("Getting matches...")
    with open('matches.txt', 'r') as f:
        lines = f.read().splitlines()
    # get IDs only
    lines = [line.split('/')[-1] for line in lines] 
    
    print("Matches loaded.")
    
    return lines

def api_call(matchlist):
    matches_maps = []
    for match in matchlist:
        # get stuff
        match_response = api.match(match)

        # sort into events and users
        all_events = match_response.events
        
        # filter for maps played
        matches_maps.append([event for event in all_events if event.detail.type == ossapi.MatchEventType.OTHER])
    return matches_maps    

def get_data(match_data: list[ossapi.MatchEvent], cache: UserCache):
    
    cur_match_data = []
    for event in match_data:
        # ensure that we have the right object
        if event.game.scores:
            cur_scores = event.game.scores 
            # process scores
            unformatted_scores = [score for score in cur_scores if score.score > 0]
            formatted_scores = [[cache.get(score.user_id), score.user_id, score.accuracy, score.mods, score.score, score.max_combo] for score in unformatted_scores]
            cur_match_data.append(formatted_scores)
    
    # homogenize the array because it's possible to have DCs
    

    return np.array(cur_match_data)

def get_stats(match_data: list[list]):
    # get usernames and stats. This is the function to modify to get individual stats/etc
    pick_data = []
    for map_data in match_data:
        pick_data.append([list(map_data[:, 0]), np.sum(map_data[:, 4])])

    
    # get unique users and return average score
    unique_users = np.unique(np.concatenate([data[0] for data in pick_data]))
    return unique_users, np.average([data[1] for data in pick_data])
 
def main():
    # cache things
    cache = UserCache()
    cache.load()

    # start processing
    matches = getmatches()
    
    match_data = api_call(matches)
    

    with tqdm(total=len(match_data)) as pbar:
        with open('results.csv', 'w') as f:
            for match in match_data:
                
                cur_match_data = get_data(match, cache)
                
                if len(cur_match_data) == 0:
                    pbar.update(1)
                    continue

                match_data_results = get_stats(cur_match_data)
                f.write(f"Users: {match_data_results[0]} | Average score: {match_data_results[1]}\n")
                pbar.update(1)
            f.close()
    # save cache
    cache.save()

if __name__ == "__main__":
    main()
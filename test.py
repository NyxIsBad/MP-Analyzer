import time
import pickle

# Load the user cache from the pickle file
with open('user_cache.pkl', 'rb') as file:
    user_cache, last_time = pickle.load(file)
with open('user_cache.pkl', 'wb') as file:
    pickle.dump((user_cache, time.time()), file)

# Print the loaded user cache to verify
print(user_cache)
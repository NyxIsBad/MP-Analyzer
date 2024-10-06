from ossapi import Ossapi 
from tqdm import tqdm
import time

# Create an instance of the Ossapi class
with open('secrets.txt', 'r') as tokens_file:
    client_id = tokens_file.readline().strip()
    client_secret = tokens_file.readline().strip()
    tokens_file.close()
api = Ossapi(client_id, client_secret)

start = 115738000
end = 115765000

def list_matches(output_file, start, end):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('ID|Match Name|Link\n')
        for i in tqdm(range(start, end), desc="Listing matches"):
            try:
                match = api.match(match_id=i).match
                if match is not None:
                    outfile.write(f"{i}|{match.name}|https://osu.ppy.sh/community/matches/{i}\n")
                    print(f"{i}|{match.name}|https://osu.ppy.sh/community/matches/{i}") 
            except ValueError as e:
                # Catch the ValueError and print the error message
                print(f"An error occurred for match {i}: {e}")
                outfile.write(f"{i}|FLAG_VALUE_ERROR|https://osu.ppy.sh/community/matches/{i}\n")
            except Exception as e:
                # Catch any other exceptions and print the error message
                print(f"An unexpected error occurred for match {i}: {e}")

output_file = 'scanner.csv'
list_matches(output_file, start, end)
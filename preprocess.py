from ossapi import Ossapi 
from tqdm import tqdm

# Create an instance of the Ossapi class
with open('secrets.txt', 'r') as tokens_file:
    client_id = tokens_file.readline().strip()
    client_secret = tokens_file.readline().strip()
    tokens_file.close()
api = Ossapi(client_id, client_secret)

# Python script to read 'pre_teams.csv' and transform the data

def process_teams_file(input_file, output_file):
    total_lines = sum(1 for line in open(input_file))
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        outfile.write('User ID|Player|Discord|Team\n')
        for line in tqdm(infile, total=total_lines, desc="Processing teams"):
            # Split the line by '|', with the first element being the team and the rest being names
            parts = line.strip().split('|')
            team = parts[0]
            names = parts[1:]
            
            # Write each name paired with the team to the output file
            for name in names:
                user_id = api.user(user=name,mode='osu',key='username').id
                outfile.write(f"{user_id}|{name}||{team}\n")

# Use the function with appropriate file names
input_file = 'pre_teams.csv'
output_file = 'teams.csv'

process_teams_file(input_file, output_file)

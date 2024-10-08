from ossapi import Ossapi
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor

# Create an instance of the Ossapi class
with open('secrets.txt', 'r') as tokens_file:
    client_id = tokens_file.readline().strip()
    client_secret = tokens_file.readline().strip()
    tokens_file.close()
api = Ossapi(client_id, client_secret)

start = 115770287
end =   115777325

def list_matches_chunk(output_file, start, end):
    with open(output_file, 'a', encoding='utf-8') as outfile:  # 'a' mode to append to the same file
        for i in range(start, end):
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

def divide_range_and_run(output_file, start, end, num_threads=4):
    # Divide the range into equal parts based on the number of threads
    chunk_size = (end - start) // num_threads
    ranges = [(start + i * chunk_size, start + (i + 1) * chunk_size) for i in range(num_threads)]
    
    # Ensure the last chunk includes the remaining part
    ranges[-1] = (ranges[-1][0], end)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for range_start, range_end in ranges:
            futures.append(executor.submit(list_matches_chunk, output_file, range_start, range_end))
        
        # Ensure all threads finish execution
        for future in futures:
            future.result()

output_file = 'scanner.csv'

# Write header to the file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('ID|Match Name|Link\n')

try:
    # Run the function with multithreading
    divide_range_and_run(output_file, start, end, num_threads=4)
except KeyboardInterrupt:
    print("\nProcess interrupted by user. Dying.")

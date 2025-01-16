import json
import json_stream
import time

file_path = 'sounds.hbat'
def read_with_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data.get('process')

def read_with_json_stream(file_path):
    with open(file_path, 'r') as file:
        data = json_stream.load(file)
        for key, value in data.items():
            if key == 'process':
                # Access the process data directly
                process_data = {k: v for k, v in value.items()}
                return process_data

# Measure time for json
start_time = time.time()
process_data_json = read_with_json(file_path)
json_duration = time.time() - start_time
print(f"Process data using json: {process_data_json}")
print(f"Time taken with json: {json_duration:.6f} seconds")

# Measure time for json_stream
start_time = time.time()
process_data_json_stream = read_with_json_stream(file_path)
json_stream_duration = time.time() - start_time
print(f"Process data using json_stream: {process_data_json_stream}")
print(f"Time taken with json_stream: {json_stream_duration:.6f} seconds")
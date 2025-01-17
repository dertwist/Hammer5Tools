import os
import time
from tabulate import tabulate
from src.common import Kv3ToJson, JsonToKv3

def measure_time(func, *args, **kwargs):
    """Utility function to measure the execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def process_file(file_path):
    """Process a single file: read, convert to JSON, convert back to KV3, and write."""
    # Measure time to open, read, and convert to JSON
    with open(file_path, 'r') as file:
        data, read_time = measure_time(file.read)
        kv3_data, kv3_to_json_time = measure_time(Kv3ToJson, data)

    # Measure time to convert back to KV3 and write
    json_data, json_to_kv3_time = measure_time(JsonToKv3, kv3_data)
    with open(file_path, 'w') as file:
        _, write_time = measure_time(file.write, json_data)

    return read_time, kv3_to_json_time, json_to_kv3_time, write_time

def main(directory):
    """Main function to process all files in the given directory and display results."""
    results = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            read_time, kv3_to_json_time, json_to_kv3_time, write_time = process_file(file_path)
            results.append([filename, read_time, kv3_to_json_time, json_to_kv3_time, write_time])

    # Display results in a table
    headers = ["Filename", "Read Time (s)", "KV3 to JSON Time (s)", "JSON to KV3 Time (s)", "Write Time (s)"]
    print(tabulate(results, headers=headers, floatfmt=".6f"))

if __name__ == "__main__":
    directory = "documents"
    main(directory)
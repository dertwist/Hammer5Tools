import re, unicodedata, random, string
def normalize_name(input_name):
    # Replace non-ASCII characters with closest ASCII equivalents
    normalized_name = unicodedata.normalize('NFKD', input_name).encode('ASCII', 'ignore').decode('ASCII')

    # Replace spaces and non-word characters with underscores
    normalized_name = re.sub(r'\W+', '_', normalized_name.lower())

    # Remove leading and trailing underscores
    normalized_name = normalized_name.strip('_')

    return normalized_name

# random
def random_char(y):
    return ''.join(random.choice(string.ascii_letters) for x in range(y))

# waiting untile the required number of files is in the folder
# def wait_until_file_count(folder_path, target_count):
#     while True:
#         try:
#             file_count = len(os.listdir(folder_path))
#         except:
#             os.makedirs(folder_path)
#             file_count = len(os.listdir(folder_path))
#         if file_count >= target_count:
#             break
#         else:
#             print(f"Waiting for {target_count - file_count} more files...")
#             time.sleep(5)  # Adjust the sleep time as needed
#     print(f"Found {target_count} files in {folder_path}. Proceeding...")\

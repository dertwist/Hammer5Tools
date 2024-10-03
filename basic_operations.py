import re, unicodedata, random, string
def normalize_name(input_name):
    normalized_name = unicodedata.normalize('NFKD', input_name).encode('ASCII', 'ignore').decode('ASCII')
    normalized_name = re.sub(r'\W+', '_', normalized_name.lower())
    normalized_name = normalized_name.strip('_')

    return normalized_name
def random_char(y):
    return ''.join(random.choice(string.ascii_letters) for x in range(y))

from os.path import exists, isfile


def read_file(filepath: str, default: str = ''):
    if not isfile(filepath) or not exists(filepath):
        return default
    with open(filepath, 'r') as f:
        return f.read()

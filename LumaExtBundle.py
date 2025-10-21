class Raw:
    def __init__(self, data):
        self.data = data


class DictToDict:
    def __init__(self, keys: list = [], values: list = []):
        self.keys = keys
        self.values = values

    def __getitem__(self, key):
        return self.values[self.keys.index(key)]

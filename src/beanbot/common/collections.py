from collections import defaultdict


class defaultdictstateless(defaultdict):
    """This implementation of defaultdict doesn't add a missing key to the dictionary, compared to the original defaultdict"""

    def __missing__(self, key):
        return self.default_factory()

__author__ = 'DarkSupremo'


class Channel:
    def __init__(self):
        self.id = None
        self.unknown1 = None
        self.unknown2 = None
        self.verbosity_default = None
        self.verbosity_current = None
        self.RGBA_Override = None
        self.name = None

    def __repr__(self):
        return str(self.id) + " | " + self.name
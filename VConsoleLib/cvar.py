__author__ = 'DarkSupremo'


class Cvar:
    def __init__(self):
        self.name = None
        self.unknown = None
        self.flags = None
        self.rangemin = None
        self.rangemax = None
        self.padding = None

    def __repr__(self):
        return '"%s" with range [%f, %f] and flags %d' % (self.name, self.rangemin, self.rangemax, self.flags)
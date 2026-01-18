__author__ = 'DarkSupremo'

from .binary import BinaryStream
from .cvar import Cvar


class PacketCVAR:
    def __init__(self, stream, cvars):
        """
        @type stream: BinaryStream
        @type cvars: list
        """

        self.stream = stream
        self.cvar = Cvar()

        self.cvar.name = stream.readBytesNullTerminated(64)
        self.cvar.unknown = stream.readInt32()
        self.cvar.flags = stream.readInt32()
        self.cvar.rangemin = stream.readFloat()
        self.cvar.rangemax = stream.readFloat()
        self.cvar.padding = stream.readByte()
        cvars.append(self.cvar)

    def __repr__(self):
        return '"%s" with range [%f, %f] and flags %d' % (self.cvar.name, self.cvar.rangemin, self.cvar.rangemax, self.cvar.flags)
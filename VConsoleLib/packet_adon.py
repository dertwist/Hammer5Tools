__author__ = 'DarkSupremo'

from .binary import BinaryStream

class PacketADON:
    def __init__(self, stream):
        """
        @type stream: BinaryStream
        """
        self.stream = stream

        self.unknown = stream.readInt16()
        self.length = stream.readInt16()
        try:
            self.name = stream.readAllBytes().decode('utf-8', errors='ignore')
        except:
            self.name = "Unknown"

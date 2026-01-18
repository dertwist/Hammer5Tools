__author__ = 'DarkSupremo'



class PacketAINF:
    def __init__(self, stream):
        """
        @type stream: BinaryStream
        """
        self.stream = stream

        self.unknown1 = stream.readInt32()
        self.unknown2 = stream.readInt32()
        self.unknown3 = stream.readInt32()
        self.unknown4 = stream.readInt32()
        self.unknown5 = stream.readInt32()
        self.unknown6 = stream.readInt32()
        self.unknown7 = stream.readInt32()
        self.unknown8 = stream.readInt32()
        self.unknown9 = stream.readInt32()
        self.unknown10 = stream.readInt32()
        self.unknown11 = stream.readInt32()
        self.unknown12 = stream.readInt32()
        self.unknown13 = stream.readInt32()
        self.unknown14 = stream.readInt32()
        self.unknown15 = stream.readInt32()
        self.unknown16 = stream.readInt32()
        self.unknown17 = stream.readInt32()
        self.unknown18 = stream.readInt32()
        self.unknown19 = stream.readInt32()
        self.padding = stream.readByte()

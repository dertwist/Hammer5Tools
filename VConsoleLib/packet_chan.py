from .channel import Channel
from .binary import BinaryStream

__author__ = 'DarkSupremo'

class PacketCHAN:
    def __bytes_to_hex(self, data):
        return "".join("{0:02x}".format(c) for c in data)

    def __init__(self, stream, channels):
        """
        @type stream: BinaryStream
        """
        self.length = stream.readInt16()
        for index in range(self.length):
            channel = Channel()
            channel.id = stream.readInt32()
            channel.unknown1 = stream.readInt32()
            channel.unknown2 = stream.readInt32()
            channel.verbosity_default = stream.readInt32()
            channel.verbosity_current = stream.readInt32()

            R = stream.readByte()
            G = stream.readByte()
            B = stream.readByte()
            A = stream.readByte()

            channel.RGBA_Override = self.__bytes_to_hex(R+G+B)

            channel.name = stream.readBytesNullTerminated(34)
            channels.append(channel)

    def channelById(self, channel_id, channels):
        """
        :return: Channel
        """
        for channel in channels:
            if channel.id == channel_id:
                return channel
        # Return a dummy channel object instead of a string to prevent attribute errors
        dummy = Channel()
        dummy.name = 'Unknown: ' + str(channel_id)
        dummy.RGBA_Override = '000000'
        return dummy

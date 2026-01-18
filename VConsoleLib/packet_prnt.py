__author__ = 'DarkSupremo'

class PacketPRNT:
    def __init__(self, stream):
        self.stream = stream

        self.channelID = stream.readInt32()
        self.unknow = stream.readBytes(24)
        msg_bytes = stream.readAllBytes()
        try:
            self.msg = msg_bytes.decode('utf-8', errors='replace')
        except:
            self.msg = str(msg_bytes)

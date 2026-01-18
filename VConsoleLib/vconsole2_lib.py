import struct
import time
import socket
from threading import Thread

# Relative imports for Python 3 compatibility
from .packet_prnt import PacketPRNT
from .packet_ainf import PacketAINF
from .packet_adon import PacketADON
from .packet_chan import PacketCHAN
from .packet_cvar import PacketCVAR
from .packet_cfgv import PacketCFGV
from .binary import BinaryStream

__author__ = 'DarkSupremo'


class VConsole2Lib:
    def __init__(self):
        self.stream = None
        self.channels = list()
        self.cvars = list()
        self.ainf = None
        self.adon_name = None
        self.on_prnt_received = None
        self.on_cvars_loaded = None
        self.on_adon_received = None
        self.on_disconnected = None
        self.ignore_channels = []
        self.client_socket = None
        self.log_to_screen = True
        self.log_to_file = None
        self.html_output = False
        self.channels_custom_color = {}

    def connect(self, ip='127.0.0.1', port=29000):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, port))

            thread = Thread(target=self.__listen)
            thread.start()
            return True
        except Exception as e:
            # print(f"Connection failed: {e}")
            return False

    def send_cmd(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.encode('utf-8')

        cmd_array = bytearray()
        cmd_array.extend(bytearray(b"CMND"))

        # CHANGED: 0xD2 (210) -> 0xD4 (212) to match new protocol version
        cmd_array.extend(bytearray([0x00, 0xD4, 0x00, 0x00]))

        cmd_array.extend(bytearray(struct.pack("!h", (len(cmd) + 13))))
        cmd_array.extend(bytearray([0x00, 0x00]))
        cmd_array.extend(bytearray(cmd))
        cmd_array.append(0x00)

        try:
            self.client_socket.send(cmd_array)
        except Exception as e:
            print(f"Error sending command: {e}")

    def log(self, text, color='000000'):
        if self.log_to_file:
            with open(self.log_to_file, "a") as myfile:
                if self.html_output:
                    myfile.write(
                        '<span style="color:#%s; display:block">[%s] %s</span>' % (color, time.strftime("%H:%M:%S"),
                                                                                   text))
                else:
                    myfile.write("[%s] %s" % (time.strftime("%H:%M:%S"), text))
        if self.log_to_screen:
            print("[%s] %s" % (time.strftime("%H:%M:%S"), text))

    def __bytes_to_hex(self, data):
        return ":".join("{0:02x}".format(c) for c in data)

    def __listen(self):
        cvars_loaded = False
        channel = None

        try:
            while True:
                self.stream = BinaryStream(self.client_socket)
                self.stream.load_packet_info()

                if self.stream.msg_type == 'PRNT':
                    prnt = PacketPRNT(self.stream)
                    # Check if we can resolve the channel name
                    if hasattr(channel, 'channelById'):
                        this_channel = channel.channelById(prnt.channelID, self.channels)
                    else:
                        this_channel = None
                        for ch in self.channels:
                            if ch.id == prnt.channelID:
                                this_channel = ch
                                break
                        if not this_channel:
                            # Create dummy if missing
                            from .channel import Channel
                            this_channel = Channel()
                            this_channel.name = f"Unknown:{prnt.channelID}"
                            this_channel.RGBA_Override = "000000"

                    if this_channel.name not in self.ignore_channels:
                        color = this_channel.RGBA_Override
                        if this_channel.name in self.channels_custom_color:
                            color = self.channels_custom_color[this_channel.name]
                        self.log("PRNT (%s): %s" % (this_channel.name, prnt.msg), color)
                        if self.on_prnt_received:
                            self.on_prnt_received(self, this_channel.name, prnt.msg)

                elif self.stream.msg_type == 'AINF':
                    self.ainf = PacketAINF(self.stream)
                elif self.stream.msg_type == 'ADON':
                    adon = PacketADON(self.stream)
                    self.adon_name = adon.name
                    self.log("ADON: %s \n" % (self.adon_name))
                    if self.on_adon_received:
                        self.on_adon_received(self, self.adon_name)
                elif self.stream.msg_type == 'CHAN':
                    channel = PacketCHAN(self.stream, self.channels)
                elif self.stream.msg_type == 'CVAR':
                    PacketCVAR(self.stream, self.cvars)
                elif self.stream.msg_type == 'CFGV':
                    PacketCFGV(self.stream)
                    if not cvars_loaded and self.on_cvars_loaded:
                        cvars_loaded = True
                        self.on_cvars_loaded(self, self.cvars)
                else:
                    self.stream.readAllBytes()

        except (socket.error, ValueError, struct.error) as error:
            # print(f"Disconnected or Packet Error: {error}")
            if self.on_disconnected:
                self.on_disconnected(self)

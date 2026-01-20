import struct
import time
import socket
from threading import Thread, Event, Lock
import logging

# Relative imports for Python 3 compatibility
from .packet_prnt import PacketPRNT
from .packet_ainf import PacketAINF
from .packet_adon import PacketADON
from .packet_chan import PacketCHAN
from .packet_cvar import PacketCVAR
from .packet_cfgv import PacketCFGV
from .binary import BinaryStream, InvalidPacketError

__author__ = 'DarkSupremo'


class ConnectionState:
    """Enum for connection states"""
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    RECONNECTING = 3


class VConsole2Lib:
    def __init__(self):
        self.stream = None
        self.channels = list()
        self.cvars = list()
        self.ainf = None
        self.adon_name = None
        
        # Callbacks
        self.on_prnt_received = None
        self.on_cvars_loaded = None
        self.on_adon_received = None
        self.on_disconnected = None
        self.on_connected = None
        self.on_reconnecting = None
        self.on_packet_error = None
        
        self.ignore_channels = []
        self.client_socket = None
        self.log_to_screen = True
        self.log_to_file = None
        self.html_output = False
        self.channels_custom_color = {}
        
        # Connection management
        self._connection_state = ConnectionState.DISCONNECTED
        self._listen_thread = None
        self._reconnect_thread = None
        self._stop_event = Event()
        self._socket_lock = Lock()
        
        # Configuration
        self.ip = '127.0.0.1'
        self.port = 29000
        self.reconnect_delay = 5.0
        self.socket_timeout = 10.0  # Reduced from 30s for better responsiveness
        self.auto_reconnect = True
        self.max_reconnect_attempts = 0
        self.skip_invalid_packets = True
        self.max_invalid_packet_warnings = 10  # Only log first N invalid packets
        
        # Statistics
        self._packets_received = 0
        self._packets_skipped = 0
        self._invalid_warnings_shown = 0
        
        # Setup logging
        self.logger = logging.getLogger('VConsole2Lib')
        
    @property
    def is_connected(self):
        """Check if currently connected"""
        return self._connection_state == ConnectionState.CONNECTED
    
    @property
    def connection_state(self):
        """Get current connection state"""
        return self._connection_state
    
    @property
    def packets_received(self):
        """Get number of packets received"""
        return self._packets_received
    
    @property
    def packets_skipped(self):
        """Get number of invalid packets skipped"""
        return self._packets_skipped
    
    @property
    def packet_success_rate(self):
        """Get packet success rate (0.0 - 1.0)"""
        total = self._packets_received + self._packets_skipped
        if total == 0:
            return 0.0
        return self._packets_received / total

    def connect(self, ip='127.0.0.1', port=29000):
        """Connect to VConsole server"""
        self.ip = ip
        self.port = port
        
        if self._connection_state != ConnectionState.DISCONNECTED:
            self.logger.warning("Already connected or connecting")
            return False
        
        self._stop_event.clear()
        self._packets_received = 0
        self._packets_skipped = 0
        self._invalid_warnings_shown = 0
        return self._establish_connection()
    
    def _establish_connection(self):
        """Internal method to establish socket connection"""
        try:
            self._connection_state = ConnectionState.CONNECTING
            
            with self._socket_lock:
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.settimeout(self.socket_timeout)
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.client_socket.connect((self.ip, self.port))
            
            self._connection_state = ConnectionState.CONNECTED
            
            self._listen_thread = Thread(target=self.__listen, daemon=True)
            self._listen_thread.start()
            
            if self.on_connected:
                try:
                    self.on_connected(self)
                except Exception as e:
                    self.logger.error(f"Error in on_connected callback: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._connection_state = ConnectionState.DISCONNECTED
            
            if self.auto_reconnect and not self._stop_event.is_set():
                self._start_reconnect()
            
            return False
    
    def _start_reconnect(self):
        """Start reconnection thread"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        
        self._reconnect_thread = Thread(target=self.__reconnect_loop, daemon=True)
        self._reconnect_thread.start()
    
    def __reconnect_loop(self):
        """Reconnection loop"""
        attempt = 0
        
        while not self._stop_event.is_set():
            if self._connection_state == ConnectionState.CONNECTED:
                break
            
            attempt += 1
            
            if self.max_reconnect_attempts > 0 and attempt > self.max_reconnect_attempts:
                self.logger.error("Max reconnection attempts reached")
                break
            
            self._connection_state = ConnectionState.RECONNECTING
            
            if self.on_reconnecting:
                try:
                    self.on_reconnecting(self, attempt)
                except Exception as e:
                    self.logger.error(f"Error in on_reconnecting callback: {e}")
            
            self.logger.info(f"Reconnection attempt {attempt}...")
            
            if self._establish_connection():
                self.logger.info("Reconnected successfully")
                break
            
            self._stop_event.wait(self.reconnect_delay)
        
        if self._stop_event.is_set():
            self._connection_state = ConnectionState.DISCONNECTED

    def disconnect(self):
        """Disconnect from server"""
        self._stop_event.set()
        self._connection_state = ConnectionState.DISCONNECTED
        
        with self._socket_lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=2.0)
        
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=2.0)

    def send_cmd(self, cmd):
        """Send command to VConsole"""
        if not self.is_connected:
            self.logger.warning("Cannot send command: not connected")
            return False
        
        if isinstance(cmd, str):
            cmd = cmd.encode('utf-8')

        cmd_array = bytearray()
        cmd_array.extend(bytearray(b"CMND"))
        cmd_array.extend(bytearray([0x00, 0xD4, 0x00, 0x00]))
        cmd_array.extend(bytearray(struct.pack("!h", (len(cmd) + 13))))
        cmd_array.extend(bytearray([0x00, 0x00]))
        cmd_array.extend(bytearray(cmd))
        cmd_array.append(0x00)

        try:
            with self._socket_lock:
                if self.client_socket:
                    self.client_socket.send(cmd_array)
            return True
        except Exception as e:
            self.logger.error(f"Error sending command: {e}")
            self._handle_disconnect()
            return False

    def _clean_text(self, text):
        """Removes null terminators, empty set symbol, and trailing newlines."""
        if not text:
            return text
        text = text.rstrip('\x00')
        text = text.replace('\u2205', '')
        text = text.rstrip('\r\n')
        return text

    def log(self, text, color='000000'):
        """Log message to file and/or screen"""
        if self.log_to_file:
            try:
                with open(self.log_to_file, "a", encoding='utf-8') as myfile:
                    if self.html_output:
                        myfile.write(
                            '<span style="color:#%s; display:block">[%s] %s</span>' % (
                                color, time.strftime("%H:%M:%S"), text
                            )
                        )
                    else:
                        myfile.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), text))
            except Exception as e:
                self.logger.error(f"Error writing to log file: {e}")
        
        if self.log_to_screen:
            print("[%s] %s" % (time.strftime("%H:%M:%S"), text))

    def _handle_disconnect(self):
        """Handle disconnection"""
        if self._connection_state == ConnectionState.DISCONNECTED:
            return
        
        prev_state = self._connection_state
        self._connection_state = ConnectionState.DISCONNECTED
        
        with self._socket_lock:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        if self.on_disconnected and prev_state == ConnectionState.CONNECTED:
            try:
                self.on_disconnected(self)
            except Exception as e:
                self.logger.error(f"Error in on_disconnected callback: {e}")
        
        if self.auto_reconnect and not self._stop_event.is_set():
            self._start_reconnect()

    def __listen(self):
        """Listen thread for incoming messages"""
        import socket as sock_module
        import struct as struct_module
        from .channel import Channel

        cvars_loaded = False
        channel = None
        last_stats_log = time.time()

        try:
            while not self._stop_event.is_set() and self.is_connected:
                try:
                    with self._socket_lock:
                        if not self.client_socket:
                            break
                        sock = self.client_socket
                    
                    self.stream = BinaryStream(sock)
                    
                    try:
                        self.stream.load_packet_info()
                        self._packets_received += 1
                        
                        # Log stats every 100 successful packets
                        if self._packets_received % 100 == 0:
                            success_rate = self.packet_success_rate * 100
                            self.logger.info(
                                f"Stats: {self._packets_received} received, "
                                f"{self._packets_skipped} skipped ({success_rate:.1f}% success)"
                            )
                        
                    except InvalidPacketError as e:
                        if self.skip_invalid_packets:
                            self._packets_skipped += 1
                            
                            # Only show first N warnings to avoid spam
                            if self._invalid_warnings_shown < self.max_invalid_packet_warnings:
                                self.logger.warning(f"Skipping invalid packet: {e}")
                                self._invalid_warnings_shown += 1
                            elif self._invalid_warnings_shown == self.max_invalid_packet_warnings:
                                self.logger.warning(
                                    f"Suppressing further invalid packet warnings "
                                    f"({self._packets_skipped} total skipped so far)"
                                )
                                self._invalid_warnings_shown += 1
                            
                            if self.on_packet_error:
                                try:
                                    self.on_packet_error(self, str(e))
                                except Exception as cb_error:
                                    self.logger.error(f"Error in on_packet_error callback: {cb_error}")
                            continue
                        else:
                            raise

                    if self.stream.msg_type == 'PRNT':
                        prnt = PacketPRNT(self.stream)
                        prnt.msg = self._clean_text(prnt.msg)

                        this_channel = None
                        for ch in self.channels:
                            if ch.id == prnt.channelID:
                                this_channel = ch
                                break
                        
                        if not this_channel:
                            this_channel = Channel()
                            this_channel.name = f"Unknown:{prnt.channelID}"
                            this_channel.RGBA_Override = "000000"

                        if this_channel.name not in self.ignore_channels:
                            if '\u2205' in this_channel.name:
                                continue

                            color = this_channel.RGBA_Override
                            if this_channel.name in self.channels_custom_color:
                                color = self.channels_custom_color[this_channel.name]

                            if prnt.msg:
                                self.log("PRNT (%s): %s" % (this_channel.name, prnt.msg), color)
                                if self.on_prnt_received:
                                    try:
                                        self.on_prnt_received(self, this_channel.name, prnt.msg)
                                    except Exception as e:
                                        self.logger.error(f"Error in on_prnt_received callback: {e}")

                    elif self.stream.msg_type == 'AINF':
                        self.ainf = PacketAINF(self.stream)
                        
                    elif self.stream.msg_type == 'ADON':
                        adon = PacketADON(self.stream)
                        self.adon_name = self._clean_text(adon.name)
                        self.log("ADON: %s" % self.adon_name)
                        if self.on_adon_received:
                            try:
                                self.on_adon_received(self, self.adon_name)
                            except Exception as e:
                                self.logger.error(f"Error in on_adon_received callback: {e}")
                                
                    elif self.stream.msg_type == 'CHAN':
                        channel = PacketCHAN(self.stream, self.channels)
                        
                    elif self.stream.msg_type == 'CVAR':
                        PacketCVAR(self.stream, self.cvars)
                        
                    elif self.stream.msg_type == 'CFGV':
                        PacketCFGV(self.stream)
                        if not cvars_loaded and self.on_cvars_loaded:
                            cvars_loaded = True
                            try:
                                self.on_cvars_loaded(self, self.cvars)
                            except Exception as e:
                                self.logger.error(f"Error in on_cvars_loaded callback: {e}")
                    else:
                        self.stream.readAllBytes()
                
                except socket.timeout:
                    continue
                
                except InvalidPacketError as e:
                    self.logger.error(f"Invalid packet error (fatal): {e}")
                    break
                    
                except (sock_module.error, ValueError, struct_module.error, OSError) as error:
                    if not self._stop_event.is_set():
                        self.logger.error(f"Socket error in listen thread: {error}")
                    break

        except Exception as e:
            if not self._stop_event.is_set():
                self.logger.error(f"Unexpected error in listen thread: {e}")
        
        finally:
            # Log final statistics
            if self._packets_received > 0 or self._packets_skipped > 0:
                success_rate = self.packet_success_rate * 100
                self.logger.info(
                    f"Session ended - Packets: {self._packets_received} received, "
                    f"{self._packets_skipped} skipped ({success_rate:.1f}% success)"
                )
            
            if not self._stop_event.is_set():
                self._handle_disconnect()

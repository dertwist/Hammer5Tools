__author__ = 'DarkSupremo'

import struct


class InvalidPacketError(Exception):
    """Raised when packet data is invalid or malformed"""
    pass


class BinaryStream:
    MAX_PACKET_SIZE = 1024 * 1024  # 1MB max packet size
    
    def __init__(self, socket):
        self.socket = socket
        self.pos = 0
        self.length = 0
        self.msg_type = None
        self.version = None
        self.handle = None

    def load_packet_info(self):
        """Load packet header information with validation"""
        try:
            # Read message type (4 bytes)
            self.msg_type = self.readBytes(4).decode('utf-8', errors='ignore')
            
            # Read version (4 bytes)
            self.version = self.readInt32()
            
            # Read length (2 bytes) - THIS IS SIGNED, so validate it
            raw_length = self.readInt16()
            
            # Validate length is positive and reasonable
            if raw_length <= 0:
                raise InvalidPacketError(f"Invalid packet length: {raw_length} (must be positive)")
            
            if raw_length > self.MAX_PACKET_SIZE:
                raise InvalidPacketError(f"Packet too large: {raw_length} bytes (max {self.MAX_PACKET_SIZE})")
            
            self.length = raw_length
            
            # Read handle (2 bytes)
            self.handle = self.readInt16()
            
        except struct.error as e:
            raise InvalidPacketError(f"Failed to unpack packet header: {e}")
        except Exception as e:
            raise InvalidPacketError(f"Error reading packet info: {e}")

    def readByte(self):
        """Read a single byte"""
        self.pos += 1
        return self._recv_validated(1)

    def readBytes(self, length):
        """Read specified number of bytes with validation"""
        if length <= 0:
            raise InvalidPacketError(f"Cannot read {length} bytes (must be positive)")
        
        if length > self.MAX_PACKET_SIZE:
            raise InvalidPacketError(f"Read size too large: {length} bytes")
        
        self.pos += length
        return self._recv_validated(length)

    def readBytesNullTerminated(self, length):
        """Read null-terminated bytes"""
        if length <= 0:
            raise InvalidPacketError(f"Cannot read {length} bytes (must be positive)")
        
        self.pos += length
        data = self._recv_validated(length).split(b'\0', 1)[0]
        try:
            return data.decode('utf-8')
        except:
            return str(data)

    def readAllBytes(self):
        """Read all remaining bytes in packet"""
        remaining = self.length - self.pos
        
        if remaining <= 0:
            return b''
        
        if remaining > self.MAX_PACKET_SIZE:
            raise InvalidPacketError(f"Remaining bytes too large: {remaining}")
        
        return self._recv_validated(remaining)

    def _recv_validated(self, length):
        """Safely receive data with validation"""
        if length <= 0:
            raise InvalidPacketError(f"Invalid recv length: {length}")
        
        try:
            data = self.socket.recv(length)
            if len(data) == 0:
                raise ConnectionError("Socket closed (received 0 bytes)")
            return data
        except Exception as e:
            raise ConnectionError(f"Socket recv error: {e}")

    def readChar(self):
        return self.unpack('b')

    def readUChar(self):
        return self.unpack('B')

    def readBool(self):
        return self.unpack('?')

    def readInt16(self):
        return self.unpack('!h', 2)

    def readUInt16(self):
        return self.unpack('!H', 2)

    def readInt32(self):
        return self.unpack('!i', 4)

    def readInt32Little(self):
        return self.unpack('i', 4)

    def readUInt32(self):
        return self.unpack('!I', 4)

    def readUInt32Little(self):
        return self.unpack('I', 4)

    def readInt64(self):
        return self.unpack('!q', 8)

    def readUInt64(self):
        return self.unpack('!Q', 8)

    def readFloat(self):
        return self.unpack('!f', 4)

    def readDouble(self):
        return self.unpack('!d', 8)

    def readString(self):
        """Read string with length prefix"""
        length = self.readUInt16()
        
        if length == 0:
            return ''
        
        if length > self.MAX_PACKET_SIZE:
            raise InvalidPacketError(f"String length too large: {length}")
        
        data = self.unpack(str(length) + 's', length)
        try:
            return data.decode('utf-8')
        except:
            return str(data)

    def unpack(self, fmt, length=1):
        """Unpack data with validation"""
        if length <= 0:
            raise InvalidPacketError(f"Invalid unpack length: {length}")
        
        self.pos += length
        data = self._recv_validated(length)
        
        try:
            return struct.unpack(fmt, data)[0]
        except struct.error as e:
            raise InvalidPacketError(f"Failed to unpack data with format '{fmt}': {e}")

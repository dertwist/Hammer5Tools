__author__ = 'DarkSupremo'

import struct


class InvalidPacketError(Exception):
    """Raised when packet data is invalid or malformed"""
    pass


class BinaryStream:
    MAX_PACKET_SIZE = 1024 * 1024  # 1MB max packet size
    PACKET_HEADER_SIZE = 12  # 4 (type) + 4 (version) + 2 (length) + 2 (handle)
    
    def __init__(self, socket):
        self.socket = socket
        self.pos = 0
        self.length = 0
        self.msg_type = None
        self.version = None
        self.handle = None
        self._buffer = b''  # Internal buffer for incomplete reads

    def _recv_exact(self, length):
        """Receive exactly 'length' bytes, handling partial reads"""
        if length <= 0:
            raise InvalidPacketError(f"Invalid recv length: {length}")
        
        data = b''
        remaining = length
        
        while remaining > 0:
            try:
                chunk = self.socket.recv(remaining)
                if len(chunk) == 0:
                    raise ConnectionError("Socket closed (received 0 bytes)")
                data += chunk
                remaining -= len(chunk)
            except Exception as e:
                if len(data) > 0:
                    raise InvalidPacketError(f"Partial packet read: got {len(data)}/{length} bytes - {e}")
                raise ConnectionError(f"Socket recv error: {e}")
        
        return data

    def load_packet_info(self):
        """Load packet header information with validation"""
        try:
            # Read entire header at once to ensure alignment
            header_data = self._recv_exact(self.PACKET_HEADER_SIZE)
            
            # Parse header
            msg_type_bytes = header_data[0:4]
            version_bytes = header_data[4:8]
            length_bytes = header_data[8:10]
            handle_bytes = header_data[10:12]
            
            # Decode message type
            try:
                self.msg_type = msg_type_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
            except:
                self.msg_type = str(msg_type_bytes)
            
            # Validate message type is printable
            if not self.msg_type or len(self.msg_type) == 0:
                raise InvalidPacketError(f"Empty message type in header")
            
            # Unpack version (big-endian int32)
            try:
                self.version = struct.unpack('!i', version_bytes)[0]
            except struct.error as e:
                raise InvalidPacketError(f"Failed to unpack version: {e}")
            
            # Unpack length (big-endian int16) - THIS CAN BE NEGATIVE!
            try:
                raw_length = struct.unpack('!h', length_bytes)[0]
            except struct.error as e:
                raise InvalidPacketError(f"Failed to unpack length: {e}")
            
            # Validate length is positive and reasonable
            if raw_length <= 0:
                raise InvalidPacketError(f"Invalid packet length: {raw_length} (must be positive)")
            
            if raw_length > self.MAX_PACKET_SIZE:
                raise InvalidPacketError(f"Packet too large: {raw_length} bytes (max {self.MAX_PACKET_SIZE})")
            
            # Length includes the header, so body size is length - header size
            # But we need to track total packet length
            self.length = raw_length
            
            # Unpack handle (big-endian int16)
            try:
                self.handle = struct.unpack('!h', handle_bytes)[0]
            except struct.error as e:
                raise InvalidPacketError(f"Failed to unpack handle: {e}")
            
            # Reset position counter (header has been read)
            self.pos = self.PACKET_HEADER_SIZE
            
        except ConnectionError:
            raise
        except InvalidPacketError:
            raise
        except Exception as e:
            raise InvalidPacketError(f"Unexpected error reading packet header: {e}")

    def readByte(self):
        """Read a single byte"""
        self.pos += 1
        return self._recv_exact(1)

    def readBytes(self, length):
        """Read specified number of bytes with validation"""
        if length <= 0:
            raise InvalidPacketError(f"Cannot read {length} bytes (must be positive)")
        
        if length > self.MAX_PACKET_SIZE:
            raise InvalidPacketError(f"Read size too large: {length} bytes")
        
        self.pos += length
        return self._recv_exact(length)

    def readBytesNullTerminated(self, length):
        """Read null-terminated bytes"""
        if length <= 0:
            raise InvalidPacketError(f"Cannot read {length} bytes (must be positive)")
        
        self.pos += length
        data = self._recv_exact(length).split(b'\0', 1)[0]
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
        
        # Read and discard remaining packet data
        return self._recv_exact(remaining)

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
        data = self._recv_exact(length)
        
        try:
            return struct.unpack(fmt, data)[0]
        except struct.error as e:
            raise InvalidPacketError(f"Failed to unpack data with format '{fmt}': {e}")

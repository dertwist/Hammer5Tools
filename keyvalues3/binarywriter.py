import enum
import array
import typing
from struct import pack
import keyvalues3 as kv3

class BinaryMagics(bytes, enum.Enum):
    VKV3 = b"VKV\x03"
    KV3_01 = b"\x013VK"
    KV3_02 = b"\x023VK"
    KV3_03 = b"\x033VK"
    @classmethod
    def is_defined(cls, magic: bytes):
        return magic in cls._value2member_map_

class BinaryTypes(enum.IntEnum):
    null = 1
    boolean = 2
    int64 = 3
    uint64 = 4
    double = 5
    string = 6
    binary_blob = 7
    array = 8
    dictionary = 9
    array_typed = 10
    int32 = 11
    uint32 = 12
    boolean_true = 13
    boolean_false = 14
    int64_zero = 15
    int64_one = 16
    double_zero = 17
    double_one = 18

types = {
    int: BinaryTypes.int64,
    float: BinaryTypes.double,
    str: BinaryTypes.string,
    list: BinaryTypes.array,
    array.array: BinaryTypes.array_typed,
    dict: BinaryTypes.dictionary,
}

zeros_ones = {
    int: {
        0: BinaryTypes.int64_zero,
        1: BinaryTypes.int64_one,
    },
    float: {
        0.0: BinaryTypes.double_zero,
        1.0: BinaryTypes.double_one,
    },
}

class BinaryV1UncompressedWriter:
    encoding = kv3.ENCODING_BINARY_UNCOMPRESSED
    def __init__(self, kv3file: kv3.KV3File, serialize_enums_as_ints: bool = False):
        self.kv3file = kv3file
        self.serialize_enums_as_ints = serialize_enums_as_ints

        self.strings: list[str] = []

    def __bytes__(self) -> bytes:
        self.strings.clear()
        return bytes(self.encode_header() + self.encode_body())

    def encode_header(self):
        return BinaryMagics.VKV3.value + self.encoding.version.bytes_le + self.kv3file.format.version.bytes_le

    def encode_body(self) -> bytes:
        value_serialized = self.value_and_type_serialize(self.kv3file.value)
        string_table = self.encode_strings()
        return string_table + value_serialized + b"\xFF\xFF\xFF\xFF"

    def encode_strings(self):
        string_table = pack("<I", len(self.strings))
        for string in self.strings:
            string_table += string.encode("utf-8")
            string_table += b"\x00"
        return string_table

    def write(self, file: typing.BinaryIO):
        file.write(bytes(self))

    def value_and_type_serialize(self, value) -> bytes:
        flags = kv3.Flag(0)
        if isinstance(value, kv3.flagged_value):
            flags = value.flags
            value = value.value
        value_type = type(value)

        def pack_type_and_flags(type: BinaryTypes, flags: kv3.Flag):
            if flags == kv3.Flag(0):
                return pack("<B", type)
            return pack("<B", type | 0x80) + pack("<B", flags)

        if value is None: return pack_type_and_flags(BinaryTypes.null, flags)
        if value is True: return pack_type_and_flags(BinaryTypes.boolean_true, flags)
        if value is False: return pack_type_and_flags(BinaryTypes.boolean_false, flags)

        if value_type in zeros_ones and value in zeros_ones[value_type]:
            return pack_type_and_flags(zeros_ones[value_type][value], flags)

        type_in_binary = None
        if value_type in types:
            type_in_binary = types[value_type]
        elif isinstance(value, enum.IntEnum):
            type_in_binary = BinaryTypes.int32 if self.serialize_enums_as_ints else BinaryTypes.string
        else:
            raise TypeError(f"Unknown type {value_type}")
        return pack_type_and_flags(type_in_binary, flags) + self.value_serialize(value)

    def value_serialize(self, value) -> bytearray:
        blob = bytearray()
        match value:
            case bool():
                ...
            case enum.IntEnum():
                if self.serialize_enums_as_ints:
                    blob += pack("<i", value.value)
                else:
                    if value == "":
                        blob += pack("<i", -1)
                    else:
                        blob += pack("<i", len(self.strings))
                        self.strings.append(value)
            case int(): blob += pack("<q", value)
            case float(): blob += pack("<d", value)
            case str():
                if value == "":
                    blob += pack("<i", -1)
                else:
                    blob += pack("<i", len(self.strings))
                    self.strings.append(value)
            case list():
                blob += pack("<i", len(value))
                for item in value:
                    blob += self.value_and_type_serialize(item)
            case array.array:
                blob += pack("<i", len(value))
                blob += pack("<B", BinaryTypes.int64)
                blob += pack("<B", kv3.Flag(0).value)
                for item in value:
                    blob += self.value_serialize(item)
            case dict():
                blob += pack("<i", len(value))
                for key, value in value.items():
                    blob += pack("<i", len(self.strings))
                    self.strings.append(key)
                    blob += self.value_and_type_serialize(value)
        return blob


import lz4.block
class BinaryLZ4(BinaryV1UncompressedWriter):
    encoding = kv3.ENCODING_BINARY_BLOCK_LZ4
    def __bytes__(self):
        self.strings.clear()
        blob = self.encode_header()
        body_uncompressed = self.encode_body()
        blob += pack("<I", len(body_uncompressed))
        blob += lz4.block.compress(body_uncompressed, store_size=False)
        return blob

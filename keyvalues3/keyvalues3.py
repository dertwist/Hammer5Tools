import array
import dataclasses
import enum
from uuid import UUID

class KV3DecodeError(ValueError): pass
class InvalidKV3Magic(KV3DecodeError): pass

@dataclasses.dataclass(frozen=True)
class _HeaderPiece:
    name: str
    version: UUID
    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f"{self!r}: name is not a valid identifier")
        if not isinstance(self.version, UUID):
            raise ValueError(f"{self!r}: version is not an UUID object")
    def __str__(self):
        return "%s:%s:version{%s}" % (self.__class__.__name__.lower(), self.name, str(self.version))

@dataclasses.dataclass(frozen=True)
class Encoding(_HeaderPiece): pass
@dataclasses.dataclass(frozen=True)
class Format(_HeaderPiece): pass

ENCODING_BINARY_UNCOMPRESSED = Encoding("binary", UUID("1b860500-f7d8-40c1-ad82-75a48267e714"))
ENCODING_BINARY_BLOCK_COMPRESSED = Encoding("binarybc", UUID("95791a46-95bc-4f6c-a70b-05bca1b7dfd2"))
ENCODING_BINARY_BLOCK_LZ4 = Format("binarylz4", UUID("6847348a-63a1-4f5c-a197-53806fd9b119"))
ENCODING_TEXT = Encoding("text", UUID("e21c7f3c-8a33-41c5-9977-a76d3a32aa0d"))

FORMAT_GENERIC = Format("generic", UUID("7412167c-06e9-4698-aff2-e63eb59037e7"))

@dataclasses.dataclass(frozen=True)
class KV3Header:
    encoding: Encoding = ENCODING_TEXT
    format: Format = FORMAT_GENERIC
    def __str__(self):
        return f"<!-- kv3 {self.encoding} {self.format} -->"


simple_types = None | bool | int | float | enum.IntEnum | str
container_types = list[simple_types] | array.array | dict[str, simple_types]
bytearrays = bytes | bytearray
ValueType = simple_types | container_types | bytearrays
"""
Any of `None` `bool` `int` `float` `enum.IntEnum` `str`
`list[ValueType]` `array.array` `dict[str, ValueType]`
`bytes` `bytearray` `flagged_value`.
"""

def check_valid(value: ValueType):
    """
    Check if a value is valid for KV3.
    Raises `ValueError`, `OverflowError`, `TypeError`.
    """
    match value:
        case flagged_value(actual_value, _):
            return check_valid(actual_value)
        case None | bool() | float() | enum.IntEnum() | str():
            pass
        case int():
            if value > 2**64 - 1: raise OverflowError("int value is bigger than biggest UInt64")
            elif value < -2**63: raise OverflowError("int value is smaller than smallest Int64")
        case list():
            for nested_value in value:
                if nested_value is value:
                    raise ValueError("list contains itself")
                check_valid(nested_value)
        case dict():
            for key, nested_value in value.items():
                if nested_value is value:
                    raise ValueError("dict contains itself")
                if not isinstance(key, str):
                    raise ValueError(f"dict key is not a string type, but {type(key)}")
                check_valid(nested_value)
        case array.array() | bytes() | bytearray():
            pass
        case _:
            raise TypeError(f"Invalid type {type(value)} for KV3 value.")

def is_valid(value: ValueType) -> bool:
    try:
        check_valid(value)
        return True
    except (ValueError, OverflowError, TypeError):
        return False

@enum.global_enum
class Flag(enum.IntFlag):
    resource = enum.auto()
    resource_name = enum.auto()
    multilinestring = enum.auto()
    panorama = enum.auto()
    soundevent = enum.auto()
    subclass = enum.auto()
    def __str__(self):
        return "|".join(flag.name for flag in self.__class__ if self.value & flag)
    def __call__(self, value: ValueType):
        return flagged_value(value, self)

class flagged_value():
    """
    Wrapper for KV3 values that have a flag attached to them.
    """
    __match_args__ = __slots__ = ("value", "flags")

    def __init__(self, value: ValueType, flags: Flag = Flag(0)):
        #assert flags.bit_count() == 1, "only one flag is allowed"
        assert isinstance(value, flagged_value) == False, "value should not be already flagged"
        self.value = value
        self.flags = flags

    def __eq__(self, other):
        if isinstance(other, flagged_value):
            return self.value == other.value and self.flags == other.flags
        else:
            if self.flags == Flag(0) or self.flags == Flag.multilinestring:
                return self.value == other
            return False

ValueType = ValueType | flagged_value

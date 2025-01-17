
import array
import enum
import keyvalues3 as kv3

class KV3EncoderOptions:
    def __init__(self, serialize_enums_as_ints: bool = False, no_header: bool = False):
        self.serialize_enums_as_ints = serialize_enums_as_ints
        self.no_header = no_header

def encode(kv3file: kv3.KV3File | kv3.ValueType, options=KV3EncoderOptions()) -> str:
    """Encode a KV3File or value to UTF-8 Text."""

    encoding = kv3.ENCODING_TEXT
    format = kv3.FORMAT_GENERIC
    value = kv3file

    if isinstance(kv3file, kv3.KV3File):
        format = kv3file.format
        value = kv3file.value

    text = ""
    if not options.no_header:
        text += str(kv3.KV3Header(encoding=encoding, format=format)) + "\n"

    def value_serialize(value: kv3.ValueType, indentation_level = 0, dictionary_value = False) -> str:
        indent = ("\t" * (indentation_level))
        indent_nested = ("\t" * (indentation_level + 1))
        match value:
            case kv3.flagged_value(value, flags):
                if flags & kv3.Flag.multilinestring:
                    return  f'"""\n{value}"""'
                if flags:
                    return f"{flags}:{value_serialize(value)}"
                return value_serialize(value)
            case None:
                return "null"
            case False:
                return "false"
            case True:
                return "true"
            case int():
                return str(value)
            case float():
                return str(round(value, 6))
            case enum.IntEnum():
                if options.serialize_enums_as_ints:
                    return str(value.value)
                return value.name
            case str():
                return '"' + value + '"'
            case list():
                qualifies_for_sameline = len(value) <= 4 and all(isinstance(item, (dict)) == False for item in value)
                if qualifies_for_sameline:
                    return "[" + ", ".join(value_serialize(item) for item in value) + "]"
                s = f"\n{indent}[\n"
                for item in value:
                    s += indent_nested + (value_serialize(item, indentation_level+1) + ",\n")
                return s + indent + "]"
            case dict():
                s = indent + "{\n"
                if dictionary_value:
                    s = "\n" + s
                for key, value in value.items():
                    if not key.isidentifier():
                        key = '"' + key + '"'
                    s += indent_nested + f"{key} = {value_serialize(value, indentation_level+1, dictionary_value=True)}\n"
                return s + indent + "}"
            case array.array():
                return "[ ]" # TODO
            case bytes() | bytearray():
                return f"#[{' '.join(f'{b:02x}' for b in value)}]"
            case _:
                raise TypeError(f"Invalid type {type(value)} for KV3 value.")

    text += value_serialize(value) + '\n'
    return text

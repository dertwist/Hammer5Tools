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

    def value_serialize(value: kv3.ValueType, indentation_level=0, dictionary_value=False, nested_list=False) -> str:
        indent = "\t" * indentation_level
        indent_nested = "\t" * (indentation_level + 1)
        match value:
            case kv3.flagged_value(value, flags):
                if flags & kv3.Flag.multilinestring:
                    return f'"""\n{value}"""'
                if flags:
                    return f"{flags}:{value_serialize(value, indentation_level, dictionary_value, nested_list)}"
                return value_serialize(value, indentation_level, dictionary_value, nested_list)
            case None:
                return "null"
            case False:
                return "false"
            case True:
                return "true"
            case int() | float():
                return str(round(value, 8) if isinstance(value, float) else value)
            case enum.IntEnum():
                return str(value.value) if options.serialize_enums_as_ints else value.name
            case str():
                return f'"{value}"'
            case list():
                if nested_list:
                    return "[" + ", ".join(value_serialize(item, indentation_level, dictionary_value, nested_list) for item in value) + "]"
                s = f"\n{indent}[\n"
                s += ",\n".join(indent_nested + value_serialize(item, indentation_level + 1, dictionary_value, nested_list=True) for item in value)
                return s + f"\n{indent}]"
            case dict():
                s = indent + "{\n"
                if dictionary_value:
                    s = "\n" + s
                for key, value in value.items():
                    key = f'"{key}"' if not key.isidentifier() else key
                    s += indent_nested + f"{key} = {value_serialize(value, indentation_level + 1, dictionary_value=True, nested_list=nested_list)}\n"
                return s + indent + "}"
            case array.array():
                return "[ ]"  # TODO
            case bytes() | bytearray():
                return f"#[{' '.join(f'{b:02x}' for b in value)}]"
            case _:
                raise TypeError(f"Invalid type {type(value)} for KV3 value.")

    text += value_serialize(value) + '\n'
    return text
import array
import enum
import keyvalues3 as kv3

class KV3EncoderOptions:
    def __init__(
        self,
        serialize_enums_as_ints: bool = False,
        no_header: bool = False,
        disable_line_value_length_limit_keys=None
    ):
        self.serialize_enums_as_ints = serialize_enums_as_ints
        self.no_header = no_header
        # Default key(s) to disable one line value length limitation.
        if disable_line_value_length_limit_keys is None:
            disable_line_value_length_limit_keys = [
                "m_vRandomPositionMax", "m_vRandomPositionMin", "m_flRandomScaleMax", "m_vRandomRotationMax",
                "m_flScale", "m_vRotation", "m_sModelName", "m_nScaleMode", "m_CoordinateSpace", "m_DirectionSpace",
                "m_GridPlacementMode", "m_GridOriginMode", "m_nNoHitResult", "m_SelectionMode", "m_PlacementMode",
                "m_DistributionMode", "m_HandleShape", "m_PointSpace", "m_PathSpace", "m_PlaceAtPositions", "m_Mode",
                "m_ApplyColorMode", "m_flBendPoint", "m_HandleSize", "m_ColorSelection", "m_HandleColor",
                "m_ColorChoices", "m_MaterialGroupName", "m_Expression", "m_StateName", "m_VariableName", "m_Comment",
                "m_VariableValue", "m_TargetName", "m_VariableComparison", "m_AllowedSurfaceProperties", 'm_nPickMode',
                "m_DisallowedSurfaceProperties", 'm_Components', 'm_flMinLength', 'm_flMaxLength', 'm_flRandomScaleMin',
                'm_flRandomScaleMax', 'm_flMaxLength', 'm_flMinLength', 'm_vRandomRotationMin', 'm_vRandomRotationMax',
                'm_flLength', 'm_vStart', 'm_vEnd'
            ]
        self.disable_line_value_length_limit_keys = disable_line_value_length_limit_keys

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

    def value_serialize(
        value: kv3.ValueType,
        indentation_level=0,
        dictionary_value=False,
        nested_list=False,
        force_single_line: bool = False
    ) -> str:
        indent = "\t" * indentation_level
        indent_nested = "\t" * (indentation_level + 1)
        match value:
            case kv3.flagged_value(val, flags):
                if flags & kv3.Flag.multilinestring:
                    return f'"""\n{val}"""'
                if flags:
                    return f"{flags}:{value_serialize(val, indentation_level, dictionary_value, nested_list, force_single_line=force_single_line)}"
                return value_serialize(val, indentation_level, dictionary_value, nested_list, force_single_line=force_single_line)
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
                if nested_list or force_single_line:
                    # When force_single_line is True, join items in one line.
                    return "[" + ", ".join(
                        value_serialize(item, indentation_level, dictionary_value, nested_list, force_single_line=force_single_line)
                        for item in value
                    ) + "]"
                s = f"\n{indent}[\n"
                s += ",\n".join(
                    indent_nested + value_serialize(item, indentation_level + 1, dictionary_value, nested_list=True)
                    for item in value
                )
                return s + f"\n{indent}]"
            case dict():
                if force_single_line:
                    # Build a compact representation in one line.
                    inner = " ".join(
                        f'{(f"""{key}""" if not key.isidentifier() else key)} = {value_serialize(val, 0, dictionary_value=True, nested_list=nested_list, force_single_line=True)}'
                        for key, val in value.items()
                    )
                    return "{" + inner + "}"
                else:
                    s = indent + "{\n"
                    if dictionary_value:
                        s = "\n" + s
                    for key, val in value.items():
                        # Format key: if not identifier, wrap in quotes.
                        key_str = f'"{key}"' if not key.isidentifier() else key
                        # Force single line formatting if key is in the disable list and length is less than 200.
                        force_flat = key in options.disable_line_value_length_limit_keys and len(str(val)) <= 200
                        s += indent_nested + f"{key_str} = {value_serialize(val, indentation_level + 1, dictionary_value=True, nested_list=nested_list, force_single_line=force_flat)}\n"
                    return s + indent + "}"
            case array.array():
                return "[ ]"  # TODO: Implement array serialization if needed.
            case bytes() | bytearray():
                return f"#[{' '.join(f'{b:02x}' for b in value)}]"
            case _:
                raise TypeError(f"Invalid type {type(value)} for KV3 value.")

    text += value_serialize(value) + "\n"
    return text
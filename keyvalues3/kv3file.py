import typing
import dataclasses
from collections.abc import MutableMapping

import keyvalues3 as kv3

@typing.runtime_checkable
class Dataclass(typing.Protocol):
    __dataclass_fields__: dict[str, dataclasses.Field]

class KV3File(MutableMapping):
    value: kv3.ValueType | Dataclass
    """The value inside this KV3 file. Usually a `dict`, but it can be any of the `kv3.Types`."""
    format: kv3.Format
    """The format of the KV3 file."""
    original_encoding: kv3.Encoding | None
    """Original encoding, if loaded from a file."""

    def __init__(self,
            value: kv3.ValueType | Dataclass = None,
            format: kv3.Format = kv3.FORMAT_GENERIC,
            validate_value: bool = True,
            original_encoding: kv3.Encoding | None = None,
            ):

        self.format = format
        self.original_encoding = original_encoding

        if isinstance(value, Dataclass) and not isinstance(value, kv3.flagged_value):
            self.value: dict = dataclasses.asdict(value)
        else:
            self.value: kv3.ValueType = value

        if validate_value:
            kv3.check_valid(self.value)
        
    def __repr__(self) -> str:
        value = repr(self.value)
        if len(value) > 100:
            value = value[:100] + '...'
        if self.format == kv3.FORMAT_GENERIC:
            return f"KV3File(value={value})"
        return f"KV3File({value}, format={self.format!r})"
    
    @staticmethod
    def __error_if_not_dictionary(method: typing.Callable) -> typing.Callable:
        def wrapper(self, *args, **kwargs):
            if not isinstance(self.value, dict):
                raise TypeError(
                    f"KV3 root value is of type '{type(self.value).__name__}', so '{method.__qualname__}' will not work."
                )
            return method(self, *args, **kwargs)
        return wrapper
        
    ## MutableMapping required methods

    @__error_if_not_dictionary
    def __getitem__(self, key):
        return self.value[key]
    
    @__error_if_not_dictionary
    def __setitem__(self, key, value):
        self.value[key] = value

    @__error_if_not_dictionary
    def __delitem__(self, key):
        del self.value[key]

    @__error_if_not_dictionary
    def __iter__(self):
        return iter(self.value)

    @__error_if_not_dictionary
    def __len__(self):
        return len(self.value)
    
    ## MutableMapping optional methods

    @__error_if_not_dictionary
    def keys(self):
        return self.value.keys()

    @__error_if_not_dictionary
    def values(self):
        return self.value.values()
        

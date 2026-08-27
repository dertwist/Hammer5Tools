"""Qt-free model for Hammer key-binding documents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HotkeyBinding:
    context: str
    command: str
    input: str | None = None


@dataclass
class HotkeyDocument:
    metadata: dict = field(default_factory=dict)
    bindings: list[HotkeyBinding] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: dict) -> "HotkeyDocument":
        metadata = {key: item for key, item in value.items() if key != "m_Bindings"}
        bindings = [
            HotkeyBinding(
                context=item.get("m_Context", ""),
                command=item.get("m_Command", ""),
                input=item.get("m_Input"),
            )
            for item in value.get("m_Bindings", [])
            if isinstance(item, dict)
        ]
        return cls(metadata=metadata, bindings=bindings)

    def find(self, context: str, command: str) -> HotkeyBinding | None:
        return next(
            (binding for binding in self.bindings
             if binding.context == context and binding.command == command),
            None,
        )

    def ensure(self, context: str, command: str) -> HotkeyBinding:
        binding = self.find(context, command)
        if binding is None:
            binding = HotkeyBinding(context, command)
            self.bindings.append(binding)
        return binding

    def to_mapping(self) -> dict:
        value = dict(self.metadata)
        value["m_Bindings"] = [
            {"m_Context": binding.context, "m_Command": binding.command, "m_Input": binding.input}
            for binding in self.bindings
            if binding.input
        ]
        return value


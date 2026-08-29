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



KV3_HEADER = (
    "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
    "format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->"
)
TAB_WIDTH = 4


def _next_stop(column: int) -> int:
    return column - column % TAB_WIDTH + TAB_WIDTH


def _literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{value}"'


def _entry_lines(entries: list[dict], indent: int) -> list[str]:
    """One line per entry, fields aligned into tab-stop columns."""
    rows = [[f"{key} = {_literal(value)}" for key, value in entry.items()] for entry in entries]
    targets, column = [], indent * TAB_WIDTH + 2  # "{ " follows the indent
    for index in range(max(len(row) for row in rows)):
        column = _next_stop(column + max(len(row[index]) for row in rows if index < len(row)))
        targets.append(column)

    # Blank line between groups only when the leading field actually repeats
    # (m_Bindings share a context; m_InputMacros each have a unique name).
    groups = [next(iter(entry.values()), None) for entry in entries]
    grouped = len(set(groups)) < len(groups)

    lines, previous = [], None
    for group, row in zip(groups, rows):
        if grouped and previous is not None and group != previous:
            lines.append("")
        previous = group
        text, column = "\t" * indent + "{ ", indent * TAB_WIDTH + 2
        for index, field in enumerate(row):
            text += field
            column += len(field)
            while column < targets[index]:
                text += "\t"
                column = _next_stop(column)
        lines.append(text + "},")
    return lines


def serialize(value: dict) -> str:
    """Render a key-binding document in Valve's hand-written layout."""
    lines = [KV3_HEADER, "{"]
    for key, item in value.items():
        if lines[-1] != "{":
            lines.append("")
        lines.append(f"\t{key} =")
        if isinstance(item, list):
            entries = [entry for entry in item if isinstance(entry, dict) and entry]
            lines.append("\t[")
            lines.extend(_entry_lines(entries, 2) if entries else [])
            lines.append("\t]")
        else:
            lines.append("\t{")
            lines.extend(f"\t\t{name} = {_literal(field)}" for name, field in item.items())
            lines.append("\t}")
    lines.append("}")
    return "\n".join(lines) + "\n"

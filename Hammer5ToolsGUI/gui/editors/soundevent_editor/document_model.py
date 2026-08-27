"""Qt-free SoundEvent document state and comment-preserving serialization."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

import keyvalues3 as kv3
from gui.editors.soundevent_editor.comment_handler import (
    extract_vsndevts_comments,
    serialize_vsndevts_with_comments,
)


@dataclass
class SoundEventDocument:
    events: dict[str, dict] = field(default_factory=dict)
    event_comments: dict[str, str] = field(default_factory=dict)
    file_header_comments: str = ""
    file_footer_comments: str = ""
    editor_info: dict | None = None
    editor_info_comments: str = ""

    @classmethod
    def from_text(cls, text: str) -> "SoundEventDocument":
        header, comments, footer = extract_vsndevts_comments(text)
        if "<!-- kv3 encoding:" not in text:
            parse_input = (
                "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{"
                + text
                + "\n}"
            )
        else:
            parse_input = text
        data = kv3.textreader.KV3TextReader().parse(parse_input).value
        editor_info = data.pop("editor_info", None) if isinstance(data, dict) else None
        return cls(
            events=deepcopy(data) if isinstance(data, dict) else {},
            event_comments={key: value for key, value in comments.items() if key != "editor_info"},
            file_header_comments=header,
            file_footer_comments=footer,
            editor_info=deepcopy(editor_info),
            editor_info_comments=comments.get("editor_info", ""),
        )

    def rename(self, old_name: str, new_name: str) -> None:
        if old_name == new_name:
            return
        value = self.events.pop(old_name)
        self.events[new_name] = value
        comment = self.event_comments.pop(old_name, None)
        if comment is not None:
            self.event_comments[new_name] = comment

    def to_text(self) -> str:
        return serialize_vsndevts_with_comments(
            self.events,
            file_header_comments=self.file_header_comments,
            event_comments=self.event_comments,
            file_footer_comments=self.file_footer_comments,
            editor_info_data=self.editor_info,
            editor_info_comments=self.editor_info_comments,
        )


"""
Comment preservation handler for SoundEvent Editor (.vsndevts files).

Extracts and serializes top-level comments (file headers, event doc-comments, and footers)
so they are preserved across load and save cycles.
"""

from typing import Dict, Tuple, Optional
import keyvalues3 as kv3
from keyvalues3.textwriter import KV3EncoderOptions


def extract_vsndevts_comments(content: str) -> Tuple[str, Dict[str, str], str]:
    """
    Scans a .vsndevts file and extracts:
      - file_header_comments: comment block before the first soundevent or editor_info definition
      - event_comments: mapping of event_name -> comment block immediately preceding it
      - file_footer_comments: comment block after the last soundevent before the closing brace
    """
    # Skip KV3 header if present
    header_end = content.find("-->")
    start_pos = 0 if header_end == -1 else header_end + 3

    root_open_idx = content.find("{", start_pos)
    if root_open_idx == -1:
        return "", {}, ""

    i = root_open_idx + 1
    n = len(content)

    file_header_comments = ""
    event_comments: Dict[str, str] = {}
    file_footer_comments = ""

    first_entry_found = False
    comment_blocks: list[list[str]] = []
    current_block: list[str] = []

    while i < n:
        c = content[i]

        if c.isspace():
            i += 1
            continue

        # Single-line comment //
        if c == '/' and i + 1 < n and content[i + 1] == '/':
            start_c = i
            end_c = content.find('\n', i)
            if end_c == -1:
                end_c = n
            comment_line = content[start_c:end_c].strip()

            # Check if separated by an empty line from previous comment
            prev_nl = content.rfind('\n', 0, start_c)
            if prev_nl != -1:
                prev_prev_nl = content.rfind('\n', 0, prev_nl)
                between = content[prev_prev_nl + 1:prev_nl] if prev_prev_nl != -1 else content[0:prev_nl]
                if between.strip() == "" and current_block:
                    comment_blocks.append(current_block)
                    current_block = []

            current_block.append(comment_line)
            i = end_c
            continue

        # Multi-line comment /* ... */
        if c == '/' and i + 1 < n and content[i + 1] == '*':
            start_c = i
            end_c = content.find('*/', i + 2)
            if end_c == -1:
                end_c = n
            else:
                end_c += 2
            comment_block = content[start_c:end_c].strip()
            current_block.append(comment_block)
            i = end_c
            continue

        # Closing brace of the root KV3 dictionary
        if c == '}':
            if current_block:
                comment_blocks.append(current_block)
                current_block = []
            if comment_blocks:
                all_footer = ["\n".join(b) for b in comment_blocks]
                file_footer_comments = "\n\n".join(all_footer)
                comment_blocks = []
            break

        # Top-level key: quoted string or identifier
        if c == '"' or c.isalnum() or c == '_':
            key = ""
            if c == '"':
                start_k = i + 1
                k_end = start_k
                while k_end < n:
                    if content[k_end] == '\\':
                        k_end += 2
                        continue
                    if content[k_end] == '"':
                        break
                    k_end += 1
                key = content[start_k:k_end]
                i = k_end + 1
            else:
                start_k = i
                k_end = i
                while k_end < n and (content[k_end].isalnum() or content[k_end] in '._-'):
                    k_end += 1
                key = content[start_k:k_end]
                i = k_end

            # Skip whitespace until assignment '='
            while i < n and content[i].isspace():
                i += 1

            if i < n and content[i] == '=':
                i += 1  # consume '='

                if current_block:
                    comment_blocks.append(current_block)
                    current_block = []

                if not first_entry_found:
                    first_entry_found = True
                    if comment_blocks:
                        if len(comment_blocks) > 1:
                            file_header_comments = "\n\n".join("\n".join(b) for b in comment_blocks[:-1])
                            event_comments[key] = "\n".join(comment_blocks[-1])
                        else:
                            last_block_text = "\n".join(comment_blocks[0])
                            if len(comment_blocks[0]) > 5:
                                file_header_comments = last_block_text
                            else:
                                prev_nl = content.rfind('\n', 0, start_k)
                                prev_prev_nl = content.rfind('\n', 0, prev_nl) if prev_nl != -1 else -1
                                between = content[prev_prev_nl + 1:prev_nl] if prev_prev_nl != -1 else ""
                                if between.strip() == "":
                                    file_header_comments = last_block_text
                                else:
                                    event_comments[key] = last_block_text
                        comment_blocks = []
                else:
                    if comment_blocks:
                        event_comments[key] = "\n\n".join("\n".join(b) for b in comment_blocks)
                        comment_blocks = []

                # Skip the value (dict, array, or scalar)
                while i < n and content[i].isspace():
                    i += 1

                if i < n:
                    if content[i] == '{':
                        brace_depth = 1
                        i += 1
                        while i < n and brace_depth > 0:
                            ch = content[i]
                            if ch == '"':
                                i += 1
                                while i < n:
                                    if content[i] == '\\':
                                        i += 2
                                        continue
                                    if content[i] == '"':
                                        i += 1
                                        break
                                    i += 1
                                continue
                            elif ch == '/' and i + 1 < n and content[i + 1] == '/':
                                end_c = content.find('\n', i)
                                i = n if end_c == -1 else end_c + 1
                                continue
                            elif ch == '/' and i + 1 < n and content[i + 1] == '*':
                                end_c = content.find('*/', i + 2)
                                i = n if end_c == -1 else end_c + 2
                                continue
                            elif ch == '{':
                                brace_depth += 1
                            elif ch == '}':
                                brace_depth -= 1
                            i += 1
                    elif content[i] == '[':
                        bracket_depth = 1
                        i += 1
                        while i < n and bracket_depth > 0:
                            ch = content[i]
                            if ch == '"':
                                i += 1
                                while i < n:
                                    if content[i] == '\\':
                                        i += 2
                                        continue
                                    if content[i] == '"':
                                        i += 1
                                        break
                                    i += 1
                                continue
                            elif ch == '/' and i + 1 < n and content[i + 1] == '/':
                                end_c = content.find('\n', i)
                                i = n if end_c == -1 else end_c + 1
                                continue
                            elif ch == '/' and i + 1 < n and content[i + 1] == '*':
                                end_c = content.find('*/', i + 2)
                                i = n if end_c == -1 else end_c + 2
                                continue
                            elif ch == '[':
                                bracket_depth += 1
                            elif ch == ']':
                                bracket_depth -= 1
                            i += 1
                    else:
                        while i < n and content[i] not in '\n\r}':
                            i += 1
            else:
                i += 1
        else:
            i += 1

    return file_header_comments, event_comments, file_footer_comments


def serialize_vsndevts_with_comments(
    events_data: Dict[str, dict],
    file_header_comments: str = "",
    event_comments: Dict[str, str] = None,
    file_footer_comments: str = "",
    editor_info_data: Optional[dict] = None,
    editor_info_comments: str = ""
) -> str:
    """
    Serializes soundevents to KV3 format preserving file header comments,
    editor_info, and pre-event doc comments.
    """
    if event_comments is None:
        event_comments = {}

    lines = []
    # Standard KV3 header
    lines.append('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->')
    lines.append('{')

    # 1. File header comments
    if file_header_comments:
        lines.append("")
        for comment_line in file_header_comments.splitlines():
            line_str = comment_line.strip()
            if line_str:
                lines.append(f"\t{line_str}")
            else:
                lines.append("")
        lines.append("")

    options = KV3EncoderOptions(serialize_enums_as_ints=False, no_header=True)

    # 2. editor_info comments & block
    ed_comment = editor_info_comments or event_comments.get("editor_info", "")
    if ed_comment:
        for comment_line in ed_comment.splitlines():
            line_str = comment_line.strip()
            if line_str:
                lines.append(f"\t{line_str}")
            else:
                lines.append("")

    if editor_info_data is None and "editor_info" in events_data:
        editor_info_data = events_data["editor_info"]

    if editor_info_data is None:
        from src.common import editor_info
        editor_info_data = editor_info.get("editor_info", {})

    if editor_info_data:
        single_kv3 = kv3.KV3File(value={"editor_info": editor_info_data}, format=kv3.FORMAT_GENERIC)
        encoded_single = kv3.textwriter.encode(single_kv3, options=options).strip()
        if encoded_single.startswith('{') and encoded_single.endswith('}'):
            inner = encoded_single[1:-1].strip()
            lines.append(f"\t{inner}")

    # 3. Soundevents
    for key, value in events_data.items():
        if key == "editor_info":
            continue

        comment = event_comments.get(key)
        if comment:
            lines.append("")
            for comment_line in comment.splitlines():
                line_str = comment_line.strip()
                if line_str:
                    lines.append(f"\t{line_str}")
                else:
                    lines.append("")

        single_kv3 = kv3.KV3File(value={key: value}, format=kv3.FORMAT_GENERIC)
        encoded_single = kv3.textwriter.encode(single_kv3, options=options).strip()
        if encoded_single.startswith('{') and encoded_single.endswith('}'):
            inner = encoded_single[1:-1].strip()
            lines.append(f"\t{inner}")

    # 4. File footer comments
    if file_footer_comments:
        lines.append("")
        for comment_line in file_footer_comments.splitlines():
            line_str = comment_line.strip()
            if line_str:
                lines.append(f"\t{line_str}")
            else:
                lines.append("")
        lines.append("")

    lines.append('}')
    lines.append('')
    return "\n".join(lines)

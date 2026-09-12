"""Access to the packaged agent guide topics.

Deep Source 2 knowledge is expensive to carry in a context window and cheap to
fetch on demand, so it lives here rather than in the server instructions.
"""

from __future__ import annotations

import importlib.resources
from typing import Any

# Order is the order they are listed in; summaries are what an agent reads to
# decide whether a topic is worth fetching, so they stay one line each.
TOPICS: dict[str, str] = {
    "vsmart-authoring": "Element, modifier, and filter vocabulary; the shape of a working linear kit.",
    "vsmart-creating": "Building a new SmartProp from scratch: skeleton, scatter, linear kit, and grid recipes.",
    "vsmart-expressions": "Intrinsics, the NaN cascade that makes props vanish, guard patterns, typed defaults.",
    "vsmart-ui": "Categories, hide and read-only expressions, dynamic model slots, viewport sizers.",
    "vsmart-enums": "Hammer dropdown label to KV3 enum value, including 'Scale last' = SCALE_END_TO_FIT.",
    "vmap-reading": "Map entities by class, brush meshes, and SmartProp placements with their variable overrides.",
    "vmap-authoring": "Why hand-written CMapMesh crashes, the prop_static blockout that does not, and what writing supports.",
    "addon-maintenance": "Dependencies, orphans, validation, renaming, compile order, and core_status.",
    "official-assets": "Searching and extracting stock Valve content from the CS2 VPK archive.",
    "particles-and-porting": "vsnap point clouds and the read-only Unreal inspection tools.",
    "gamedata-vdata": "KeyValues3 gamedata tables: reading entries, writing them, and the schema type.",
    "compile-verify": "Using resourcecompiler as the test harness and reading what it reports.",
    "material-texture": "vmat, vtex, and vmdl conventions, colour spaces, and asset renaming.",
}


def guide(topic: str | None = None) -> dict[str, Any]:
    """Return one guide topic, or the index when no topic is named."""
    if not topic:
        return {
            "topics": [{"topic": name, "summary": summary} for name, summary in TOPICS.items()],
            "usage": "Call again with topic=<name> for the full text.",
        }
    if topic not in TOPICS:
        raise ValueError(f"Unknown guide topic '{topic}'. Available: {', '.join(TOPICS)}")
    text = importlib.resources.files("automation.guides").joinpath(f"{topic}.md").read_text(encoding="utf-8")
    return {"topic": topic, "summary": TOPICS[topic], "content": text.strip()}

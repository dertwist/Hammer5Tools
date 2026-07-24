"""Auto-generate a commit message from `git status --porcelain` output.

One file -> "Edit <name>". One content folder -> "Update <folder>".
Several folders -> "Update a, b, c". Nothing recognizable -> "Update files".
"""
import os


def _changed_paths(porcelain):
    """Yield paths from porcelain lines, handling renames (`old -> new`)."""
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        yield path.strip().strip('"')


def generate(porcelain):
    paths = list(_changed_paths(porcelain))
    if not paths:
        return "Update files"
    if len(paths) == 1:
        return f"Edit {os.path.basename(paths[0])}"

    # Group by first path segment (materials, models, maps, sounds, ...).
    groups = []
    for p in paths:
        seg = p.replace("\\", "/").split("/", 1)[0]
        if seg not in groups:
            groups.append(seg)
    if len(groups) == 1:
        return f"Update {groups[0]}"
    shown = groups[:3]
    msg = "Update " + ", ".join(shown)
    if len(groups) > 3:
        msg += f", +{len(groups) - 3} more"
    return msg


def _demo():
    assert generate("") == "Update files"
    assert generate(" M materials/foo.vmat") == "Edit foo.vmat"
    assert generate("R  a/old.vmat -> materials/new.vmat") == "Edit new.vmat"
    assert generate(" M materials/a.vmat\n M materials/b.vmat") == "Update materials"
    assert generate(" M materials/a.vmat\n M models/b.vmdl") == "Update materials, models"
    assert generate(
        " M materials/a\n M models/b\n M maps/c\n M sounds/d"
    ) == "Update materials, models, maps, +1 more"
    print("commit_msg self-check OK")


if __name__ == "__main__":
    _demo()

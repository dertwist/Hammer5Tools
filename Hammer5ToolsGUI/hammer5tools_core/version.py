"""Application version loaded from the repository release manifest."""

import json
from pathlib import Path

from hammer5tools_core.runtime_paths import resolve_runtime_paths


def _version_manifest() -> Path:
    runtime_paths = resolve_runtime_paths()
    candidates = (
        runtime_paths.runtime_resource("version.json"),
        runtime_paths.install_root / "version.json",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def read_version() -> str:
    """Return the application version from the root version manifest."""
    manifest = _version_manifest()
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unable to read application version from {manifest}") from exc
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Invalid application version in {manifest}")
    return value


APP_VERSION = read_version()

import json
import re
from pathlib import Path

import myjob_server


ROOT = Path(__file__).parents[1]
VERSION_PATTERN = re.compile(r"^(?:[0-9]|[1-9][0-9])\.(?:[0-9]|[1-9][0-9])\.(?:[0-9]|[1-9][0-9])$")


def test_release_version_uses_three_segments_with_each_at_most_99():
    release = (ROOT / "VERSION").read_text(encoding="utf-8").strip().removeprefix("V")
    assert VERSION_PATTERN.fullmatch(release)
    assert all(0 <= int(segment) <= 99 for segment in release.split("."))


def test_release_version_is_consistent_across_runtime_surfaces():
    release = (ROOT / "VERSION").read_text(encoding="utf-8").strip().removeprefix("V")
    manifest = json.loads((ROOT / "browser_extension/manifest.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "resume_ui/package.json").read_text(encoding="utf-8"))
    cli_schema = json.loads((ROOT / "MyJob_cli/schema.json").read_text(encoding="utf-8"))
    assert release == "0.0.12"
    assert manifest["version"] == release
    assert package["version"] == release
    assert cli_schema["version"] == release
    assert myjob_server.VERSION == f"V{release}"

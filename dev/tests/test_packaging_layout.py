from pathlib import Path

from makefile import stage_three_root_bundle


def test_stages_pyinstaller_payload_under_application_root(tmp_path):
    output = tmp_path / "pyinstaller" / "Hammer5Tools_Core"
    runtime = output / "runtime"
    runtime.mkdir(parents=True)
    (output / "Hammer5Tools_Core.exe").write_bytes(b"exe")
    (runtime / "dependency.dll").write_bytes(b"dll")
    bundle = tmp_path / "bundle"

    stage_three_root_bundle(str(output), str(bundle))

    assert (bundle / "app" / "Hammer5Tools_Core.exe").read_bytes() == b"exe"
    assert (bundle / "app" / "runtime" / "dependency.dll").read_bytes() == b"dll"
    assert not output.exists()

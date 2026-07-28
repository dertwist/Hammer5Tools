"""Channel selection + downgrade policy for the updater.

Run: python tests/test_update_channel.py
"""
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if 'velopack' not in sys.modules:  # not installed outside frozen builds
    stub = types.ModuleType('velopack')
    stub.UpdateOptions = type('UpdateOptions', (), {
        '__init__': lambda self, **kw: self.__dict__.update(kw)
    })
    stub.HttpSource = type('HttpSource', (), {
        '__init__': lambda self, url: setattr(self, 'url', url)
    })
    sys.modules['velopack'] = stub

import src.common as common  # noqa: E402
from src.common import get_channel, get_update_options, get_update_source  # noqa: E402


def _case(setting, build, expect_channel, expect_downgrade):
    """setting: value get_settings_bool returns for 'dev_channel' (None = never set -> default)."""
    def fake_bool(section, key, default=None):
        return default if setting is None else setting

    with patch('src.settings.common.get_settings_bool', fake_bool), \
         patch('src.common.get_build_channel', lambda: build):
        assert get_channel() == expect_channel, (setting, build, get_channel())
        opts = get_update_options()
        assert opts.ExplicitChannel == expect_channel
        assert bool(opts.AllowVersionDowngrade) is expect_downgrade, (setting, build)


def demo():
    # Opted in -> dev, and dev pre-releases sort below stable so downgrade must be allowed
    _case(True, 'stable', 'dev', True)
    _case(True, 'dev', 'dev', True)
    # Opted out -> stable in both directions; leaving a dev build is itself a downgrade
    _case(False, 'dev', 'stable', True)
    _case(False, 'stable', 'stable', False)
    # Never touched -> follow the build's own channel
    _case(None, 'dev', 'dev', True)
    _case(None, 'stable', 'stable', False)

    # Velopack host-sniffs a bare string, so any github.com URL becomes a GitHub
    # API source. The dev feed is an asset directory, not a repo -> must be an
    # explicit HttpSource or the dev channel silently never finds updates.
    with patch('src.common.get_channel', lambda: 'dev'):
        assert isinstance(get_update_source(), sys.modules['velopack'].HttpSource)
    with patch('src.common.get_channel', lambda: 'stable'):
        assert get_update_source() == 'https://github.com/dertwist/Hammer5Tools'

    # CI writes version.txt with a BOM (PowerShell Out-File -Encoding utf8) and
    # the packed dev version on line 1; both must survive the read.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        exe = Path(d) / 'Hammer5Tools.exe'
        (Path(d) / 'version.txt').write_bytes('5.5.0-dev.226\ndev\n'.encode('utf-8-sig'))
        with patch.object(sys, 'executable', str(exe)), \
             patch.object(sys, 'frozen', True, create=True):
            assert common._version_txt() == ['5.5.0-dev.226', 'dev'], common._version_txt()
            assert common.get_build_channel() == 'dev'

    print("ok")


if __name__ == '__main__':
    demo()

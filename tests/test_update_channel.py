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
    sys.modules['velopack'] = stub

from src.common import get_channel, get_update_options  # noqa: E402


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
    print("ok")


if __name__ == '__main__':
    demo()

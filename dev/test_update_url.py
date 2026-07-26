import sys
import os
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import src.common as common


def _head(url):
    req = urllib.request.Request(url, method='HEAD',
                                 headers={'User-Agent': 'Hammer5Tools-Updater'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status


def test_update_url():
    original = common.get_channel
    try:
        common.get_channel = lambda: 'dev'
        dev = common.get_update_url()
        common.get_channel = lambda: 'stable'
        stable = common.get_update_url()
    finally:
        common.get_channel = original

    assert stable == 'https://github.com/dertwist/Hammer5Tools', stable
    # The dev release is a GitHub pre-release, which Velopack's GitHub source
    # skips, so dev must use the tag's asset directory as a plain HTTP feed.
    assert dev != stable, 'dev channel must not use the GitHub API source'
    assert _head(f'{dev}/releases.dev.json') == 200, 'dev feed missing'


if __name__ == '__main__':
    test_update_url()
    print('ok')

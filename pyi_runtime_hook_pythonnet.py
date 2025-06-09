
import sys, os, tempfile
# Fix for pycparser needing writable parser tables
if hasattr(sys, '_MEIPASS'):
    import shutil
    import pycparser
    import pycparser.ply
    tempdir = tempfile.gettempdir()
    for tabfile in ['lextab.py', 'yacctab.py']:
        src = os.path.join(sys._MEIPASS, 'pycparser', tabfile)
        dst = os.path.join(tempdir, tabfile)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
    sys.path.insert(0, tempdir)

import sys, os, tempfile, shutil
# Copy pre-bundled pycparser parser tables to a writable tempdir so pycparser
# can import them. Only runs when the app is frozen by PyInstaller.
if hasattr(sys, '_MEIPASS'):
    tempdir = tempfile.gettempdir()
    for tabfile in ['lextab.py', 'yacctab.py']:
        src = os.path.join(sys._MEIPASS, 'pycparser', tabfile)
        dst = os.path.join(tempdir, tabfile)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass
    sys.path.insert(0, tempdir)

"""Detail prop editor.

No re-export here on purpose: importing the package would then construct the
widget module, and Qt with it, which stops the schema and the document rules
from being imported (or tested) without a GUI. Import from the module you
want -- `from .main import DetailPropEditorWidget`.
"""

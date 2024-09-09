from PySide6 import QtWidgets
import sys
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global

app = QtWidgets.QApplication(sys.argv)
dialog = QtWidgets.QColorDialog()

grid = dialog.findChild(QtWidgets.QGridLayout)
names = iter(('hue', 'sat', 'val', 'red', 'green', 'blue', 'alpha'))
for i in range(grid.count()):
    item = grid.itemAt(i)
    widget = item.widget()
    if isinstance(widget, QtWidgets.QSpinBox):
        widget.setObjectName(next(names))

buttonBox = dialog.findChild(QtWidgets.QDialogButtonBox)
buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setObjectName('ok')
buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setObjectName('cancel')

dialog.setStyleSheet(QT_Stylesheet_global)

dialog.show()
sys.exit(app.exec_())
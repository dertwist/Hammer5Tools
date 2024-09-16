import ast
import re
from smartprop_editor.properties_classes.ui_color import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter, QColorDialog
from PySide6.QtCore import Signal
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global


class PropertyColor(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.color = [255, 255, 255]
        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText('Variable name, RGB or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        if isinstance(value, dict):
            if value['m_Expression']:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(self.var_value)
                self.color = [255, 255, 255]
            elif value['m_SourceName']:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.color = [255, 255 ,255]
                self.text_line.setPlainText(self.var_value)
            else:
                print('Could not parse given input data')
                self.color = [255, 255, 255]
        elif isinstance(value, list):
            self.ui.logic_switch.setCurrentIndex(1)
            self.color = value
        else:
            self.ui.logic_switch.setCurrentIndex(0)
            self.color = [255, 255 ,255]

        self.ui.value.clicked.connect(self.open_dialog)

        self.on_changed()
    def open_dialog(self):
        color = self.dialog.getColor().getRgb()[:3]
        self.ui.value.setStyleSheet(f"""background-color: rgb{color};
            padding:4px;
            border:0px;
            border: 2px solid translucent;
            border-color: rgba(80, 80, 80, 100);
            """)
        print("RGB Color:", color)
        self.color = list(color)
        self.on_changed()


    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.hide()
            self.ui.value.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
        else:
            self.text_line.show()
            self.ui.value.hide()

    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.ui.value.setStyleSheet(f"""background-color: rgb{tuple(self.color)};
            padding:4px;
            border:0px;
            border: 2px solid translucent;
            border-color: rgba(80, 80, 80, 100);
            """)
        self.edited.emit()
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            self.value = {self.value_class: self.color}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': value}}
        # Expression
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_Expression': value}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

import ast

from smartprop_editor.properties_classes.ui_vector3d import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal


class PropertyVector3D(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        self.ui.property_class.setText(self.value_class)
        self.ui.logic_switch.currentTextChanged.connect(self.logic_switch)

        # Variable
        self.text_line = CompletingPlainTextEdit()
        self.text_line.setPlaceholderText('Variable name')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        # Vector X
        self.text_line_x = CompletingPlainTextEdit()
        self.ui.layout_x.insertWidget(1, self.text_line_x)
        self.text_line_x.textChanged.connect(self.on_changed)  # Connect on_changed method

        # Vector Y
        self.text_line_y = CompletingPlainTextEdit()
        self.ui.layout_y.insertWidget(1, self.text_line_y)
        self.text_line_y.textChanged.connect(self.on_changed)  # Connect on_changed method

        # Vector Z
        self.text_line_z = CompletingPlainTextEdit()
        self.ui.layout_z.insertWidget(1, self.text_line_z)
        self.text_line_z.textChanged.connect(self.on_changed)

        if value['m_Components']:
            self.ui.logic_switch.setCurrentIndex(1)
            def add_value(layout, value):
                if isinstance(value, dict):
                    if 'm_Expression' in value:
                        layout.setPlainText(str(value['m_Expression']))
                    elif 'm_SourceName' in value:
                        pass
                    else:
                        pass
                elif isinstance(value, int) or  isinstance(value, float):
                    layout.setPlainText(str(value))

            add_value(self.text_line_x, value['m_Components'][0])
            add_value(self.text_line_y, value['m_Components'][1])
            add_value(self.text_line_z, value['m_Components'][2])
            # self.text_line_x.setPlainText(str(value['m_Components'][0]))
            # self.text_line_y.setPlainText(str(value['m_Components'][1]))
            # self.text_line_z.setPlainText(str(value['m_Components'][2]))
        elif value['m_SourceName']:
            self.ui.logic_switch.setCurrentIndex(0)
            self.var_value = value['m_SourceName']
            self.text_line.setPlainText(self.var_value)
        else:
            print('Could not parse given input data')
            self.value = {'m_Components': [{'m_Expression': '0'}, {'m_Expression': '0'}, {'m_Expression': '0'}]}



        self.logic_switch()

        self.change_value()




    def logic_switch(self):
        widget = self.ui.layout.itemAt(2).widget()
        if self.ui.logic_switch.currentText() == 'Variable source':
            self.ui.frame_4.setMaximumHeight(0)
            widget.setEnabled(True)
        else:
            self.ui.frame_4.setMaximumHeight(1600)
            if isinstance(widget, CompletingPlainTextEdit):
                widget.setEnabled(False)

    def on_changed(self):
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.text_line_x.completions.setStringList(variables)
        self.text_line_y.completions.setStringList(variables)
        self.text_line_z.completions.setStringList(variables)

        self.change_value()
        self.edited.emit()
    def change_value(self):
        if self.ui.logic_switch.currentIndex() == 0:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': value}}
        elif self.ui.logic_switch.currentIndex() == 1:
            value_x = self.text_line_x.toPlainText()
            value_y = self.text_line_y.toPlainText()
            value_z = self.text_line_z.toPlainText()
            try:
                value_x = ast.literal_eval(value_x)
            except:
                pass
            try:
                value_y = ast.literal_eval(value_y)
            except:
                pass
            try:
                value_z = ast.literal_eval(value_z)
            except:
                pass
            self.value = {self.value_class: {'m_Components': [{'m_Expression': value_x}, {'m_Expression': value_y}, {'m_Expression': value_z}]}}
            print(self.value)

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

import ast
import re

from smartprop_editor.properties_classes.ui_vector3d import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal
from smartprop_editor.objects import expression_completer


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

        output = re.sub(r'm_fl|m_n|m_v|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentIndexChanged.connect(self.on_changed)

        # Variable
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText('Variable name')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        # Vector X
        self.text_line_x = CompletingPlainTextEdit()
        self.ui.layout_x.insertWidget(2, self.text_line_x)
        self.text_line_x.textChanged.connect(self.on_changed)
        self.ui.comboBox_x.currentIndexChanged.connect(self.on_changed)

        # Vector Y
        self.text_line_y = CompletingPlainTextEdit()
        self.ui.layout_y.insertWidget(2, self.text_line_y)
        self.text_line_y.textChanged.connect(self.on_changed)
        self.ui.comboBox_y.currentIndexChanged.connect(self.on_changed)

        # Vector Z
        self.text_line_z = CompletingPlainTextEdit()
        self.ui.layout_z.insertWidget(2, self.text_line_z)
        self.text_line_z.textChanged.connect(self.on_changed)
        self.ui.comboBox_z.currentIndexChanged.connect(self.on_changed)

        self.value = None
        self.ui.logic_switch.setCurrentIndex(0)

        if isinstance(value, dict):
            if  'm_Components' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                def add_value(layout, value, combo):
                    if isinstance(value, dict):
                        if 'm_Expression' in value:
                            layout.setPlainText(str(value['m_Expression']))
                            combo.setCurrentIndex(2)
                        if 'm_SourceName' in value:
                            layout.setPlainText(str(value['m_SourceName']))
                            combo.setCurrentIndex(1)
                    elif isinstance(value, int) or isinstance(value, float):
                        layout.setPlainText(str(value))
                        combo.setCurrentIndex(0)
                    else:
                        layout.setPlainText(str(value))
                        combo.setCurrentIndex(0)

                add_value(self.text_line_x, value['m_Components'][0], self.ui.comboBox_x)
                add_value(self.text_line_y, value['m_Components'][1], self.ui.comboBox_y)
                add_value(self.text_line_z, value['m_Components'][2], self.ui.comboBox_z)
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(1)
                self.var_value = value['m_SourceName']
                self.text_line.setPlainText(self.var_value)
            else:
                pass



        self.on_changed()



    def logic_switch_line(self):
        if self.ui.comboBox_x.currentIndex() == 0:
            self.text_line_x.OnlyFloat = True
        else:
            self.text_line_x.OnlyFloat = False

        if self.ui.comboBox_y.currentIndex() == 0:
            self.text_line_y.OnlyFloat = True
        else:
            self.text_line_y.OnlyFloat = False

        if self.ui.comboBox_z.currentIndex() == 0:
            self.text_line_z.OnlyFloat = True
        else:
            self.text_line_z.OnlyFloat = False
    def logic_switch(self):
        widget = self.ui.layout.itemAt(2).widget()
        if self.ui.logic_switch.currentIndex() == 0:
            self.ui.frame_4.setMaximumHeight(0)
            widget.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.ui.frame_4.setMaximumHeight(0)
            widget.show()
        else:
            self.ui.frame_4.setMaximumHeight(1600)
            if isinstance(widget, CompletingPlainTextEdit):
                widget.hide()

    def on_changed(self):
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables + expression_completer)
        self.text_line_x.completions.setStringList(variables + expression_completer)
        self.text_line_y.completions.setStringList(variables + expression_completer)
        self.text_line_z.completions.setStringList(variables + expression_completer)
        self.logic_switch_line()
        self.logic_switch()

        self.change_value()
        self.edited.emit()
    def change_value(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        elif self.ui.logic_switch.currentIndex() == 1:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': value}}
        elif self.ui.logic_switch.currentIndex() == 2:
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
            def handle_value(value, combo_box):
                index = combo_box.currentIndex()
                if index == 0:
                    pass
                elif index == 1:
                    value = {'m_SourceName': value}
                elif index == 2:
                    value = {'m_Expression': str(value)}
                return value

            # Update values
            value_x = handle_value(value_x, self.ui.comboBox_x)
            value_y = handle_value(value_y, self.ui.comboBox_y)
            value_z = handle_value(value_z, self.ui.comboBox_z)
            self.value = {self.value_class: {'m_Components': [value_x, value_y, value_z]}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

import ast
import re
from smartprop_editor.properties_classes.ui_float import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal
from smartprop_editor.objects import expression_completer


class PropertyFloat(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, int_bool=False,slider_range=[-99,99]):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.int_bool = int_bool
        self.variables_scrollArea = variables_scrollArea

        if self.int_bool:
            self.ui.logic_switch.setItemText(1, 'Int')
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;
            
            color: rgb(108, 135, 255);
                        """)
        else:
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;

            color: rgb(181, 255, 239);
                        """)


        output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('0')


        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(str(self.var_value))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.text_line.setPlainText(str(self.var_value))
        elif isinstance(value, float) or isinstance(value, int):
            self.ui.logic_switch.setCurrentIndex(1)
            self.ui.SpinBox.setValue(value)
            self.on_SpinBox_updated()
            # self.text_line.setPlainText(str(value))

        # Float widget setup
        self.ui.Slider.valueChanged.connect(self.on_Slider_updated)
        self.ui.SpinBox.valueChanged.connect(self.on_SpinBox_updated)
        self.ui.Slider.setMinimum(slider_range[0]*100)
        self.ui.Slider.setMaximum(slider_range[1]*100)
        self.on_changed()


    # Float Widget
    def on_SpinBox_updated(self):
        value = self.ui.SpinBox.value()
        self.ui.Slider.setValue(value*100)
        self.on_changed()
    def on_Slider_updated(self):
        value = self.ui.Slider.value()
        self.ui.SpinBox.setValue(value/100)
        self.on_changed()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.OnlyFloat = False
            self.text_line.hide()
            self.ui.float_widget.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.float_widget.show()
        else:
            self.text_line.OnlyFloat = False
            self.text_line.show()
            self.ui.float_widget.hide()

    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables + expression_completer)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = {self.value_class: None}
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            value = self.ui.SpinBox.value()
            if self.int_bool:
                self.value = {self.value_class: round(float(value))}
            else:
                self.value = {self.value_class: float(value)}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': str(value)}}
        # Expression
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_Expression': str(value)}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

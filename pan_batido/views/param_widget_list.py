from qgis.PyQt import QtWidgets

from .param_widget import ParamWidget


class ParamWidgetList(QtWidgets.QWidget):
    def __init__(self, params, parent=None):
        super(ParamWidgetList, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.param_widgets = []

        for k, v in params.items():
            param_widget = ParamWidget(k, **v)
            self.param_widgets.append(param_widget)
            self.layout.addWidget(param_widget)

        self.setLayout(self.layout)

    def set_range(self, params):
        for prm, wdg in zip(params, self.param_widgets):
            wdg.spinbox.setRange(prm["min"], prm["max"])
            wdg.slider.setRange(prm["min"], prm["max"])

    def set_values(self, params):
        for prm, wdg in zip(params, self.param_widgets):
            wdg.spinbox.setValue(prm["value"])
            wdg.slider.setValue(prm["value"])

    def get_values(self):
        return [param_widget.spinbox.value() for param_widget in self.param_widgets]

    def get_range(self):
        return [
            {"min": param_widget.spinbox.minimum(), "max": param_widget.spinbox.maximum()}
            for param_widget in self.param_widgets
        ]

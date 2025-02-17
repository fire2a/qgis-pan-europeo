from qgis.PyQt import QtCore, QtWidgets


class ParamWidget(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, label_text="", min=0, max=100, value=50, parent=None):
        super(ParamWidget, self).__init__(parent)

        self.layout = QtWidgets.QHBoxLayout(self)

        self.label = QtWidgets.QLabel(label_text)
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setRange(min, max)
        self.spinbox.setValue(value)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(min, max)
        self.slider.setValue(value)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.spinbox)
        self.layout.addWidget(self.slider)

        self.slider.valueChanged.connect(self.spinbox.setValue)
        self.spinbox.valueChanged.connect(self.slider.setValue)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)

        self.setLayout(self.layout)

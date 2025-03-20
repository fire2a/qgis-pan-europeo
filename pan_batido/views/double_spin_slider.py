#!python
"""
thanks to bfris
https://stackoverflow.com/users/9705687/bfris
https://stackoverflow.com/a/50300848
"""
from math import ceil, floor

from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.QtCore import QSize, Qt


class DoubleSpinSlider(QtWidgets.QWidget):
    valueChanged = QtCore.pyqtSignal(float)
    editingFinished = QtCore.pyqtSignal()

    def __init__(self, orientation=QtCore.Qt.Horizontal, decimals=3, parent=None, *args, **kargs):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QtWidgets.QLabel(self)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.spinbox = QtWidgets.QDoubleSpinBox(self)
        self.slider = QtWidgets.QSlider(orientation, self)
        self._multi = 10**decimals

        if orientation == Qt.Horizontal:
            layout = QtWidgets.QHBoxLayout(self)
        elif orientation == Qt.Vertical:
            layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.spinbox)
        layout.addWidget(self.slider)
        self.setLayout(layout)

        self.spinbox.valueChanged.connect(self.on_spinbox_value_changed)
        self.spinbox.editingFinished.connect(self.on_editing_finished)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
        self.slider.sliderReleased.connect(self.on_slider_released)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Set stylesheets
        # self.setStyleSheet(
        #     """
        #     QDoubleSpinBox {
        #         background: transparent;
        #     }
        #     QSlider {
        #         background: transparent;
        #     }
        #     QLabel {
        #         background: transparent;
        #     }
        # """
        # )
        # self.setStyleSheet(
        #     """
        #     QDoubleSpinBox {
        #         background: transparent;
        #         border: none;
        #         color: black;
        #     }
        #     QSlider::groove:horizontal {
        #         border: 1px solid #999999;
        #         height: 8px;
        #         background: white;
        #         margin: 2px 0;
        #     }
        #     QSlider::handle:horizontal {
        #         background: #b4b4b4;
        #         border: 1px solid #5c5c5c;
        #         width: 18px;
        #         margin: -2px 0;
        #         border-radius: 3px;
        #     }
        # """
        # )

    def sizeHint(self):
        return QSize(200, 40)

    @QtCore.pyqtSlot(float)
    def on_spinbox_value_changed(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(int(value * self._multi))
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)

    @QtCore.pyqtSlot(int)
    def on_slider_value_changed(self, value):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value / self._multi)
        self.spinbox.blockSignals(False)
        self.valueChanged.emit(value / self._multi)

    def on_editing_finished(self):
        self.editingFinished.emit()

    def on_slider_released(self):
        self.editingFinished.emit()

    def value(self):
        return self.spinbox.value()

    def setMinimum(self, value):
        self.slider.setMinimum(ceil(value * self._multi))
        self.spinbox.setMinimum(value)

    def setMaximum(self, value):
        self.slider.setMaximum(floor(value * self._multi))
        self.spinbox.setMaximum(value)

    def setSingleStep(self, value):
        self.slider.setSingleStep(int(value * self._multi))
        self.spinbox.setSingleStep(value)

    def singleStep(self):
        # return float(super().singleStep()) / self._multi
        return self.spinbox.singleStep()

    def setValue(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(int(value * self._multi))
        self.slider.blockSignals(False)
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(value)
        self.spinbox.blockSignals(False)

    def minimum(self):
        return self.spinbox.minimum()

    def maximum(self):
        return self.spinbox.maximum()

    def setRange(self, minimum, maximum):
        self.setMinimum(minimum)
        self.setMaximum(maximum)

    def set3(self, min_, val, max_):
        self.setMinimum(min_)
        self.setMaximum(max_)
        self.setValue(val)

    def get3(self):
        return self.minimum(), self.value(), self.maximum()

    def setText(self, text):
        self.label.setText(text)

    def text(self):
        return self.label.text()

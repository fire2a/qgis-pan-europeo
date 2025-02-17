#!python
"""
thanks to bfris
https://stackoverflow.com/users/9705687/bfris
https://stackoverflow.com/a/50300848
"""
from qgis.PyQt import QtCore, QtWidgets


class DoubleSlider(QtWidgets.QSlider):

    # create our own signal that we can connect to if necessary
    doubleValueChanged = QtCore.pyqtSignal(float)

    def __init__(self, orientation=QtCore.Qt.Horizontal, decimals=3, parent=None, *args, **kargs):
        super().__init__(orientation, parent, *args, **kargs)
        self._multi = 10**decimals

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super().value()) / self._multi
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super().value()) / self._multi

    def setMinimum(self, value):
        return super().setMinimum(value * self._multi)

    def setMaximum(self, value):
        return super().setMaximum(value * self._multi)

    def setSingleStep(self, value):
        return super().setSingleStep(value * self._multi)

    def singleStep(self):
        return float(super().singleStep()) / self._multi

    def setValue(self, value):
        super().setValue(int(value * self._multi))

    def setRange(self, min_value, max_value):
        self.setMinimum(min_value)
        self.setMaximum(max_value)

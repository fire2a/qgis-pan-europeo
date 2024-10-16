#!python3
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MarraquetaDialog
                                 A QGIS plugin
 Ponders different rasters with different utility functions
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-05-14
        git sha              : $Format:%H$
        copyright            : (C) 2024 by fdobad@github
        email                : fbadilla@ing.uchile.cl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from functools import partial

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog,
                                 QDialogButtonBox, QGridLayout, QGroupBox,
                                 QHBoxLayout, QLabel, QSizePolicy, QSlider,
                                 QSpacerItem, QSpinBox, QVBoxLayout, QWidget)
from qgis.utils import iface

from .config import DATATYPES, GRIORAS, qprint


class MarraquetaDialog(QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(MarraquetaDialog, self).__init__(parent)
        qprint("MarraquetaDialog.__init__")
        # set window title to Pan Europeo
        self.setWindowTitle("Pan Europeo Baguette Marraqueta Coliza Hallulla")
        self.verticalLayout = QVBoxLayout()
        self.setLayout(self.verticalLayout)

        # each row is a name | weight | resample | utility function
        self.input_groupbox = QGroupBox("Input rasters")
        self.grid = QGridLayout()
        self.grid.addWidget(QLabel("name"), 0, 0)
        self.grid.addWidget(QLabel("weight"), 0, 1)
        self.grid.addWidget(QLabel("resample/interpolation algo."), 0, 2)
        self.grid.addWidget(QLabel("utility func."), 0, 3)

        # for each layer a row of controls
        self.rows = []
        for i, layer in enumerate(iface.mapCanvas().layers()):
            if layer.publicSource() == "":
                qprint(
                    f"layer {layer.name()} has no public source, skipping (is it written locally?)", level=Qgis.Warning
                )
            # name
            self.grid.addWidget(QLabel(layer.name()), i + 1, 0)
            # weight
            weight_layout = QHBoxLayout()
            checkbox = QCheckBox()
            spinbox = QSpinBox()
            slider = QSlider(Qt.Orientation.Horizontal)
            link_spinbox_slider(spinbox, slider)
            spinbox.setValue(1)
            weight_layout.addWidget(checkbox)
            weight_layout.addWidget(spinbox)
            weight_layout.addWidget(slider)
            self.grid.addLayout(weight_layout, i + 1, 1)
            # resample
            resample_dropdown = QComboBox()
            # NO REORDER:
            resample_dropdown.addItems(list(GRIORAS.keys()))
            resample_dropdown.row_id = i
            self.grid.addWidget(resample_dropdown, i + 1, 2)
            # utility function
            ufunc_layout = QHBoxLayout()
            ufunc_dropdown = QComboBox()
            # NO REORDER:
            ufunc_dropdown.addItems(
                ["min-max", "max-min", "bi-piecewise-linear values", "bi-piecewise-linear percentage"]
            )
            # signal for hiding/showing each parameters
            ufunc_dropdown.currentIndexChanged.connect(self.function_change)
            # add id to the dropdown
            ufunc_dropdown.row_id = i
            ufunc_layout.addWidget(ufunc_dropdown)
            # minmax parameters
            lbl1 = QLabel("")
            lbl1.func_id = 0
            lbl1.row_id = i
            ufunc_layout.addWidget(lbl1)
            # maxmin parameters
            lbl2 = QLabel("")
            lbl2.func_id = 1
            lbl2.row_id = i
            ufunc_layout.addWidget(lbl2)

            # piecewise-linear parameters
            # a
            a_spinbox = QSpinBox()
            a_slider = QSlider(Qt.Orientation.Horizontal)
            link_spinbox_slider(a_slider, a_spinbox)
            # b
            b_spinbox = QSpinBox()
            b_slider = QSlider(Qt.Orientation.Horizontal)
            link_spinbox_slider(b_slider, b_spinbox)
            for elto in [a_spinbox, a_slider, b_spinbox, b_slider]:
                elto.row_id = i
                elto.func_id = 2
                elto.setVisible(False)
                ufunc_layout.addWidget(elto)

            # piecewise-linear parameters
            # c
            c_spinbox = QSpinBox()
            c_slider = QSlider(Qt.Orientation.Horizontal)
            link_spinbox_slider(c_slider, c_spinbox)
            # d
            d_spinbox = QSpinBox()
            d_slider = QSlider(Qt.Orientation.Horizontal)
            link_spinbox_slider(d_slider, d_spinbox)
            for elto in [c_spinbox, c_slider, d_spinbox, d_slider]:
                elto.row_id = i
                elto.func_id = 3
                elto.setVisible(False)
                ufunc_layout.addWidget(elto)

            checkbox.setChecked(True)
            checkbox.stateChanged.connect(
                partial(
                    set_enabled,
                    spinbox,
                    slider,
                    resample_dropdown,
                    ufunc_dropdown,
                    a_spinbox,
                    a_slider,
                    b_spinbox,
                    b_slider,
                    c_spinbox,
                    c_slider,
                    d_spinbox,
                    d_slider,
                )
            )

            self.grid.addLayout(ufunc_layout, i + 1, 3)
            self.rows += [
                {
                    "i": len(self.rows),
                    "layer_id": layer.id(),
                    "weight_checkbox": checkbox,
                    "weight_spinbox": spinbox,
                    "weight_slider": slider,
                    "resample_dropdown": resample_dropdown,
                    "ufunc_dropdown": ufunc_dropdown,
                    "a_spinbox": a_spinbox,
                    "a_slider": a_slider,
                    "b_spinbox": b_spinbox,
                    "b_slider": b_slider,
                    "c_spinbox": c_spinbox,
                    "c_slider": c_slider,
                    "d_spinbox": d_spinbox,
                    "d_slider": d_slider,
                }
            ]
        self.input_groupbox.setLayout(self.grid)
        self.verticalLayout.addWidget(self.input_groupbox)

        self.verticalLayout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # target resolution x,y; pixel size, data type
        self.target_groupbox = QGroupBox("Output configuration")
        self.target_layout = QGridLayout()
        self.target_layout.addWidget(QLabel("width [px]:"), 0, 0)
        self.resolution_x = QSpinBox()
        self.resolution_x.setRange(1, 2147483647)
        self.resolution_x.setValue(1920)
        self.target_layout.addWidget(self.resolution_x, 0, 1)
        self.target_layout.addWidget(QLabel("height [px]:"), 1, 0)
        self.resolution_y = QSpinBox()
        self.resolution_y.setRange(1, 2147483647)
        self.resolution_y.setValue(1080)
        self.target_layout.addWidget(self.resolution_y, 1, 1)
        self.target_layout.addWidget(QLabel("pixel size [m]:"), 0, 2)
        self.pixel_size = QSpinBox()
        self.pixel_size.setRange(1, 2147483647)
        self.pixel_size.setValue(100)
        self.target_layout.addWidget(self.pixel_size, 0, 3)
        self.target_layout.addWidget(QLabel("data type:"), 1, 2)
        self.data_type = QComboBox()
        self.data_type.addItems(list(DATATYPES.keys()))
        self.data_type.setCurrentIndex(2)
        self.target_layout.addWidget(self.data_type, 1, 3)
        self.target_groupbox.setLayout(self.target_layout)
        self.verticalLayout.addWidget(self.target_groupbox)

        # add a QtButtonBox to the bottom of the dialog with Ok, and Cancel
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Close | QDialogButtonBox.Reset,
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        for button in self.buttonBox.buttons():
            if button.text() == "Reset":
                button.clicked.connect(self.reset)

        hl = QHBoxLayout()
        label = QLabel()
        label.setText('<a href="https://fire2a.github.io/qgis-pan-europeo/">user manual</a>')
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignLeft)
        hl.addWidget(label)
        label = QLabel()
        label.setText('<a href="https://github.com/fire2a/qgis-pan-europeo/issues">issues</a>')
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignRight)
        hl.addWidget(label)
        self.verticalLayout.addLayout(hl)

        self.verticalLayout.addWidget(self.buttonBox)
        # self.setupUi(self)

    def reject(self):
        self.destroy()

    def reset(self):
        self.destroy()
        self = self.__init__()

    def rescale_weights(self):
        """all inputs should sum to 100"""
        accum_weight = 0
        for row in self.rows:
            checkbox, spinbox = row["weight_checkbox"], row["weight_spinbox"]
            if checkbox.isChecked():
                accum_weight += spinbox.value()
        if accum_weight != 100 and accum_weight != 0:
            for row in self.rows:
                spinbox = row["weight_spinbox"]
                spinbox.setValue(int(spinbox.value() * 100 / accum_weight))

    def function_change(self, idx):
        """make visible row a_spinbox, a_slider, b_spinbox, b_slider if index !=0"""
        # def function_change(self, *args, **kwargs):
        # QgsMessageLog.logMessage(f"{args=}, {kwargs=}", "Marraqueta")
        # args=(1,), kwargs={}
        # qprint(f"dropdown {idx=} {self.sender().row_id=}")
        # identify row
        row = self.rows[self.sender().row_id]
        # iterate over func_id elements
        for elto in row.values():
            if not isinstance(elto, QWidget):
                continue
            if hasattr(elto, "func_id"):
                if elto.func_id == idx:
                    elto.setVisible(True)
                else:
                    elto.setVisible(False)


def link_spinbox_slider(slider, spinbox):
    """Link a QSpinBox, QSlider"""
    spinbox.setRange(0, 100)
    slider.setRange(0, 100)

    def set_spinbox_value(value):
        spinbox.setValue(value)

    def set_slider_value(value):
        slider.setValue(value)

    spinbox.valueChanged.connect(set_slider_value)
    slider.valueChanged.connect(set_spinbox_value)


def set_enabled(*args):
    value = args[-1]
    for widget in args[:-1]:
        widget.setEnabled(value)

#!python3
"""
breakpoint()
from IPython import embed

https://fire2a.github.io/qgis-pan-europeo/

https://www.riverbankcomputing.com/static/Docs/PyQt5/
https://www.riverbankcomputing.com/static/Docs/PyQt5/search.html

https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtwidgets/qlayout.html
https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtwidgets/qabstractitemview.html

https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtwidgets/qtreewidget.html
https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtwidgets/qtreewidgetitem.html

https://www.riverbankcomputing.com/static/Docs/PyQt5/api/qtwidgets/qtreewidgetitemiterator.html
"""
import sys

import numpy as np
from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtGui import QDrag
# from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QMainWindow,
                             QSlider, QSpinBox, QTreeWidget, QTreeWidgetItem,
                             QWidget)


class ComboBox(QComboBox):
    def __init__(self, parent=None, options=["op1", "op2"]):
        super().__init__(parent)
        if options:
            self.addItems(options)

    def clone(self):
        new = ComboBox(options=None)
        new.setEnabled(self.isEnabled())
        for index in range(self.count()):
            new.addItem(self.itemText(index))
        new.setCurrentIndex(self.currentIndex())
        return new


class SpinBoxSlider(QWidget):
    def __init__(self, value=50):
        super().__init__()
        self.spinBox = QSpinBox()
        self.slider = QSlider(Qt.Horizontal)
        self.spinBox.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self.spinBox.setValue)
        self.spinBox.setRange(0, 100)
        self.slider.setRange(0, 100)
        self.spinBox.setValue(value)
        layout = QHBoxLayout(self)
        layout.addWidget(self.spinBox)
        layout.addWidget(self.slider)

    def clone(self):
        new = SpinBoxSlider(self.spinBox.value())
        new.setEnabled(self.isEnabled())
        return new


class LinkedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.p0 = SpinBoxSlider(33)
        self.p1 = SpinBoxSlider(66)
        self.p2 = SpinBoxSlider(99)
        layout = QHBoxLayout(self)
        layout.addWidget(self.p0)
        layout.addWidget(self.p1)
        layout.addWidget(self.p2)

    def clone(self):
        new = LinkedWidget()
        new.p0.spinBox.setValue(self.p0.spinBox.value())
        new.p1.spinBox.setValue(self.p1.spinBox.value())
        new.p2.spinBox.setValue(self.p2.spinBox.value())
        new.p0.setVisible(self.p0.isVisible())
        new.p1.setVisible(self.p1.isVisible())
        new.p2.setVisible(self.p2.isVisible())
        new.setEnabled(self.isEnabled())
        return new

    def set_active(self, idx):
        match idx:
            case 0:
                self.p0.setVisible(True)
                self.p1.setVisible(False)
                self.p2.setVisible(False)
            case 1:
                self.p0.setVisible(False)
                self.p1.setVisible(True)
                self.p2.setVisible(True)


class TreeWidget(QTreeWidget):
    def __init__(self, instance, column_count=3, header_labels=["Name", "Weight", "Option"]):
        super().__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.instance = instance
        self.setColumnCount(column_count)
        self.setHeaderLabels(header_labels)

        for pkey, pdic in instance.items():
            pdic["item"].setText(0, pkey)
            pdic["item"].setCheckState(0, Qt.Checked)
            self.addTopLevelItem(pdic["item"])
            for i, wid in enumerate(pdic["widgets"]):
                self.setItemWidget(pdic["item"], i + 1, wid)
            for ckey, cdic in pdic["children"].items():
                cdic["item"].setText(0, ckey)
                cdic["item"].setCheckState(0, Qt.Checked)
                pdic["item"].addChild(cdic["item"])
                pdic["item"].setFlags(pdic["item"].flags() | Qt.ItemIsDragEnabled)
                for i, wid in enumerate(cdic["widgets"]):
                    self.setItemWidget(cdic["item"], i + 1, wid)
                # connect options combo with linked widget
                cdic["widgets"][1].currentIndexChanged.connect(cdic["widgets"][2].set_active)
                cdic["widgets"][2].set_active(0)

        self.itemChanged.connect(self.item_changed)
        self.expandAll()

    def item_changed(self, item):
        for i in range(self.columnCount() - 1):
            widget = self.itemWidget(item, i + 1)
            if widget:
                widget.setEnabled(item.checkState(0) == Qt.Checked)
        # item is top level
        if item.parent() is None:
            if item.checkState(0) == Qt.Checked:
                item.setExpanded(True)
            else:
                item.setExpanded(False)

        """
        # iterate over all rows in the tree
        for i in range(self.topLevelItemCount()):
            parent = self.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.Checked:
                    child.setExpanded(True)
                else:
                    child.setExpanded(False)
        """

    def startDrag(self, supportedActions):
        item = self.currentItem()
        mimeData = QMimeData()
        mimeData.setText(item.text(0))

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.exec_(supportedActions)

    def dragEnterEvent(self, event):
        # if source is parent, ignore
        source_item = self.currentItem()
        if source_item.parent() is None:
            event.ignore()
            return
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        source_item = self.currentItem()
        target_item = self.itemAt(event.pos())
        if target_item is None:
            event.ignore()
            return

        # get target item top level
        while target_item.parent():
            target_item = target_item.parent()

        # print(f"source_item {source_item.text(0)}")
        # print(f"target_item {target_item.text(0)}")

        widgets = [self.itemWidget(source_item, i + 1).clone() for i in range(self.columnCount() - 1)]
        widgets[1].currentIndexChanged.connect(widgets[2].set_active)

        source_parent = source_item.parent()
        if source_parent:
            # print("remove child from {source_parent.text(0)}")
            source_parent.removeChild(source_item)

        new_item = source_item.clone()
        target_item.addChild(new_item)

        # Reattach the widget to the source item
        for i, widget in enumerate(widgets):
            # print(f"Reattaching widget {widget=} {i} to {new_item.text(0)}")
            self.setItemWidget(new_item, i + 1, widget)

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()

    instance = {
        f"{p}.parent": {
            "item": QTreeWidgetItem(),
            "widgets": [SpinBoxSlider()],
            "children": {
                f"{p}.{c}.child": {
                    "item": QTreeWidgetItem(),
                    "widgets": [SpinBoxSlider(), ComboBox(), LinkedWidget()],
                }
                for c in range(np.random.randint(1, 4))
            },
        }
        for p in range(np.random.randint(2, 4))
    }

    tree = TreeWidget(instance, column_count=4, header_labels=["Name", "Weight", "Option", "Linked"])

    main_window.setCentralWidget(tree)
    main_window.resize(800, 600)  # Manually set the size of the main window (width, height)
    # main_window.adjustSize()  # Adjust the main window size to fit its contents
    main_window.show()

    sys.exit(app.exec_())

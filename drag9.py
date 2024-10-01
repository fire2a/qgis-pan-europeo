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
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialogButtonBox,
                             QHBoxLayout, QMainWindow, QPushButton, QSlider,
                             QSpinBox, QTreeWidget, QTreeWidgetItem,
                             QTreeWidgetItemIterator, QVBoxLayout, QWidget)

retree = None


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

    def setValue(self, value):
        self.spinBox.setValue(value)
        self.slider.setValue(value)

    def value(self):
        return self.spinBox.value()


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


def cb_close(*args, **kwargs):
    print("cb Close", args, kwargs)


def cb_reset(*args, **kwargs):
    print("cb Reset", args, kwargs)
    from IPython.terminal.embed import InteractiveShellEmbed

    InteractiveShellEmbed()()


def cb_apply(*args, **kwargs):
    global retree
    print("cb Apply", args, kwargs)

    iterator = QTreeWidgetItemIterator(tree)
    retree = []
    while iterator.value():
        item = iterator.value()
        if not item.parent():
            parent = {
                "name": item.text(0),
                "check": item.checkState(0),
                "is_enabled": tree.itemWidget(item, 1).isEnabled(),
                "value": tree.itemWidget(item, 1).value(),
                "weight_widget": tree.itemWidget(item, 1),
            }
            children = []
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    child_item = item.child(i)
                    weight_widget = tree.itemWidget(child_item, 1)
                    child = {
                        "twi": child_item,
                        "name": child_item.text(0),
                        "check": child_item.checkState(0),
                        "is_enabled": weight_widget.isEnabled(),
                        "value": weight_widget.value(),
                        "weight_widget": weight_widget,
                    }
                    children.append(child)
            parent["children"] = children
            retree += [parent]
        iterator += 1

    parent_sum = sum([parent["check"] / 2 * parent["value"] for parent in retree])
    for parent in retree:
        parent_adj_val = parent["check"] / 2 * parent["value"] / (parent_sum if parent_sum != 0 else 1)
        print(
            f"PARENT\t{parent['name']}\t{parent['check']}\t{parent['is_enabled']}\t{parent['value']:.3f}\t{parent_adj_val:.3f}"
        )
        parent["adj_val"] = parent_adj_val
        child_sum = sum([child["check"] / 2 * child["value"] for child in parent["children"]])
        for child in parent["children"]:
            child_adj_val = child["check"] / 2 * child["value"] / (child_sum if child_sum != 0 else 1)
            child["adj_val"] = child_adj_val
            print(
                f"CHILD\t{child['name']}\t{child['check']}\t{child['is_enabled']}\t{child['value']:.3f}\t{child_adj_val:.3f}\t{parent_adj_val*child_adj_val:.3f}"
            )
            # print float with 2 decimals
            # print(f"{parent_adj_val*child_adj_val:.2f}")


def cb_ok(*args, **kwargs):
    global retree
    print("cb Ok", args, kwargs)

    for parent in retree:
        if parent["is_enabled"]:
            parent["weight_widget"].setValue(int(parent["adj_val"] * 100))
        for child in parent["children"]:
            if child["is_enabled"]:
                child["weight_widget"].setValue(int(child["adj_val"] * 100))


def has_parent(item):
    if item.parent():
        return True
    return False


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
        # enable/disable same row widgets according to item check state
        for i in range(self.columnCount() - 1):
            if widget := self.itemWidget(item, i + 1):
                widget.setEnabled(item.checkState(0) == Qt.Checked)
        if parent := item.parent():
            # if checking a child, check parent
            if item.checkState(0) == Qt.Checked:
                parent.setCheckState(0, Qt.Checked)
        else:
            # expand/fold children
            if item.checkState(0) == Qt.Checked:
                item.setExpanded(True)
            else:
                item.setExpanded(False)
                # fold => uncheck children
                for j in range(item.childCount()):
                    child = item.child(j)
                    child.setCheckState(0, Qt.Unchecked)

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

    btn = QPushButton("Adjust Weights")
    buttonBox = QDialogButtonBox(
        QDialogButtonBox.Ok | QDialogButtonBox.Close | QDialogButtonBox.Reset | QDialogButtonBox.Apply,
    )
    buttonBox.addButton(btn, QDialogButtonBox.ActionRole)
    buttonBox.accepted.connect(cb_ok)
    buttonBox.rejected.connect(cb_close)
    for bbb in buttonBox.buttons():
        match bbb.text():
            case "Reset":
                print("reset")
                bbb.clicked.connect(cb_reset)
            case "Apply":
                print("apply")
                bbb.clicked.connect(cb_apply)

    vlayout = QVBoxLayout()
    vlayout.addWidget(tree)
    vlayout.addWidget(buttonBox)
    central_widget = QWidget()
    central_widget.setLayout(vlayout)

    main_window.setCentralWidget(central_widget)
    main_window.resize(800, 600)  # Manually set the size of the main window (width, height)
    # main_window.adjustSize()  # Adjust the main window size to fit its contents
    main_window.show()

    sys.exit(app.exec_())

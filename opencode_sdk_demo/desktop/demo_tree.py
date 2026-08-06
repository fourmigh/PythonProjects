from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QColor

from _shared import DEMO_ORDER, get_description

STATUS_COLORS = {
    "pending": QColor("#7f8c8d"),
    "running": QColor("#3498db"),
    "success": QColor("#27ae60"),
    "failed": QColor("#e74c3c"),
}


class DemoTreeWidget(QTreeWidget):
    demo_selected = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)
        self.itemClicked.connect(self._on_click)
        self._items = {}
        self._build_tree()

    def _build_tree(self):
        for cat, names in DEMO_ORDER:
            cat_label = cat.split("_", 1)[1] if "_" in cat else cat
            cat_item = QTreeWidgetItem(self, [cat_label])
            cat_item.setData(0, 256, ("_category_", cat))
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            cat_item.setForeground(0, QColor("#cccccc"))
            for name in names:
                desc = get_description(cat, name)
                label = name.split("_", 1)[1] if "_" in name else name
                item = QTreeWidgetItem(cat_item, [f"{label}  —  {desc}"])
                item.setData(0, 256, (cat, name))
                item.setForeground(0, QColor("#999999"))
                self._items[(cat, name)] = item
            cat_item.setExpanded(True)

    def _on_click(self, item, column):
        data = item.data(0, 256)
        if data and data[0] != "_category_":
            cat, name = data
            self.demo_selected.emit(cat, name)

    def set_status(self, cat, name, status):
        key = (cat, name)
        if key not in self._items:
            return
        color = STATUS_COLORS.get(status, QColor("#999999"))
        self._items[key].setForeground(0, color)

    def reset_all_status(self):
        for item in self._items.values():
            item.setForeground(0, QColor("#999999"))

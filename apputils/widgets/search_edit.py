from PySide2 import QtGui
from .button_edit import ButtonEdit
from . import icons  # noqa: F401


class SearchEdit(ButtonEdit):
    def __init__(self, parent=None):
        super(SearchEdit, self).__init__(parent)
        self.button.setIcon(QtGui.QIcon(":/apputils/widgets/process-stop.png"))

        self.setPlaceholderText("Filter List")

        self.buttonPressed.connect(self.reset)

    def reset(self):
        self.clear()
        self.textEdited.emit("")
        self.editingFinished.emit()

from PySide2 import QtGui, QtWidgets

class UpperValidator(QtGui.QValidator):
    def validate(self, input, pos):
        # strip & upper
        cleaned = ''.join([a for a in input if 32 <= ord(a) < 128])
        return QtGui.QValidator.Acceptable, cleaned.upper(), pos


class IdentifierEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(IdentifierEdit, self).__init__(parent)

        self._validator = UpperValidator(self)
        self.setValidator(self._validator)

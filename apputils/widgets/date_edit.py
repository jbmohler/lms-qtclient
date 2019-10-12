"""
The DateEdit provides a date input box with more flexible entry.

It also supports null dates which is something QDateEdit does not.
"""

import datetime
import fuzzyparsers
from PySide2 import QtCore, QtGui, QtWidgets
from .button_edit import ButtonEdit
from . import icons # noqa: F401

class DateValidator(QtGui.QValidator):
    def __init__(self, parent=None):
        QtGui.QValidator.__init__(self, parent)

    def fixup(self, input):
        if input == '':
            return ''
        try:
            date = fuzzyparsers.parse_date(input)
        except:
            return ''
        #input.replace(0, input.length(), date.strftime('%x'))
        return date.strftime('%x')

    def validate(self, input, pos):
        try:
            # merely try parsing, return Intermediate if not successful
            _ = fuzzyparsers.parse_date(input)
            return QtGui.QValidator.Acceptable, input, pos
        except Exception:
            return QtGui.QValidator.Intermediate, input, pos
    

class DateEdit(ButtonEdit):
    """
    DateEdit is a QLineEdit derivative that parses input strings into dates 
    with the fuzzyparsers python package.  A QCalendarWidget is available 
    by clicking a button to the right of the edit or pressing F4.
    """
    def __init__(self, parent=None):
        super(DateEdit, self).__init__(parent)
        self.setValidator(DateValidator())
        self.button.setIcon(QtGui.QIcon(':/apputils/widgets/view-calendar.ico'))
        self.editingFinished.connect(self.transform)
        x = self.sizePolicy()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, x.verticalPolicy())

    def minimumSizeHint(self):
        buttonWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        x = ButtonEdit.minimumSizeHint(self)
        x.setWidth(len(datetime.date.today().strftime('%x'))*9+buttonWidth)
        return x

    def sizeHint(self):
        buttonWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        x = ButtonEdit.sizeHint(self)
        x.setWidth(len(datetime.date.today().strftime('%x'))*9+buttonWidth)
        return x

    def date(self):
        x = self.text()
        if x == '':
            return None
        else:
            return QtCore.QDate(fuzzyparsers.parse_date(x))

    def setDate(self, v):
        if hasattr(v, 'toPython'):
            v = v.toPython()
        if v is None:
            self.setText('')
        else:
            self.setText(v.strftime('%x'))

    date = QtCore.Property('QDate', date, setDate)

    def transform(self):
        x = self.text()
        if x != '':
            self.setDate(QtCore.QDate(fuzzyparsers.parse_date(x)))

    def date_selected(self, date):
        self.setDate(date)
        self.calendar.close()
        #self.calendar = None

    def buttonPress(self):
        ButtonEdit.buttonPress(self)
        self.calendar = QtWidgets.QCalendarWidget(self)
        self.calendar.setWindowFlags(QtCore.Qt.Popup)
        if self.date is not None:
            self.calendar.setSelectedDate(self.date)
        self.calendar.activated.connect(self.date_selected)
        self.calendar.clicked.connect(self.date_selected)
        self.calendar.move(self.mapToGlobal(self.rect().bottomLeft()))
        self.calendar.show()
        self.calendar.setFocus(QtCore.Qt.PopupFocusReason)

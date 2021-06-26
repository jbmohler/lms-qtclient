from PySide6 import QtCore, QtWidgets
import apputils
import valix
from . import validators
from . import date_edit
from . import search_edit


def date_value(self):
    try:
        d = self.date
    except (NotImplementedError, ValueError) as e:
        raise apputils.ModValueError(str(e)) from e
    if d == None:
        return None
    return d.toPython()


def date(parent, skinny=False, informational=False):
    Klass = apputils.as_modifiable(date_edit.DateEdit)
    Klass.INVALID = "QLineEdit{ background: --; }".replace("--", valix.INVALID_RGBA)
    Klass.VALID = "QLineEdit{}"
    Klass.value = date_value
    Klass.setValue = lambda self, value: self.setDate(value)
    w = Klass(parent)
    if informational:
        w.button.hide()
    if skinny:
        w.setFrame(False)
        w.setMaximumWidth(15 * 10)
    else:
        w.setMaximumWidth(16 * 10)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.textChanged.connect(lambda *args: w.clear_invalid())
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    w.editingFinished.connect(lambda *args: w.test_invalid())
    return w


def datetimewid(parent):
    Klass = apputils.as_modifiable(QtWidgets.QLineEdit)
    Klass.INVALID = "QLineEdit{ background: --; }".replace("--", valix.INVALID_RGBA)
    Klass.VALID = "QLineEdit{}"
    Klass.value = lambda: apputils.not_implemented_error()
    Klass.setValue = lambda self, value: self.setText(
        "" if value == None else f"{value:%m/%d/%Y %I:%M:%S %p}"
    )
    w = Klass(parent)
    w.setMaximumWidth(24 * 10)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.textChanged.connect(lambda *args: w.clear_invalid())
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    w.editingFinished.connect(lambda *args: w.test_invalid())
    return w


def checkbox(parent, label=None):
    Klass = apputils.as_modifiable(QtWidgets.QCheckBox)
    Klass.value = lambda self: self.isChecked()
    Klass.setValue = lambda self, value: self.setChecked(
        value if value != None else False
    )
    Klass.setReadOnly = lambda self, ro: self.setEnabled(not ro)
    Klass.internal_label = True
    Klass.set_internal_label = lambda self, label: self.setText(label)
    w = Klass(parent)
    if label != None:
        w.setText(label)
    w.toggled.connect(lambda *args: w.setWidgetModified(True))
    w.toggled.connect(lambda *args: w.setValueApplied())
    return w


def none_as_blank(v):
    return "" if v == None else str(v)


def int_none_allowed(t):
    return None if t == "" else int(t)


def integer(parent):
    Klass = apputils.as_modifiable(QtWidgets.QLineEdit)
    Klass.value = lambda self: int_none_allowed(self.text())
    Klass.setValue = lambda self, value: self.setText(none_as_blank(value))
    w = Klass(parent)
    w.setValidator(validators.BlankableIntValidator(w))
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w


def float_none_allowed(value):
    if value in ["", None]:
        return None
    if isinstance(value, str) and "," in value:
        value = value.replace(",", "")
    return float(value)


def QLineEdit_setText_fromDouble(self, value, decimals):
    if value == None:
        s = ""
    else:
        s = f"{{:,.{decimals}f}}".format(value)
    self.setText(s)


def quantity_value(self):
    try:
        return float_none_allowed(self.text())
    except (NotImplementedError, ValueError) as e:
        raise apputils.ModValueError(str(e)) from e


def quantity(parent, decimals=None):
    Klass = apputils.as_modifiable(QtWidgets.QLineEdit)
    Klass.INVALID = "QLineEdit{ background: --; }".replace("--", valix.INVALID_RGBA)
    Klass.VALID = "QLineEdit{}"
    Klass.value = quantity_value
    if decimals == None:
        Klass.setValue = lambda self, value: self.setText(none_as_blank(value))
    else:
        Klass.setValue = lambda self, value, d=decimals: QLineEdit_setText_fromDouble(
            self, value, d
        )
    w = Klass(parent)
    w.setMaximumWidth(12 * 10)
    w.setValidator(validators.BlankableFloatValidator(w))
    w.setAlignment(QtCore.Qt.AlignRight)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.textChanged.connect(lambda *args: w.clear_invalid())
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    w.editingFinished.connect(lambda *args: w.test_invalid())
    return w


def QLineEdit_setText_fromPercent(self, value, decimals):
    if value == None:
        s = ""
    else:
        s = f"{{:.{decimals}f}}".format(value * 100.0)
    self.setText(s)


def percent_value(self):
    try:
        base = float_none_allowed(self.text())
        if base == None:
            return ""
        return base / 100.0
    except (NotImplementedError, ValueError) as e:
        raise apputils.ModValueError(str(e)) from e


def percent(parent, decimals=None):
    if decimals == None:
        decimals = 1
    Klass = apputils.as_modifiable(QtWidgets.QLineEdit)
    Klass.INVALID = "QLineEdit{ background: --; }".replace("--", valix.INVALID_RGBA)
    Klass.VALID = "QLineEdit{}"
    Klass.value = percent_value
    if decimals == None:
        Klass.setValue = lambda self, value: self.setText(none_as_blank(value))
    else:
        Klass.setValue = lambda self, value, d=decimals: QLineEdit_setText_fromPercent(
            self, value, d
        )
    w = Klass(parent)
    w.setMaximumWidth(12 * 10)
    w.setValidator(validators.BlankableFloatValidator(w))
    w.setAlignment(QtCore.Qt.AlignRight)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.textChanged.connect(lambda *args: w.clear_invalid())
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    w.editingFinished.connect(lambda *args: w.test_invalid())
    return w


def radio(parent, options, hotkey=False):
    def set_value(grp, value):
        for v, wid in grp.radios.items():
            if v == value:
                wid.setChecked(True)
            else:
                wid.setChecked(False)

    def value(grp):
        return grp.checkedButton()._value

    Klass = apputils.as_modifiable(QtWidgets.QButtonGroup)
    Klass.value = value
    Klass.setValue = set_value
    w = Klass(parent)
    w.radios = {}
    for shown, value in options:
        if hotkey:
            shown = "&" + shown
        r = QtWidgets.QRadioButton(shown)
        r._value = value
        w.radios[value] = r
        w.addButton(r)
    w.buttonClicked.connect(lambda *args: w.setWidgetModified(True))
    w.buttonClicked.connect(lambda *args: w.setValueApplied())
    return w


class DualComboBoxBase(QtWidgets.QStackedWidget):
    def __init__(self, parent=None):
        super(DualComboBoxBase, self).__init__(parent)

        self._combo = QtWidgets.QComboBox()
        self._redit = QtWidgets.QLineEdit()
        self._redit.setReadOnly(True)

        self.addWidget(self._combo)
        self.addWidget(self._redit)

        self.setFocusProxy(self._combo)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

    def clear(self):
        self._combo.clear()

    def addItem(self, text, userData):
        self._combo.addItem(text, userData)

    def view(self):
        return self._combo.view()

    def setReadOnly(self, ro):
        self.setCurrentIndex(0 if not ro else 1)


class DualComboBox(DualComboBoxBase):
    def value(self):
        return self._combo.itemData(self._combo.currentIndex(), QtCore.Qt.UserRole)

    def setValue(self, value):
        self._combo.setCurrentIndex(self._combo.findData(value, QtCore.Qt.UserRole))
        self._redit.setText(self._combo.currentText())

    def set_options(self, options):
        self._combo.clear()
        for shown, value in options:
            self._combo.addItem(shown, value)


def combo(parent, options=None):
    Klass = apputils.as_modifiable(DualComboBox)
    w = Klass(parent)
    if options != None:
        w.set_options(options)
    w._combo.currentIndexChanged.connect(lambda *args: w.setWidgetModified(True))
    w._combo.currentIndexChanged.connect(lambda *args: w.setValueApplied())
    return w


def basic(parent, characters=None, uppercase=False, alignment=None, skinny=False):
    Klass = apputils.as_modifiable(QtWidgets.QLineEdit)
    Klass.value = lambda self: self.text()
    Klass.setValue = lambda self, value: self.setText(value)
    w = Klass(parent)
    if uppercase:
        w._validator = validators.UpperValidator(w)
        w.setValidator(w._validator)
    if skinny:
        w.setFrame(False)
    if characters != None:
        w.setMaximumWidth(characters * 11)
    if alignment == "right":
        w.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w


def search(parent, characters=None):
    Klass = apputils.as_modifiable(search_edit.SearchEdit)
    Klass.value = lambda self: self.text()
    Klass.setValue = lambda self, value: self.setText(value)
    w = Klass(parent)
    if characters != None:
        w.setMaximumWidth(characters * 11)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w


class TextEdit2(QtWidgets.QTextEdit):
    editingFinished = QtCore.Signal()

    def focusOutEvent(self, event):
        self.editingFinished.emit()
        super(TextEdit2, self).focusOutEvent(event)


def multiline(parent):
    Klass = apputils.as_modifiable(TextEdit2)
    Klass.value = lambda self: self.toPlainText()
    Klass.setValue = lambda self, value: self.setPlainText(value)
    w = Klass(parent)
    w.setTabChangesFocus(True)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w


def richtext(parent):
    Klass = apputils.as_modifiable(TextEdit2)
    Klass.value = lambda self: self.toHtml()
    Klass.setValue = lambda self, value: self.setHtml(value)
    w = Klass(parent)
    w.setTabChangesFocus(True)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w

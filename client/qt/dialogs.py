from PySide2 import QtWidgets
import rtlib
from . import bindings
from . import utils

def no_op():
    pass


class ObjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ObjectDialog, self).__init__(parent)

        name = QtWidgets.QApplication.instance().applicationName()
        self.setWindowTitle(name)

        self.applychanges = no_op
        self.attrs = []
        self._button_row = None

        self.binder = bindings.Binder(self)

    def button_row(self):
        if self._button_row != None:
            return self._button_row
        QDB = QtWidgets.QDialogButtonBox
        self._button_row = QDB(QDB.Ok | QDB.Cancel)
        self._button_row.accepted.connect(self.accept)
        self._button_row.rejected.connect(self.reject)
        return self._button_row

    def bind(self, row=None):
        if row == None:
            attrs = [a for a, _ in self.attrs]
            values = [v for _, v in self.attrs]
            self.RowType = rtlib.fixedrecord('RowType', attrs)
            row = self.RowType(*tuple(values))

        self.binder.bind(row)

    def get_bound(self):
        return self.binder.bound

    def accept(self):
        self.binder.save(self.binder.bound)

        abort_accept = True
        try:
            if self.applychanges == no_op:
                abort_accept = False
            else:
                abort_accept = not self.applychanges(self.binder.bound)
        except:
            utils.exception_message(self, 'Error applying changes.')
            abort_accept = True

        if abort_accept:
            return

        return super(ObjectDialog, self).accept()


class InternalLabelFormLayout(QtWidgets.QFormLayout):
    def __init__(self, parent=None):
        super(InternalLabelFormLayout, self).__init__(parent)
        self._label_wid_list = []

    def addRow(self, label, widget, finalize=True):
        if getattr(widget, 'internal_label', False):
            widget.set_internal_label(label)
            labwid = QtWidgets.QLabel('')
        else:
            labwid = QtWidgets.QLabel(label)
            labwid.setBuddy(widget)
        self._label_wid_list.append(labwid)
        super(InternalLabelFormLayout, self).addRow(labwid, widget)

        if finalize:
            self.finalize()

    def finalize(self):
        # There seems to be a bug in which QFormLayout
        # does not correctly follow the size hints
        # when the label is null/empty.  We manually
        # set the minimum width here to compensate for
        # that bug.
        labwidth = max([lw.sizeHint().width() for lw in self._label_wid_list])
        for lw in self._label_wid_list:
            lw.setMinimumWidth(labwidth)

class FormEntryDialog(ObjectDialog):
    def __init__(self, text, parent=None):
        super(FormEntryDialog, self).__init__(parent)

        self.attrs = []

        self.layout = QtWidgets.QVBoxLayout(self)
        self.buttons = self.button_row()
        self.label = QtWidgets.QLabel(text)
        self.form = InternalLabelFormLayout()
        self.layout.addWidget(self.label)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttons)

    def add_form_row(self, attr, label, type_, default=None, **kwargs):
        self.attrs.append((attr, default))
        self.binder.construct(attr, type_, **kwargs)
        w = self.binder.widgets[attr]

        self.form.addRow(label, w)

        items = [w] + list(self.buttons.buttons())
        for a, b in zip(items[:-1], items[1:]):
            QtWidgets.QWidget.setTabOrder(a, b)

"""
What is a mayor?  It is an abstraction of an binding map from attribute names
to editable widgets on screen.  It has two main incarnations.  One is a simple
binding map from attributes to widgets in a form layout.  The second is a grid
with rows and columns.
"""

import contextlib
from PySide6 import QtCore, QtWidgets
import valix
import apputils
from . import bindings
from . import utils


class SaveError(RuntimeError):
    pass


def commit_mayor(mayor):
    import apputils.widgets as widgets

    if isinstance(mayor, widgets.TableView):
        mayor.commit_editors()
    elif isinstance(mayor, bindings.Binder):
        if mayor.bound == None:
            raise NotImplementedError("unconnected singleton mayor ... mayday")
        mayor.save(mayor.bound)
    else:
        raise NotImplementedError("unsupported type of mayor")


def focus_to_edit(mayor, error):
    import apputils.widgets as widgets

    if isinstance(mayor, widgets.TableView):
        index = mayor.model().index_object_column(error[0], error[1])
        mayor.setCurrentIndex(index)
    elif isinstance(mayor, bindings.Binder):
        w = mayor.widgets[error[1]]
        w.setFocus()
    else:
        raise NotImplementedError("unsupported type of mayor")


def highlight_errors(mayor, errors):
    import apputils.widgets as widgets

    if isinstance(mayor, widgets.TableView):
        mayor.model().update_invalid_fields([], errors)


class ValidationSession:
    def __init__(self, frame):
        self.frame = frame

        self._errors = []

    def class_validate_rowset(self, klass, rows, mayor):
        x = valix.class_validate_rowset(klass, rows)
        if len(x):
            self._errors.append((mayor, x))

    def class_validate_row(self, klass, row, mayor):
        self.class_validate_rowset(klass, [row], mayor)

    def has_errors(self):
        return len(self._errors)

    def errors(self):
        for mayor, e in self._errors:
            for e2 in e:
                yield mayor, e2

    def highlight_mayors(self):
        for mayor, e in self._errors:
            highlight_errors(mayor, e)

    def finalize(self):
        self.frame.finalize_session(self)


VAL_FRAME_CSS = """
QFrame {
    background: --;
}
""".replace(
    "--", valix.INVALID_RGBA
)


class ValidationFrame(QtWidgets.QFrame):
    focus_error = QtCore.Signal()

    def __init__(self, parent):
        super(ValidationFrame, self).__init__(parent)

        self.hide()

        self.obscured = parent
        self.obscured.installEventFilter(self)

        self.layout = QtWidgets.QHBoxLayout(self)
        self.status = QtWidgets.QLabel("no errors")
        self.gobtn = QtWidgets.QPushButton("&Fix Error")
        self.gobtn.clicked.connect(self.focus_error.emit)
        self.hidebtn = QtWidgets.QPushButton("&X")
        self.hidebtn.clicked.connect(self.hide)
        self.layout.addWidget(self.status)
        self.layout.addStretch(12)
        self.layout.addWidget(self.gobtn)
        self.layout.addWidget(self.hidebtn)

        self.setStyleSheet(VAL_FRAME_CSS)
        self._set_size()

        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setInterval(1000 * 5)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def _set_size(self):
        s = self.obscured.size()
        s.setHeight(36)
        self.resize(s)

    def eventFilter(self, obj, ev):
        if obj == self.obscured and ev.type() == QtCore.QEvent.Resize:
            self._set_size()
            # self.show()
        return False

    def hideEvent(self, event):
        self.hide_timer.stop()
        return super(ValidationFrame, self).hideEvent(event)

    def session(self):
        return ValidationSession(self)

    def finalize_session(self, session):
        if session.has_errors():
            mayor, error = next(session.errors())
            self.status.setText(error[2])
            self.show()
            self.hide_timer.start()
            focus_to_edit(mayor, error)
            raise SaveError("validation failed")


class DocumentTracker:
    def __init__(self):
        self.dirty = False
        self._dirty_fields = set()
        self.load_lockout = False
        self._mayors = None

    @contextlib.contextmanager
    def loading(self, reset=True):
        self.load_lockout = True
        yield
        self.load_lockout = False
        if reset:
            self.reset_dirty()

    def is_dirty(self):
        return self.dirty

    def is_dirty_attr(self, row, attr):
        return (id(row), attr) in self._dirty_fields

    def dirty_rows(self, rows):
        dirties = set([x for x, _ in self._dirty_fields])
        return [row for row in rows if id(row) in dirties]

    def set_mayor_list(self, mayors):
        self._mayors = list(mayors)

    def reset_dirty(self):
        self.dirty = False
        self._dirty_fields = set()

    def set_dirty(self, row, attr):
        if not self.load_lockout:
            self.dirty = True
            self._dirty_fields.add((id(row), attr))

    def ask_save(self, parent):
        """
        Returns one of 'Yes', 'No', 'Cancel'
        """
        if not self.dirty:
            return "No"
        return apputils.message(
            parent, "Do you want to save changes?", buttons=["Yes", "No", "Cancel"]
        )

    def _commit_mayors(self):
        for mayor in self._mayors:
            commit_mayor(mayor)

    def window_close(self, parent, callback, confirmed=False):
        if self._mayors == None:
            return True

        self._commit_mayors()
        if confirmed:
            save = "Yes"
        else:
            save = self.ask_save(parent)
        if save == "Yes":
            try:
                callback()
            except SaveError:
                return False
            except:
                utils.exception_message(parent, "Error Saving")
                return False
        if save == "Cancel":
            return False

        return True

    # For the moment I do not know what would be different between a close
    # event and a new/open-different document.  However it seems pleasant to be
    # distinct.
    window_new_document = window_close


class SaveButtonDocumentTracker(DocumentTracker):
    def __init__(self, button, save_callback):
        super(SaveButtonDocumentTracker, self).__init__()
        self.button = button
        self.button.clicked.connect(lambda *args: self.save(asksave=False))
        self.callback = save_callback

    def set_dirty(self, row, attr):
        super(SaveButtonDocumentTracker, self).set_dirty(row, attr)
        self.button.setEnabled(self.dirty)

    def reset_dirty(self):
        super(SaveButtonDocumentTracker, self).reset_dirty()
        self.button.setEnabled(self.dirty)

    def save(self, asksave):
        if self.is_dirty:
            save = self.ask_save(self.button.window()) if asksave else "Yes"
        else:
            return True
        reset = False
        if save == "Yes":
            try:
                self.callback()
                reset = True
            except:
                return False
        if save == "Cancel":
            return False
        if reset:
            self.reset_dirty()
        return True

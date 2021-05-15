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


def containing_mayor(row, mayors):
    for mayor in mayors:
        import apputils.widgets as widgets

        if isinstance(mayor, widgets.TableView):
            if row in mayor.model()._main_rows:
                return mayor
        elif isinstance(mayor, bindings.Binder):
            if mayor.bound == row:
                return mayor
        else:
            raise NotImplementedError("unsupported type of mayor")
    return None


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
        for e in self._errors:
            mayor = containing_mayor(e[0], self._mayors)
            yield mayor, e

    def highlight_mayors(self):
        grouped = {id(m): (m, []) for m in self._mayors}
        for e in self._errors:
            mayor = containing_mayor(e[0], self._mayors)
            grouped[id(mayor)][1].append(e)
        for m, errors in grouped.items():
            if len(errors[1]) > 0:
                highlight_errors(*errors)

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


class DocumentTracker(QtCore.QObject):
    dirty_change = QtCore.Signal(bool)  # is_dirty
    post_save = QtCore.Signal(str)  # mode

    def __init__(self, parent, save_callback):
        super(DocumentTracker, self).__init__(parent)

        self.widparent = parent
        self.save_callback = save_callback

        self.dirty = False
        self._dirty_fields = set()
        self.is_new_document = False
        self.load_lockout = False
        self._mayors = None

    @contextlib.contextmanager
    def loading(self, reset=True):
        self.load_lockout = True
        yield
        self.load_lockout = False
        if reset:
            self.reset_dirty()

    def connect_button(self, button):
        button.clicked.connect(lambda: self.command_save(asksave=False))
        self.dirty_change.connect(button.setEnabled)
        button.setEnabled(self.dirty)

    def connect_action(self, action):
        action.triggered.connect(lambda: self.command_save(asksave=False))
        self.dirty_change.connect(action.setEnabled)
        action.setEnabled(self.dirty)

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
        self.dirty_change.emit(self.dirty)

    def set_dirty(self, row, attr):
        if not self.load_lockout:
            self.dirty = True
            self._dirty_fields.add((id(row), attr))

            self.dirty_change.emit(self.dirty)

    def ask_save(self):
        """
        Returns one of 'Yes', 'No', 'Cancel'
        """
        if not self.dirty:
            return "No"
        return apputils.message(
            self.widparent,
            "Do you want to save changes?",
            buttons=["Yes", "No", "Cancel"],
        )

    def _commit_mayors(self):
        for mayor in self._mayors:
            commit_mayor(mayor)

    def _core_save(self, asksave):
        if self._mayors == None:
            return True

        self._commit_mayors()
        save = self.ask_save() if asksave else ("Yes" if self.dirty else "No")
        reset = False
        if save == "Yes":
            try:
                self.save_callback()
                reset = True
            except SaveError:
                return False
            except:
                utils.exception_message(
                    self.widparent, "Error Saving", logged="unknown"
                )
                return False
        if save == "Cancel":
            return False
        if reset:
            self.reset_dirty()

        return True

    def window_close(self, asksave=True):
        result = self._core_save(asksave=asksave)
        if result:
            self.post_save.emit("window_close")
        return result

    def window_new_document(self, asksave=True):
        result = self._core_save(asksave=asksave)
        if result:
            self.post_save.emit("window_close")
        return result

    def command_save(self, asksave=False, enforce_persist_new=False):
        if self.is_new_document and enforce_persist_new:
            self.set_dirty(None, "__new__")

        result = self._core_save(asksave)
        if result:
            self.post_save.emit("command_save")
        return result

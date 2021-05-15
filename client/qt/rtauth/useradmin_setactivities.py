import uuid
from PySide6 import QtCore, QtWidgets
import rtlib
import apputils
import apputils.widgets as widgets
import apputils.viewmenus as viewmenus
from client.qt import winlist
from client.qt import valqt
from client.qt import gridmgr


def attr_2_label(attr):
    if attr == None:
        return ""
    if attr.startswith("api_"):
        attr = attr[4:]
    if attr.startswith("put_api_"):
        attr = attr[8:]
    if attr.startswith("delete_"):
        attr = attr[7:]
    if attr.startswith("post_api_"):
        attr = attr[9:]
    return attr.replace("_", " ").title()


class ActivitiesEditing:
    # TODO: write the setattr with tracker notify!

    @classmethod
    def from_unregistered(kls, row):
        self = kls()
        self.id = uuid.uuid1().hex
        self.description = (
            row.description
            if row.description not in ["", None]
            else attr_2_label(row.act_name)
        )
        self.save = row.act_name not in ["", None]
        for attr in kls.__slots__:
            if attr not in ["description", "id", "save"]:
                setattr(self, attr, getattr(row, attr))
        return self


class ManageActivities(QtWidgets.QMainWindow):
    ID = "admin_write_activities"
    TITLE = "Manage Activities List"
    SRC_URL = "api/activities"

    def __init__(self, session, exports_dir, parent=None, unregistered=True):
        super(ManageActivities, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowIcon(QtWidgets.QApplication.instance().icon)
        self.setWindowTitle(self.TITLE)
        winlist.register(self, self.ID)

        self.center = QtWidgets.QWidget()
        self.setCentralWidget(self.center)
        self.layout = QtWidgets.QVBoxLayout(self.center)
        self.grid = widgets.EditableTableView()
        self.grid.setObjectName("content")
        self.grid.setSortingEnabled(True)
        self.gridmgr = gridmgr.GridManager(self.grid, self)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.btn_save = self.buttons.addButton(QDB.Save)
        self.layout.addWidget(self.grid)
        self.layout.addWidget(self.buttons)

        self.client = session.std_client()
        self.backgrounder = apputils.Backgrounder(self)
        self.ctxmenu = viewmenus.ContextMenu(self.grid, self)
        self.tracker = valqt.DocumentTracker(self, self.save_activities)
        self.tracker.connect_button(self.btn_save)
        self.tracker.post_save.connect(self.refresh)

        self.geo = apputils.WindowGeometry(
            self, size=True, position=False, grids=[self.grid]
        )

        if unregistered:
            self.refresh()

    def refresh(self):
        self.backgrounder(
            self.load_unregistered,
            self.client.get,
            "api/endpoints",
            unregistered=True,
        )

    def load_unregistered(self):
        self.center.setEnabled(False)
        try:
            content = yield
            loaded = content.main_table()

            columns = [
                ("id", {"type": "yenot_activity.surrogate"}),
            ]

            # create editable row from unregistered row
            for attr, meta in content.main_columns():
                if attr == "description":
                    meta = meta.copy()
                    meta["check_attr"] = "save"
                    meta["editable"] = True
                    columns.insert(1, (attr, meta))
                else:
                    columns.append((attr, meta))

            self.records = rtlib.ClientTable(columns, [], mixin=ActivitiesEditing)

            for row in loaded.rows:
                self.records.rows.append(self.records.DataRow.from_unregistered(row))

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)

            self.tracker.set_mayor_list([self.grid])
            self.tracker.set_dirty(None, "__new__")

            self.center.setEnabled(True)
        except:
            apputils.exception_message(
                self, f"There was an error loading {self.TITLE}."
            )

    def save_activities(self):
        try:
            tosend = self.records.duplicate(
                rows=[r for r in self.records.rows if r.save]
            )
            files = {"activities": tosend.as_http_post_file(exclusions=["method"])}

            self.client.post(self.SRC_URL, files=files)
        except Exception:
            apputils.exception_message(self.window(), f"Error saving {self.TITLE}.")
            raise

    def closeEvent(self, event):
        if not self.tracker.window_close(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(ManageActivities, self).closeEvent(event)

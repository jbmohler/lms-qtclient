from PySide6 import QtCore, QtWidgets
import apputils
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
import client.qt as qt
from client.qt import valqt
from client.qt import winlist
from client.qt import gridmgr


class RoleMixin:
    tracker = None


class UserIndexer(object):
    def __init__(self, user_id):
        self.user_id = user_id

    def __get__(self, obj, objtype):
        return obj.users.linked(self.user_id)

    def __set__(self, obj, value):
        obj.tracker.set_dirty(obj, "users")
        obj.users.toggle_linked(self.user_id, value)


class UserRoleMapperLineTracker(valqt.DocumentTracker):
    def set_dirty(self, row, attr):
        if not self.load_lockout:
            if not hasattr(self, "_mods"):
                self._mods = set()
            self._mods.add(row)
        super(UserRoleMapperLineTracker, self).set_dirty(row, attr)

    @property
    def modified(self):
        if hasattr(self, "_mods"):
            return self._mods
        else:
            return []


class UserRoleMapperTargetsByUser(QtWidgets.QMainWindow):
    ID = "admin_userrole_mapper"
    TITLE = "Set User Roles"
    SRC_URL = "api/userroles/by-users"

    def __init__(self, session, exports_dir, parent=None, users=None):
        super(UserRoleMapperTargetsByUser, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        winlist.register(self, self.ID)

        self.user_universe = list(users)

        self.center = QtWidgets.QWidget()
        self.setCentralWidget(self.center)
        self.layout = QtWidgets.QVBoxLayout(self.center)
        self.grid = widgets.EditableTableView()
        self.grid.setObjectName("content")
        self.grid.setSortingEnabled(True)
        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.btn_save = self.buttons.addButton(QDB.Save)
        self.buttons.addButton(QDB.Reset).clicked.connect(self.reset)
        self.layout.addWidget(self.grid)
        self.layout.addWidget(self.buttons)

        self.client = session.std_client()
        self.backgrounder = apputils.Backgrounder(self)
        self.ctxmenu = viewmenus.ContextMenu(self.grid, self)

        self.tracker = UserRoleMapperLineTracker(self, self.save_targets)
        self.tracker.connect_button(self.btn_save)
        self.reset()

        self.geo = apputils.WindowGeometry(
            self, size=True, position=False, grids=[self.grid]
        )

    def reset(self):
        if not self.tracker.window_new_document(asksave=True):
            return

        self.model = None
        self.backgrounder(
            self.load, self.client.get, self.SRC_URL, users=",".join(self.user_universe)
        )

    def load(self):
        self.setEnabled(False)
        try:
            content = yield

            clsvars = {"tracker": self.tracker}
            for u in self.user_universe:
                clsvars[f"user_{u}"] = UserIndexer(u)

            with self.tracker.loading():
                self.records = content.main_table(mixin=RoleMixin, cls_members=clsvars)
                self.users = content.named_table("usernames")
                self.users.rows.sort(key=lambda x: x.username)

            columns = [c for c in self.records.columns if c.attr in ["role_name"]]
            for u in self.users.rows:
                columns.append(
                    apputils.field(
                        f"user_{u.id}",
                        u.username,
                        type_="boolean",
                        checkbox=True,
                        editable=True,
                    )
                )
            self.model = apputils.ObjectQtModel(columns=columns)

            with self.geo.grid_reset(self.grid):
                self.grid.setModel(self.model)
                self.model.set_rows(self.records.rows)
            self.tracker.set_mayor_list([self.grid])
            self.tracker.reset_dirty()

            self.ctxmenu.update_model()
            self.ctxmenu.reset_action_list()
            gridmgr.apply_column_url_views(self.ctxmenu, self.grid.model())

            self.setEnabled(True)
        except:
            qt.exception_message(self, f"There was an error loading {self.TITLE}.")

    def save_targets(self):
        try:
            tosend = self.records.duplicate(rows=list(self.tracker.modified))
            data = {"users": ",".join(self.user_universe)}
            files = {"roles": tosend.as_http_post_file()}

            self.client.put(self.SRC_URL, data=data, files=files)
        except Exception:
            qt.exception_message(self.window(), f"Error saving {self.TITLE}.")
            raise

    def closeEvent(self, event):
        if not self.tracker.window_close(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(UserRoleMapperTargetsByUser, self).closeEvent(event)

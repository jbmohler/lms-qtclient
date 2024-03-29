from PySide6 import QtCore, QtWidgets
import apputils
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
import client.qt as qt
from client.qt import valqt
from client.qt import gridmgr
from client.qt import winlist


class UserMixin:
    tracker = None


class RoleIndexer(object):
    def __init__(self, role_id):
        self.role_id = role_id

    def __get__(self, obj, objtype):
        return obj.roles.linked(self.role_id)

    def __set__(self, obj, value):
        obj.tracker.set_dirty(obj, "roles")
        obj.roles.toggle_linked(self.role_id, value)


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


class UserRoleMapperTargetsByRole(QtWidgets.QMainWindow):
    ID = "admin_userrole_mapper"
    TITLE = "Set User Roles"
    SRC_URL = "api/userroles/by-roles"

    def __init__(self, session, exports_dir, parent=None, roles=None):
        super(UserRoleMapperTargetsByRole, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        winlist.register(self, self.ID)

        self.role_universe = list(roles)

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
            self.load, self.client.get, self.SRC_URL, roles=",".join(self.role_universe)
        )

    def load(self):
        self.setEnabled(False)
        try:
            content = yield

            clsvars = {"tracker": self.tracker}
            for u in self.role_universe:
                clsvars[f"role_{u}"] = RoleIndexer(u)

            with self.tracker.loading():
                self.records = content.main_table(mixin=UserMixin, cls_members=clsvars)
                self.roles = content.named_table("roles:universe")
                self.roles.rows.sort(key=lambda x: x.role_name)

            columns = [c for c in self.records.columns if c.attr in ["username"]]
            for u in self.roles.rows:
                columns.append(
                    apputils.field(
                        f"role_{u.id}",
                        u.role_name.replace(" ", "\n", 2),
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
            qt.exception_message(
                self.window(), f"There was an error loading {self.TITLE}."
            )

    def save_targets(self):
        try:
            tosend = self.records.duplicate(rows=list(self.tracker.modified))
            data = {"roles": ",".join(self.role_universe)}
            files = {"users": tosend.as_http_post_file()}

            self.client.put(self.SRC_URL, data=data, files=files)
        except Exception:
            qt.exception_message(self.window(), f"Error saving {self.TITLE}.")
            raise

    def closeEvent(self, event):
        if not self.tracker.window_new_document(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(UserRoleMapperTargetsByRole, self).closeEvent(event)

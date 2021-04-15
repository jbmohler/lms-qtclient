from PySide6 import QtCore, QtGui, QtWidgets
import rtlib
import apputils
import apputils.models as models
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
from client.qt import bindings
from client.qt import reporttab
import client.qt as qt
from .useradmin_userroles import UserRoleMapperTargetsByUser
from .useradmin_userroles_selected_roles import UserRoleMapperTargetsByRole
from .useradmin_roleactivities import RoleActivityMapperTargets


class ReportTabEx(reporttab.ReportTab):
    def __init__(self, parent=None, state=None):
        super(ReportTabEx, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = state.exports_dir
        self.client = state.session.std_client()
        self.backgrounder = apputils.Backgrounder(self)
        self.ctxmenu = viewmenus.ContextMenu(self.grid, self)
        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

        self.init_view2()

        self.refresh()

    def init_view2(self):
        pass


class SessionList(ReportTabEx):
    ID = "administrative/sessions"
    TITLE = "Active Session List"
    URL_TAIL = "api/sessions/active"


class UserListSidebar(QtWidgets.QWidget):
    TITLE = "User"
    ID = "user-view"
    SRC_INSTANCE_URL = "api/user/{}"
    refresh = QtCore.Signal()

    def __init__(self, parent, state):
        super(UserListSidebar, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = state.session.std_client()
        self.exports_dir = state.exports_dir
        self.added = False

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        # User Button with menu
        self.btn_user = self.buttons.addButton("User", self.buttons.ActionRole)
        self.entmenu = QtWidgets.QMenu()
        self.entmenu.addAction("New").triggered.connect(self.cmd_add_user)
        self.entmenu.addSeparator()
        self.entmenu.addAction("Edit").triggered.connect(
            self.adapt_sbcommand(self.cmd_edit_user)
        )
        self.entmenu.addAction("Change Password").triggered.connect(
            self.adapt_sbcommand(self.cmd_change_password)
        )
        self.entmenu.addAction("Set Roles").triggered.connect(
            lambda: self.cmd_set_roles([self.userrow])
        )
        self.entmenu.addAction("Delete").triggered.connect(
            self.adapt_sbcommand(self.cmd_delete_user)
        )
        self.btn_user.setMenu(self.entmenu)

        self.layout.addWidget(self.buttons)

        # User information
        self.html = QtWidgets.QTextBrowser()
        # self.html.linkClicked.connect(gridmgr.show_link)
        self.layout.addWidget(self.html)

        # Roles

        # Device Tokens
        self.devtok_grid = widgets.TableView()
        self.devtok_grid.setSortingEnabled(True)
        self.devtok_gridmgr = qt.GridManager(self.devtok_grid, self)
        self.layout.addWidget(self.devtok_grid)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.devtok_grid]
        )

    def init_grid_menu(self, gridmgr):
        self.gridmgr = gridmgr

        if not self.added:
            self.added = True
            self.gridmgr.add_action("&Add User", triggered=self.cmd_add_user)
            self.gridmgr.add_action("&Set Roles", triggered=self.cmd_set_roles)
            self.gridmgr.add_action("&Edit User", triggered=self.cmd_edit_user)
            self.gridmgr.add_action("&Delete User", triggered=self.cmd_delete_user)

    def highlight(self, row):
        if row == None:
            self.html.setHtml("")
            self.devtok_grid.setModel(None)
        else:
            self.backgrounder(
                self.load_users,
                self.client.get,
                self.SRC_INSTANCE_URL,
                row.id,
            )

    def load_users(self):
        try:
            content = yield apputils.AnimateWait(self)

            self.user = content.named_table("user")
            self.userrow = self.user.rows[0]

            self.roles = content.named_table("roles")

            self.html.setHtml(
                f"""
<b>Username: </b>{self.userrow.username}<br />
<b>Full Name: </b>{self.userrow.full_name}<br />
<b>Description: </b>{self.userrow.descr}<br />

<hline>

{self.roles.as_html()}
"""
            )

            with self.geo.grid_reset(self.devtok_grid):
                self.devtokens = content.named_table("devicetokens")
                self.devtok_gridmgr.set_client_table(self.devtokens)
        except:
            qt.exception_message(self.window(), "Error loading users")
            return

    def adapt_sbcommand(self, f):
        return lambda: f(self.userrow)

    def cmd_add_user(self):
        user = rtlib.ClientTable(
            [
                ("full_name", None),
                ("username", None),
                ("password", None),
                ("password2", None),
                ("descr", None),
            ],
            [],
        )
        with user.adding_row() as r2:
            pass
        if edit_user_dlg(self, user, editrec=False):
            self.refresh.emit()

    def cmd_edit_user(self, row):
        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        user = content.main_table()
        if edit_user_dlg(self, user, editrec=True):
            self.refresh.emit()

    def cmd_change_password(self, row):
        utils.to_be_implemented("change password dialog")

    def cmd_set_roles(self, rows):
        users = [o.id for o in rows]

        w = UserRoleMapperTargetsByUser(
            self.client.session, self.exports_dir, None, users
        )
        w.show()
        # TODO: should show call be modal?
        # self.refresh.emit()

    def cmd_delete_user(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f"Are you sure that you wish to delete the user {row.username}?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.id)
                self.refresh.emit()
            except:
                qt.exception_message(self.window(), "The user could not be deleted.")


class UserList(QtWidgets.QWidget):
    ID = "administrative/users"
    TITLE = "User List"
    URL_TAIL = "api/users/list"
    SRC_INSTANCE_URL = "api/user/{}"

    def __init__(self, parent=None, state=None):
        super(UserList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = state.exports_dir
        self.client = state.session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = qt.RevealedSplitter(QtCore.Qt.Horizontal)

        self.sidebar = UserListSidebar(self, state)

        self.grid = widgets.TableView()
        self.grid.setObjectName("content")
        self.grid.setSortingEnabled(True)
        self.gridmgr = qt.GridManager(self.grid, self)
        self.gridmgr.current_row_update.connect(self.sidebar_update)
        self.sidebar.init_grid_menu(self.gridmgr)
        self.splitter.addWidget(self.grid)
        self.splitter.addWidget(self.sidebar)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.splitter)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton("&Refresh", QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton("&Export", QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

        self.refresh()

    def sidebar_update(self):
        row = self.gridmgr.selected_row()
        self.sidebar.highlight(row)

    def load(self):
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys["headers"]

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)
        except:
            qt.exception_message(
                self.window(), f"There was an error loading the {self.TITLE}."
            )
        finally:
            self.setEnabled(True)

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, "xlsx")

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            qt.xlsx_start_file(self.window, fname)


class RoleSidebar(QtWidgets.QWidget):
    def __init__(self, parent=None, state=None):
        super(RoleSidebar, self).__init__(parent)

        self.client = None
        if state != None:
            self.client = state.session.std_client()
        self.backgrounder = apputils.Backgrounder(self)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.user_grid = widgets.TableView()
        self.user_gridmgr = qt.GridManager(self.user_grid, self)
        self.act_grid = widgets.TableView()
        self.act_gridmgr = qt.GridManager(self.act_grid, self)

        self.layout.addWidget(self.user_grid)
        self.layout.addWidget(self.act_grid)

        self.geo = apputils.WindowGeometry(self, grids=[self.user_grid, self.act_grid])

    def highlight(self, row):
        if row == None:
            self.act_grid.setModel(None)
            self.user_grid.setModel(None)
        else:
            self.backgrounder(
                self.load_activities,
                self.client.get,
                "api/activities/by-role",
                role=row.id,
            )
            self.backgrounder(
                self.load_users, self.client.get, "api/users/by-role", role=row.id
            )

    def load_users(self):
        try:
            content = yield
        except:
            qt.exception_message(self.window(), "Error loading users")
            return

        with self.geo.grid_reset(self.user_grid):
            self.users = content.main_table()
            self.user_gridmgr.set_client_table(self.users)

    def load_activities(self):
        try:
            content = yield
        except:
            qt.exception_message(self.window(), "Error loading activities")
            return

        with self.geo.grid_reset(self.act_grid):
            self.activities = content.main_table()
            self.act_gridmgr.set_client_table(self.activities)


class RoleList(QtWidgets.QWidget):
    ID = "administrative/roles"
    TITLE = "Role List"
    URL_TAIL = "api/roles/list"
    SRC_INSTANCE_URL = "api/role/{}"

    def __init__(self, parent=None, state=None):
        super(RoleList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = state.exports_dir
        self.client = state.session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setObjectName("content")
        self.grid.setSortingEnabled(True)
        self.gridmgr = qt.GridManager(self.grid, self)
        self.gridmgr.add_action("Add &New Role", triggered=self.cmd_add_new_role)
        self.gridmgr.add_action("&Rename Role", triggered=self.cmd_rename_role)
        self.gridmgr.add_action("&Delete Role", triggered=self.cmd_delete_role)
        self.gridmgr.add_action("Assigned &Users", triggered=self.cmd_assigned_users)
        self.gridmgr.add_action("Permitted &Actions", triggered=self.cmd_permit_actions)
        self.splitter.addWidget(self.grid)

        self.sidebar = RoleSidebar(self, state)
        self.splitter.addWidget(self.sidebar)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.splitter)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.gridmgr.current_row_update.connect(self.sidebar_update)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton("&Refresh", QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton("&Export", QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

        self.refresh()

    def sidebar_update(self):
        row = self.gridmgr.selected_row()
        self.sidebar.highlight(row)

    def cmd_add_new_role(self):
        content = self.client.get(self.SRC_INSTANCE_URL, "new")
        t = content.main_table()
        self._edit_role(t)

    def cmd_rename_role(self, row):
        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        t = content.main_table()
        self._edit_role(t)

    def cmd_delete_role(self, row):
        try:
            self.client.delete(self.SRC_INSTANCE_URL, row.id)
        except:
            qt.exception_message(self.window(), "The role could not be deleted.")

        self.refresh()

    def _edit_role(self, table):
        assert len(table.rows) == 1

        w = QtWidgets.QDialog(self.window())
        w.setWindowTitle("Edit Role")

        w.bind = bindings.Binder(w)

        layout = QtWidgets.QVBoxLayout(w)
        form = QtWidgets.QFormLayout()
        form.addRow("&Role Name:", w.bind.construct("role_name", "basic"))
        form.addRow("&Order", w.bind.construct("sort", "integer"))

        def save():
            files = {"role": table.as_http_post_file()}
            try:
                self.client.put(self.SRC_INSTANCE_URL, table.rows[0].id, files=files)
                w.accept()
            except:
                qt.exception_message(w, "There was an error adding the role.")

        QDB = QtWidgets.QDialogButtonBox
        buttons = QDB(QDB.Ok | QDB.Cancel, QtCore.Qt.Horizontal)
        layout.addLayout(form)
        layout.addWidget(buttons)
        buttons.accepted.connect(save)
        buttons.rejected.connect(w.reject)

        w.bind.bind(table.rows[0])

        w.exec_()

        self.refresh()

    def cmd_assigned_users(self, rows):
        roles = [o.id for o in rows]

        w = UserRoleMapperTargetsByRole(
            self.client.session, self.exports_dir, None, roles
        )
        w.show()

    def cmd_permit_actions(self, rows):
        roles = [o.id for o in rows]

        w = RoleActivityMapperTargets(
            self.client.session, self.exports_dir, None, roles
        )
        w.show()

    def load(self):
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys["headers"]

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)
        except:
            qt.exception_message(
                self.window(), f"There was an error loading the {self.TITLE}."
            )
        finally:
            self.setEnabled(True)

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, "xlsx")

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            qt.xlsx_start_file(self.window, fname)


class ActivitySidebar(QtWidgets.QWidget):
    def __init__(self, parent=None, state=None):
        super(ActivitySidebar, self).__init__(parent)

        self.client = None
        if state != None:
            self.client = state.session.std_client()
        self.backgrounder = apputils.Backgrounder(self)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.html = QtWidgets.QTextBrowser()
        # self.html.linkClicked.connect(gridmgr.show_link)
        self.layout.addWidget(self.html)

    def highlight(self, row):
        if row == None:
            self.html.setHtml("")
        else:
            self.backgrounder(
                self.load_sidebar, self.client, "api/report/{}/info", row.act_name
            )

    def load_sidebar(self):
        try:
            content = yield
        except Exception as e:
            self.html.setHtml(f"<html><body>Error:  {str(e)}</body></html>")
            return

        acttable = content.main_table()
        activity = acttable.rows[0]

        if activity.method:
            httpgunk = f"""{activity.method} {activity.url}"""
        else:
            httpgunk = "Not available"

        if activity.prompts is None:
            reportgunk = ""
        else:
            gui_url = f"rtx:report/{activity.act_name}?prompt1=value1"
            self.prompts = rtlib.PromptList(activity.prompts)

            cols = ["label", "attr", "type_"]
            table = rtlib.ClientTable([(c, None) for c in cols], [])
            table.rows = self.prompts

            reportgunk = """
<pre>
{}
</pre>
(See <a href="{}docs/rtxurls.html" target="_blank">Rtx URL docs</a> for more details.)


<h3>Prompts</h3>

{}
""".format(
                gui_url,
                self.client.session.server_url,
                table.as_html(border="1", cellspacing="0"),
            )

        html = f"""<html>
<body>
<h2>{activity.description}</h2>

{reportgunk}

<hr />

<h3>HTTP Access:</h3>

{httpgunk}

<hr />

<h3>Documentation Note:</h3>

{activity.note}

</body>
</html>"""
        self.html.setHtml(html)

        # self.html.page().setLinkDelegationPolicy(QtWebEngineWidgets.QWebEnginePage.DelegateAllLinks)


class ActivityList(QtWidgets.QWidget):
    ID = "administrative/activities"
    TITLE = "Activity List"
    URL_TAIL = "api/activities/list"
    SRC_INSTANCE_URL = "api/activity/{}"

    def __init__(self, parent=None, state=None):
        super(ActivityList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = state.exports_dir
        self.client = state.session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setObjectName("content")
        self.grid.setSortingEnabled(True)
        self.gridmgr = qt.GridManager(self.grid, self)
        self.gridmgr.add_action("Add &New Activity", triggered=self.cmd_addnew_activity)
        self.gridmgr.add_action("&Edit Activity", triggered=self.cmd_edit_activity)
        self.splitter.addWidget(self.grid)

        self.sidebar = ActivitySidebar(self, state)
        self.splitter.addWidget(self.sidebar)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.filter_edit = apputils.construct("search")
        self.setFocusProxy(self.filter_edit)

        self.layout.addWidget(self.filter_edit)
        self.layout.addWidget(self.splitter)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.refilter_list)
        self.filter_edit.applyValue.connect(self.load_timer.ui_start)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.gridmgr.current_row_update.connect(self.sidebar_update)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton("&Refresh", QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton("&Export", QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

        self.refresh()

    def sidebar_update(self):
        row = self.gridmgr.selected_row()
        self.sidebar.highlight(row)

    def cmd_addnew_activity(self):
        activity = rtlib.ClientTable(
            [("name", None), ("description", None), ("note", None)], []
        )
        activity.rows.append(activity.DataRow("", "", ""))
        edit_activity_dlg(self, activity)

    def cmd_edit_activity(self, row):
        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        t = content.main_table()
        edit_activity_dlg(self, t)

    def refilter_list(self):
        self.model.setFilterFixedString(self.filter_edit.text())

    def filterable_model(self, model):
        self._core_model = model
        m2 = QtCore.QSortFilterProxyModel()
        m2.setSourceModel(model)
        m2.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        m2.setFilterKeyColumn(0)
        m2.columns = model.columns
        return m2

    def load(self):
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys["headers"]

            with self.geo.grid_reset(self.grid):
                # TODO:  make an elegant way to filter on a GridManager
                m = qt.client_table_as_model(self.records, self)
                self.model = self.filterable_model(m)
                self.grid.setModel(self.model)
                self._core_model.set_rows(self.records.rows)
                self.gridmgr.table = self.records
                self.gridmgr._post_model_action()
        except:
            apputils.exception_message(
                self, f"There was an error loading the {self.TITLE}."
            )

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, "xlsx")

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            qt.xlsx_start_file(self.window, fname)


def edit_activity_dlg(parentwin, table):
    w = QtWidgets.QDialog(parentwin.window())
    w.setWindowTitle("Edit Activity")

    w.bind = bindings.Binder(w)
    layout = QtWidgets.QVBoxLayout(w)
    form = QtWidgets.QFormLayout()
    form.addRow("&Activity Name:", w.bind.construct("act_name", "basic"))
    form.addRow("&Description", w.bind.construct("description", "basic"))
    form.addRow("&Note", w.bind.construct("note", "multiline"))

    if hasattr(table.rows[0], "id"):
        w.bind.widgets["act_name"].setReadOnly(True)

    def save():
        files = {"activities": table.as_http_post_file()}
        try:
            parentwin.client.post("api/activities", files=files)
            w.accept()
        except:
            qt.exception_message(w, "There was an error adding the activity.")

    QDB = QtWidgets.QDialogButtonBox
    buttons = QDB(QDB.Ok | QDB.Cancel, QtCore.Qt.Horizontal)
    layout.addLayout(form)
    layout.addWidget(buttons)
    buttons.accepted.connect(save)
    buttons.rejected.connect(w.reject)

    w.bind.bind(table.rows[0])

    return w.Accepted == w.exec_()


def edit_user_dlg(parentwin, table, editrec):
    w = QtWidgets.QDialog(parentwin.window())
    w.setWindowTitle("Edit User Properties" if editrec else "Add New User")

    w.bind = bindings.Binder(w)
    layout = QtWidgets.QVBoxLayout(w)
    form = QtWidgets.QFormLayout()
    form.addRow("&Full Name", w.bind.construct("full_name", "basic"))
    form.addRow("&User Name", w.bind.construct("username", "basic"))
    if not editrec:
        form.addRow("&Password", w.bind.construct("password", "basic"))
        form.addRow("&Password (confirm)", w.bind.construct("password2", "basic"))
        w.bind.widgets["password"].setEchoMode(QtWidgets.QLineEdit.Password)
        w.bind.widgets["password2"].setEchoMode(QtWidgets.QLineEdit.Password)
    else:
        form.addRow("", w.bind.construct("inactive", "boolean", label="Inactive"))
    form.addRow("&Description", w.bind.construct("descr", "multiline"))

    def save():
        row = table.rows[0]
        if not editrec:
            if row.password != row.password2:
                apputils.information(w, "Password and confirm password do not match.")
                return False

        if editrec:
            files = {
                "user": table.as_http_post_file(
                    inclusions=["username", "full_name", "inactive", "descr"]
                )
            }
        else:
            files = {"user": table.as_http_post_file(exclusions=["password2"])}
        try:
            if editrec:
                parentwin.client.put(
                    parentwin.SRC_INSTANCE_URL, table.rows[0].id, files=files
                )
            else:
                parentwin.client.post("api/user", files=files)
            w.accept()
        except:
            qt.exception_message(w, "There was an error adding the user.")

    QDB = QtWidgets.QDialogButtonBox
    buttons = QDB(QDB.Ok | QDB.Cancel, QtCore.Qt.Horizontal)
    layout.addLayout(form)
    layout.addWidget(buttons)
    buttons.accepted.connect(save)
    buttons.rejected.connect(w.reject)

    w.bind.bind(table.rows[0])

    return w.Accepted == w.exec_()


class PidCancellerTab(ReportTabEx):
    def init_view2(self):
        self.action_cancel_backend = QtGui.QAction("&Cancel Backend", self)
        self.action_cancel_backend.triggered.connect(self.cancel_backend)
        self.ctxmenu.add_action(self.action_cancel_backend)

        self.reload_timer = QtCore.QTimer(self)
        self.reload_timer.timeout.connect(self.refresh)
        self.reload_timer.start(5000)

    def cancel_backend(self):
        obj = self.ctxmenu.active_index.data(models.ObjectRole)
        try:
            self.client.put("api/database/cancelbackend", pid=obj.pid)
        except:
            qt.exception_message(self.window(), "Canceling the backend failed.")
        self.refresh()

    def closeEvent(self, event):
        self.reload_timer.stop()
        self.reload_timer = None
        return super(PidCancellerTab, self).closeEvent(event)


class ConnectionList(PidCancellerTab):
    ID = "administrative/dbconnections"
    TITLE = "Current Database Connections"
    URL_TAIL = "api/database/connections"


class LockList(PidCancellerTab):
    ID = "administrative/dblocks"
    TITLE = "Current Database Locks"
    URL_TAIL = "api/database/locks"


SIMPLE_LISTS = [ConnectionList, LockList, UserList, SessionList, RoleList, ActivityList]

SIMPLE_LIST_MAP = {K.ID: K for K in SIMPLE_LISTS}

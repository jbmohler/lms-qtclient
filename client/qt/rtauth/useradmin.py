from PySide2 import QtCore, QtWidgets
import rtlib
import apputils
import apputils.models as models
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
from client.qt import utils
from client.qt import gridmgr
from client.qt import bindings
from client.qt import reporttab
from .useradmin_userroles import UserRoleMapperTargetsByUser
from .useradmin_userroles_selected_roles import UserRoleMapperTargetsByRole
from .useradmin_roleactivities import RoleActivityMapperTargets

class ReportTabEx(reporttab.ReportTab):
    def __init__(self, session, exports_dir, parent=None):
        super(ReportTabEx, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = exports_dir
        self.client = session.std_client()
        self.backgrounder = apputils.Backgrounder(self)
        self.ctxmenu = viewmenus.ContextMenu(self.grid, self)
        self.geo = apputils.WindowGeometry(self, size=False, position=False, grids=[self.grid])

        self.init_view2()

        self.refresh()

    def init_view2(self):
        pass


class SessionList(ReportTabEx):
    ID = 'administrative/sessions'
    TITLE = 'Active Session List'
    URL_TAIL = 'api/sessions/active'

class UserList(QtWidgets.QWidget):
    ID = 'administrative/users'
    TITLE = 'User List'
    URL_TAIL = 'api/users/list'
    SRC_INSTANCE_URL = 'api/user/{}'

    def __init__(self, session, exports_dir, parent=None):
        super(UserList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = exports_dir
        self.client = session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setObjectName('content')
        self.grid.setSortingEnabled(True)
        self.gridmgr = gridmgr.GridManager(self.grid, self)
        self.gridmgr.add_action('&Add User', triggered=self.cmd_add_user)
        self.gridmgr.add_action('&Set Roles', triggered=self.cmd_set_roles)
        self.gridmgr.add_action('&Edit User', triggered=self.cmd_edit_user)
        self.gridmgr.add_action('&Delete User', triggered=self.cmd_delete_user)
        self.splitter.addWidget(self.grid)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.splitter)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton('&Refresh', QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton('&Export', QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(self, size=False, position=False, grids=[self.grid])

        self.refresh()

    def cmd_add_user(self):
        user = rtlib.ClientTable([('full_name', None), ('username', None), ('password', None), ('password2', None), ('descr', None)], [])
        with user.adding_row() as r2:
            pass
        if edit_user_dlg(self, user, editrec=False):
            self.refresh()

    def cmd_edit_user(self, row):
        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        user = content.main_table()
        if edit_user_dlg(self, user, editrec=True):
            self.refresh()

    def cmd_set_roles(self, rows):
        users = [o.id for o in rows]

        w = UserRoleMapperTargetsByUser(self.client.session, self.exports_dir, None, users)
        w.show()
        self.refresh()

    def cmd_delete_user(self, row):
        if 'Yes' == apputils.message(self.window(), 'Are you sure that you wish to delete the user {}?'.format(row.username), buttons=['Yes', 'No']):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.id)
                self.refresh()
            except:
                utils.exception_message(self.window(), 'The user could not be deleted.')

    def load(self):
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys['headers']

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)
        except:
            apputils.exception_message(self, 'There was an error loading the {}.'.format(self.TITLE))
        finally:
            self.setEnabled(True)

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, 'xlsx')

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            utils.xlsx_start_file(self.window, fname)


class RoleSidebar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RoleSidebar, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.user_grid = widgets.TableView()
        self.user_gridmgr = gridmgr.GridManager(self.user_grid, self)
        self.act_grid = widgets.TableView()
        self.act_gridmgr = gridmgr.GridManager(self.act_grid, self)

        self.layout.addWidget(self.user_grid)
        self.layout.addWidget(self.act_grid)

        self.geo = apputils.WindowGeometry(self, grids=[self.user_grid, self.act_grid])

    def highlight(self, row):
        if row == None:
            self.act_grid.setModel(None)
            self.user_grid.setModel(None)
        else:
            self.backgrounder(self.load_activities, self.client.get, 'api/activities/by-role', role=row.id)
            self.backgrounder(self.load_users, self.client.get, 'api/users/by-role', role=row.id)

    def load_users(self):
        try:
            content = yield
        except:
            utils.exception_message(self.window(), 'Error loading users')
            return

        with self.geo.grid_reset(self.user_grid):
            self.users = content.main_table()
            self.user_gridmgr.set_client_table(self.users)

    def load_activities(self):
        try:
            content = yield
        except:
            utils.exception_message(self.window(), 'Error loading activities')
            return

        with self.geo.grid_reset(self.act_grid):
            self.activities = content.main_table()
            self.act_gridmgr.set_client_table(self.activities)

class RoleList(QtWidgets.QWidget):
    ID = 'administrative/roles'
    TITLE = 'Role List'
    URL_TAIL = 'api/roles/list'
    SRC_INSTANCE_URL = 'api/role/{}'

    def __init__(self, session, exports_dir, parent=None):
        super(RoleList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = exports_dir
        self.client = session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setObjectName('content')
        self.grid.setSortingEnabled(True)
        self.gridmgr = gridmgr.GridManager(self.grid, self)
        self.gridmgr.add_action('Add &New Role', triggered=self.cmd_add_new_role)
        self.gridmgr.add_action('&Rename Role', triggered=self.cmd_rename_role)
        self.gridmgr.add_action('&Delete Role', triggered=self.cmd_delete_role)
        self.gridmgr.add_action('Assigned &Users', triggered=self.cmd_assigned_users)
        self.gridmgr.add_action('Permitted &Actions', triggered=self.cmd_permit_actions)
        self.splitter.addWidget(self.grid)

        self.sidebar = RoleSidebar()
        self.splitter.addWidget(self.sidebar)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.splitter)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.gridmgr.current_row_update.connect(self.sidebar_update)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton('&Refresh', QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton('&Export', QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(self, size=False, position=False, grids=[self.grid])

        self.refresh()

    def sidebar_update(self):
        row = self.gridmgr.selected_row()
        self.sidebar.highlight(row)

    def cmd_add_new_role(self):
        content = self.client.get(self.SRC_INSTANCE_URL, 'new')
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
            utils.exception_message(self.window(), 'The role could not be deleted.')

        self.refresh()

    def _edit_role(self, table):
        assert len(table.rows) == 1

        w = QtWidgets.QDialog(self.window())
        w.setWindowTitle('Edit Role')

        w.bind = bindings.Binder(w)

        layout = QtWidgets.QVBoxLayout(w)
        form = QtWidgets.QFormLayout()
        form.addRow('&Role Name:', w.bind.construct('role_name', 'basic'))
        form.addRow('&Order', w.bind.construct('sort', 'integer'))

        def save():
            files = {'role': table.as_http_post_file()}
            try:
                self.client.put(self.SRC_INSTANCE_URL, table.rows[0].id, files=files)
                w.accept()
            except:
                utils.exception_message(w, 'There was an error adding the role.')

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

        w = UserRoleMapperTargetsByRole(self.client.session, self.exports_dir, None, roles)
        w.show()

    def cmd_permit_actions(self, rows):
        roles = [o.id for o in rows]

        w = RoleActivityMapperTargets(self.client.session, self.exports_dir, None, roles)
        w.show()

    def load(self):
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys['headers']

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)
        except:
            apputils.exception_message(self, 'There was an error loading the {}.'.format(self.TITLE))
        finally:
            self.setEnabled(True)

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, 'xlsx')

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            utils.xlsx_start_file(self.window, fname)


class ActivitySidebar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ActivitySidebar, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.html = QtWidgets.QTextBrowser()
        #self.html.linkClicked.connect(gridmgr.show_link)
        self.layout.addWidget(self.html)

    def highlight(self, row):
        if row == None:
            self.html.setHtml('')
        else:
            self.backgrounder(self.load_sidebar, self.client, 'api/report/{}/info', row.act_name)

    def load_sidebar(self):
        try:
            content = yield
        except Exception as e:
            self.html.setHtml('<html><body>Error:  {}</body></html>'.format(str(e)))
            return

        acttable = content.main_table()
        activity = acttable.rows[0]

        if 'prompts' not in content[0]:
            reportgunk = ''
        else:
            gui_url = 'rtx:report/{}?prompt1=value1'.format(content[0]['name'])
            self.prompts = rtlib.PromptList(content[0]['prompts'])

            cols = ['label', 'attr', 'type_']
            table = rtlib.ClientTable([(c, None) for c in cols], [])
            table.rows = self.prompts

            reportgunk = """
<pre>
{}
</pre>
(See <a href="{}docs/rtxurls.html" target="_blank">Rtx URL docs</a> for more details.)


<h3>Prompts</h3>

{}
""".format(gui_url, self.client.session.server_url, table.as_html(border='1', cellspacing='0'))

        html = """\
<html>
<body>
<h2>{}</h2>

{}

<hr />

<h3>Documentation Note:</h3>

{}

</body>
</html>""".format(activity.description, reportgunk, activity.note)
        self.html.setHtml(html)

        self.html.page().setLinkDelegationPolicy(QtWebEngineWidgets.QWebEnginePage.DelegateAllLinks)

class ActivityList(QtWidgets.QWidget):
    ID = 'administrative/activities'
    TITLE = 'Activity List'
    URL_TAIL = 'api/activities/list'
    SRC_INSTANCE_URL = 'api/activity/{}'

    def __init__(self, session, exports_dir, parent=None):
        super(ActivityList, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        self.exports_dir = exports_dir
        self.client = session.std_client()

        self.backgrounder = apputils.Backgrounder(self)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setObjectName('content')
        self.grid.setSortingEnabled(True)
        self.gridmgr = gridmgr.GridManager(self.grid, self)
        self.gridmgr.add_action('Add &New Activity', triggered=self.cmd_addnew_activity)
        self.gridmgr.add_action('&Edit Activity', triggered=self.cmd_edit_activity)
        self.splitter.addWidget(self.grid)

        self.sidebar = ActivitySidebar()
        self.splitter.addWidget(self.sidebar)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.filter_gizmo = QtWidgets.QHBoxLayout()
        self.filter_edit = widgets.SearchEdit()
        self.filter_edit.editingFinished.connect(self.refilter_list)
        self.filter_gizmo.addWidget(self.filter_edit)
        self.layout.addLayout(self.filter_gizmo)
        self.layout.addWidget(self.splitter)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.gridmgr.current_row_update.connect(self.sidebar_update)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton('&Refresh', QDB.ApplyRole).clicked.connect(self.refresh)
        self.buttons.addButton('&Export', QDB.ApplyRole).clicked.connect(self.export)
        self.layout.addWidget(self.buttons)

        self.geo = apputils.WindowGeometry(self, size=False, position=False, grids=[self.grid])

        self.refresh()

    def sidebar_update(self):
        row = self.gridmgr.selected_row()
        self.sidebar.highlight(row)

    def cmd_addnew_activity(self):
        activity = rtlib.ClientTable([('name', None), ('description', None), ('note', None)], [])
        activity.rows.append(activity.DataRow('', '', ''))
        edit_activity_dlg(self, activity)

    def cmd_edit_activity(self):
        row = self.ctxmenu.active_index.data(models.ObjectRole)

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
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys['headers']

            with self.geo.grid_reset(self.grid):
                # TODO:  make an elegant way to filter on a GridManager
                m = gridmgr.client_table_as_model(self.records, self)
                self.model = self.filterable_model(m)
                self.grid.setModel(self.model)
                self._core_model.set_rows(self.records.rows)
                self.gridmgr.table = self.records
                self.gridmgr._post_model_action()
        except:
            apputils.exception_message(self, 'There was an error loading the {}.'.format(self.TITLE))
        finally:
            self.setEnabled(True)

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, 'xlsx')

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            utils.xlsx_start_file(self.window, fname)

def edit_activity_dlg(parentwin, table):
    w = QtWidgets.QDialog(parentwin.window())
    w.setWindowTitle('Edit Activity')

    w.bind = bindings.Binder(w)
    layout = QtWidgets.QVBoxLayout(w)
    form = QtWidgets.QFormLayout()
    form.addRow('&Activity Name:', w.bind.construct('act_name', 'basic'))
    form.addRow('&Description', w.bind.construct('description', 'basic'))
    form.addRow('&Note', w.bind.construct('note', 'memo'))

    if hasattr(table.rows[0], 'id'):
        w.bind.widgets['act_name'].setReadOnly(True)

    def save():
        files = {'activities': table.as_http_post_file()}
        try:
            parentwin.client.put('api/activities', files=files)
            w.accept()
        except:
            utils.exception_message(w, 'There was an error adding the activity.')

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
    w.setWindowTitle('Edit User Properties' if editrec else 'Add New User')

    w.bind = bindings.Binder(w)
    layout = QtWidgets.QVBoxLayout(w)
    form = QtWidgets.QFormLayout()
    form.addRow('&Full Name', w.bind.construct('full_name', 'basic'))
    form.addRow('&User Name', w.bind.construct('username', 'basic'))
    if not editrec:
        form.addRow('&Password', w.bind.construct('password', 'basic'))
        form.addRow('&Password (confirm)', w.bind.construct('password2', 'basic'))
        w.bind.widgets['password'].setEchoMode(QtWidgets.QLineEdit.Password)
        w.bind.widgets['password2'].setEchoMode(QtWidgets.QLineEdit.Password)
    else:
        form.addRow('', w.bind.construct('inactive', 'boolean', label='Inactive'))
    form.addRow('&Description', w.bind.construct('descr', 'multiline'))

    def save():
        row = table.rows[0]
        if not editrec:
            if row.password != row.password2:
                apputils.information(w, 'Password and confirm password do not match.')
                return False

        if editrec:
            files = {'user': table.as_http_post_file(inclusions=['username', 'full_name', 'inactive', 'descr'])}
        else:
            files = {'user': table.as_http_post_file(exclusions=['password2'])}
        try:
            if editrec:
                parentwin.client.put(parentwin.SRC_INSTANCE_URL, table.rows[0].id, files=files)
            else:
                parentwin.client.post('api/user', files=files)
            w.accept()
        except:
            utils.exception_message(w, 'There was an error adding the user.')

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
        self.action_cancel_backend = QtWidgets.QAction('&Cancel Backend', self)
        self.action_cancel_backend.triggered.connect(self.cancel_backend)
        self.ctxmenu.add_action(self.action_cancel_backend)

        self.reload_timer = QtCore.QTimer(self)
        self.reload_timer.timeout.connect(self.refresh)
        self.reload_timer.start(5000)

    def cancel_backend(self):
        obj = self.ctxmenu.active_index.data(models.ObjectRole)
        try:
            self.client.put('api/database/cancelbackend', pid=obj.pid)
        except:
            utils.exception_message(self.window(), 'Canceling the backend failed.')
        self.refresh()

    def closeEvent(self, event):
        self.reload_timer.stop()
        self.reload_timer = None
        return super(PidCancellerTab, self).closeEvent(event)

class ConnectionList(PidCancellerTab):
    ID = 'administrative/dbconnections'
    TITLE = 'Current Database Connections'
    URL_TAIL = 'api/database/connections'

class LockList(PidCancellerTab):
    ID = 'administrative/dblocks'
    TITLE = 'Current Database Locks'
    URL_TAIL = 'api/database/locks'


SIMPLE_LISTS = [ \
        ConnectionList,
        LockList, 
        UserList, 
        SessionList, 
        RoleList,
        ActivityList]

SIMPLE_LIST_MAP = {K.ID: K for K in SIMPLE_LISTS}

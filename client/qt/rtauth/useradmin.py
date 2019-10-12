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

class UserList(ReportTabEx):
    ID = 'administrative/users'
    TITLE = 'User List'
    URL_TAIL = 'api/users/list'

    def init_view2(self):
        self.action_set_roles = QtWidgets.QAction('&Set Roles', self)
        self.action_set_roles.triggered.connect(self.show_set_roles)
        self.ctxmenu.add_action(self.action_set_roles)

    def show_set_roles(self):
        objects = {}
        for index in self.ctxmenu.selected_indexes():
            objects[index.row()] = index.data(models.ObjectRole)
        users = [o.id for o in objects.values()]

        w = UserRoleMapperTargetsByUser(self.client.session, self.exports_dir, None, users)
        w.show()


class RoleSidebar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(RoleSidebar, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.user_grid = widgets.TableView()
        self.act_grid = widgets.TableView()

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
            self.user_grid.setModel(gridmgr.client_table_as_model(self.users, self))

    def load_activities(self):
        try:
            content = yield
        except:
            utils.exception_message(self.window(), 'Error loading activities')
            return

        with self.geo.grid_reset(self.act_grid):
            self.activities = content.main_table()
            self.act_grid.setModel(gridmgr.client_table_as_model(self.activities, self))

class RoleList(ReportTabEx):
    ID = 'administrative/roles'
    TITLE = 'Role List'
    URL_TAIL = 'api/roles/list'
    SRC_INSTANCE_URL = 'api/role/{}'

    def init_view(self):
        super(RoleList, self).init_view()
        self.sidebar = RoleSidebar()
        self.splitter.addWidget(self.sidebar)

        self.geo = apputils.WindowGeometry(self, size=False, position=False, splitters=[self.splitter])

    def init_view2(self):
        self.action_new_role = QtWidgets.QAction('Add &New Role', self)
        self.action_new_role.triggered.connect(self.add_new_role)
        self.ctxmenu.add_action(self.action_new_role)

        self.action_rename_role = QtWidgets.QAction('&Rename Role', self)
        self.action_rename_role.triggered.connect(self.rename_role)
        self.ctxmenu.add_action(self.action_rename_role)

        self.action_delete_role = QtWidgets.QAction('&Delete Role', self)
        self.action_delete_role.triggered.connect(self.delete_role)
        self.ctxmenu.add_action(self.action_delete_role)

        self.action_assigned_users = QtWidgets.QAction('Assigned &Users', self)
        self.action_assigned_users.triggered.connect(self.show_assigned_users)
        self.ctxmenu.add_action(self.action_assigned_users)

        self.action_permit_actions = QtWidgets.QAction('Permitted &Actions', self)
        self.action_permit_actions.triggered.connect(self.show_permit_actions)
        self.ctxmenu.add_action(self.action_permit_actions)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.ctxmenu.current_row_update.connect(self.sidebar_update)

    def sidebar_update(self):
        obj = self.ctxmenu.active_index.data(models.ObjectRole) if self.ctxmenu.active_index != None else None
        self.sidebar.highlight(obj)

    def delete_role(self):
        row = self.ctxmenu.active_index.data(models.ObjectRole)
        try:
            self.client.delete(self.SRC_INSTANCE_URL, row.id)
        except:
            utils.exception_message(self.window(), 'The role could not be deleted.')

        self.refresh()

    def rename_role(self):
        row = self.ctxmenu.active_index.data(models.ObjectRole)

        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        t = content.main_table()
        self.edit_role(t)

    def add_new_role(self):
        content = self.client.get(self.SRC_INSTANCE_URL, 'new')
        t = content.main_table()
        self.edit_role(t)

    def edit_role(self, table):
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

    def show_assigned_users(self):
        objects = {}
        for index in self.ctxmenu.selected_indexes():
            objects[index.row()] = index.data(models.ObjectRole)
        roles = [o.id for o in objects.values()]

        w = UserRoleMapperTargetsByRole(self.client.session, self.exports_dir, None, roles)
        w.show()

    def show_permit_actions(self):
        objects = {}
        for index in self.ctxmenu.selected_indexes():
            objects[index.row()] = index.data(models.ObjectRole)
        roles = [o.id for o in objects.values()]

        w = RoleActivityMapperTargets(self.client.session, self.exports_dir, None, roles)
        w.show()


class ActivitySidebar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ActivitySidebar, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.html = QtWidgets.QTextBrowser()
        #self.html.linkClicked.connect(gridmgr.show_link)
        self.layout.addWidget(self.html)

    def highlight(self, row):
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


class ActivityList(ReportTabEx):
    ID = 'administrative/activities'
    TITLE = 'Activity List'
    URL_TAIL = 'api/activities/list'
    SRC_INSTANCE_URL = 'api/activity/{}'

    def init_view(self):
        self.filter_gizmo = QtWidgets.QHBoxLayout()
        self.filter_edit = widgets.SearchEdit()
        self.filter_edit.editingFinished.connect(self.refilter_list)
        self.filter_gizmo.addWidget(self.filter_edit)
        self.layout.insertLayout(0, self.filter_gizmo)

        self.sidebar = ActivitySidebar()
        self.splitter.addWidget(self.sidebar)

        self.geo = apputils.WindowGeometry(self, splitters=[self.splitter])

    def refilter_list(self):
        self.model.setFilterFixedString(self.filter_edit.text())

    def filterable_model(self, model):
        self._core_model = model
        m2 = QtCore.QSortFilterProxyModel()
        m2.setSourceModel(model)
        m2.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        m2.setFilterKeyColumn(0)
        return m2

    def init_view2(self):
        self.action_new_activity = QtWidgets.QAction('Add &New Activity', self)
        self.action_new_activity.triggered.connect(self.addnew_activity)
        self.ctxmenu.add_action(self.action_new_activity)

        self.action_edit_activity = QtWidgets.QAction('&Edit Activity', self)
        self.action_edit_activity.triggered.connect(self.edit_activity)
        self.ctxmenu.add_action(self.action_edit_activity)

        self.sidebar.backgrounder = self.backgrounder
        self.sidebar.client = self.client
        self.ctxmenu.current_row_update.connect(self.sidebar_update)

    def sidebar_update(self):
        obj = self.ctxmenu.active_index.data(models.ObjectRole) if self.ctxmenu.active_index != None else None
        self.sidebar.highlight(obj)

    def addnew_activity(self):
        activity = rtlib.ClientTable([('name', None), ('description', None), ('note', None)], [])
        activity.rows.append(activity.DataRow('', '', ''))
        edit_activity_dlg(self, activity)

    def edit_activity(self):
        row = self.ctxmenu.active_index.data(models.ObjectRole)

        content = self.client.get(self.SRC_INSTANCE_URL, row.id)
        t = content.main_table()
        edit_activity_dlg(self, t)

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

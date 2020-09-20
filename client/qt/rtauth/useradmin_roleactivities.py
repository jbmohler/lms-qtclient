from PySide2 import QtCore, QtWidgets
import apputils
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
import apputils.models as models
from client.qt import winlist
from client.qt import valqt
from client.qt import gridmgr


def perm_meta_formatter(value):
    if value.get('dashboard', False):
        return 'On dashboard'
    else:
        return ''

class RoleActivityMapperRowMixin:
    tracker = None

    def get_by_roleaid(self, role_aid):
        # implemented 'sub-scripted' attribute
        roles = {x['roleid']: x for x in self.permissions}
        return roles.get(role_aid, {'roleid': role_aid})

    def set_by_roleaid(self, role_aid, value):
        # implemented 'sub-scripted' attribute
        for index, x in enumerate(self.permissions):
            if x['roleid'] == role_aid:
                self.permissions[index] = value
                self.permissions[index]['roleid'] = role_aid
                break
        else:
            n = {'roleid': role_aid}
            self.permissions.append(n)

    def get_by_roleaid_permitted(self, role_aid):
        # implemented 'sub-scripted' attribute
        roles = {x['roleid']: x for x in self.permissions}
        return roles.get(role_aid, {}).get('permitted', False)

    def set_by_roleaid_permitted(self, role_aid, value):
        # implemented 'sub-scripted' attribute
        roles = {x['roleid']: x for x in self.permissions}
        if role_aid not in roles:
            n = {'roleid': role_aid}
            roles[role_aid] = n
            self.permissions.append(n)
        roles[role_aid]['permitted'] = value

    def __setattr__(self, attr, value):
        self.tracker.set_dirty(self, attr)
        super(RoleActivityMapperRowMixin, self).__setattr__(attr, value)

class RoleIndexer(object):
    def __init__(self, role_aid):
        self.role_aid = role_aid

    def __get__(self, obj, objtype):
        return obj.get_by_roleaid(self.role_aid)

    def __set__(self, obj, value):
        obj.set_by_roleaid(self.role_aid, value)

class RoleIndexerPermitted(object):
    def __init__(self, role_aid):
        self.role_aid = role_aid

    def __get__(self, obj, objtype):
        return obj.get_by_roleaid_permitted(self.role_aid)

    def __set__(self, obj, value):
        obj.set_by_roleaid_permitted(self.role_aid, value)

class RoleActivityMapperLineTracker(valqt.SaveButtonDocumentTracker):
    def set_dirty(self, row, attr):
        if not self.load_lockout:
            if not hasattr(self, '_mods'):
                self._mods = set()
            self._mods.add(row)
        super(RoleActivityMapperLineTracker, self).set_dirty(row, attr)

    @property
    def modified(self):
        if hasattr(self, '_mods'):
            return self._mods
        else:
            return []

class RoleActivityMapperTargets(QtWidgets.QMainWindow):
    ID = 'admin_roleactivity_mapper'
    TITLE = 'Set Activities for Roles'
    SRC_URL = 'api/roleactivities/by-roles'

    def __init__(self, session, exports_dir, parent=None, roles=None):
        super(RoleActivityMapperTargets, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)
        winlist.register(self, self.ID)

        self.role_universe = list(roles)

        self.center = QtWidgets.QWidget()
        self.setCentralWidget(self.center)
        self.layout = QtWidgets.QVBoxLayout(self.center)
        self.grid = widgets.EditableTableView()
        self.grid.setObjectName('content')
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

        self.grid.doubleClicked.connect(self.edit_perm_meta)

        self.tracker = RoleActivityMapperLineTracker(self.btn_save, self.save_targets)
        self.reset()

        self.geo = apputils.WindowGeometry(self, size=True, position=False, grids=[self.grid])

    def reset(self):
        if not self.tracker.save(asksave=True):
            return

        self.model = None
        self.backgrounder(self.load, self.client.get, self.SRC_URL, roles=','.join(self.role_universe))

    def load(self):
        self.setEnabled(False)
        try:
            content = yield

            fred = {'tracker': self.tracker}
            for u in self.role_universe:
                fred[f'meta_{u}'] = RoleIndexer(u)
                fred[f'permitted_{u}'] = RoleIndexerPermitted(u)
            self.MyRoleActivityMapperRowMixin = type('MyRoleActivityMapperRowMixin', (RoleActivityMapperRowMixin,), fred)

            with self.tracker.loading():
                self.records = content.main_table(mixin=self.MyRoleActivityMapperRowMixin)
                self.roles = content.named_table('rolenames')
                # self.roles.rows.sort(key=lambda x: x.order)

                for row in self.records.rows:
                    if row.permissions == None:
                        row.permissions = []

            columns = [c for c in self.records.columns if c.attr in ['act_name', 'description']]
            for u in self.roles.rows:
                a1 = f'meta_{u.id}'
                a2 = f'permitted_{u.id}'
                columns.append(apputils.field(a1, u.role_name.replace(' ', '\n', 2), formatter=perm_meta_formatter, check_attr=a2))
            self.model = apputils.ObjectQtModel(columns=columns)

            with self.geo.grid_reset(self.grid):
                self.grid.setModel(self.model)
                self.model.set_rows(self.records.rows)
            self.tracker.reset_dirty()

            self.ctxmenu.update_model()
            self.ctxmenu.reset_action_list()
            gridmgr.apply_column_url_views(self.ctxmenu, self.grid.model())

            self.setEnabled(True)
        except:
            apputils.exception_message(self, f'There was an error loading {self.TITLE}.')

    def save_targets(self):
        try:
            tosend = self.records.duplicate(rows=list(self.tracker.modified))
            data = {'roles': ','.join(self.role_universe)}
            files = {'roleactivities': tosend.as_http_post_file(exclusions=['act_name', 'description'])}

            self.client.put(self.SRC_URL, data=data, files=files)
        except Exception:
            apputils.exception_message(self.window(), f'Error saving {self.TITLE}.')
            raise

    def edit_perm_meta(self, index):
        c = self.model.columns[index.column()]
        if c.attr.startswith('meta_'):
            row = index.data(models.ObjectRole)
            value = getattr(row, c.attr)

            value['dashboard'] = not value.get('dashboard', False)
            setattr(row, c.attr, value)

    def closeEvent(self, event):
        if not self.tracker.save(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(RoleActivityMapperTargets, self).closeEvent(event)

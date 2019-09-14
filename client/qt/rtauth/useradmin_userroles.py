from QtShim import QtCore, QtWidgets
import rtlib
import apputils
import apputils.viewmenus as viewmenus
import apputils.widgets as widgets
from client.qt import valqt
from client.qt import winlist
from client.qt import gridmgr

class UserRoleMapperRowMixin:
    tracker = None
    def get_by_useraid(self, user_aid):
        # implemented 'sub-scripted' attribute
        return user_aid in self.user_list

    def set_by_useraid(self, user_aid, value):
        # implemented 'sub-scripted' attribute
        if value and not user_aid in self.user_list:
            self.user_list.append(user_aid)
        elif not value and user_aid in self.user_list:
            self.user_list.remove(user_aid)

    def __setattr__(self, attr, value):
        self.tracker.set_dirty(self, attr)
        super(UserRoleMapperRowMixin, self).__setattr__(attr, value)

class UserIndexer(object):
    def __init__(self, user_aid):
        self.user_aid = user_aid

    def __get__(self, obj, objtype):
        return obj.get_by_useraid(self.user_aid)

    def __set__(self, obj, value):
        obj.set_by_useraid(self.user_aid, value)

class UserRoleMapperLineTracker(valqt.SaveButtonDocumentTracker):
    def set_dirty(self, row, attr):
        if not self.load_lockout:
            if not hasattr(self, '_mods'):
                self._mods = set()
            self._mods.add(row)
        super(UserRoleMapperLineTracker, self).set_dirty(row, attr)

    @property
    def modified(self):
        if hasattr(self, '_mods'):
            return self._mods
        else:
            return []

class UserRoleMapperTargetsByUser(QtWidgets.QMainWindow):
    ID = 'admin_userrole_mapper'
    TITLE = 'Set User Roles'
    SRC_URL = 'api/userroles/by-users'

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

        self.tracker = UserRoleMapperLineTracker(self.btn_save, self.save_targets)
        self.reset()

        self.geo = apputils.WindowGeometry(self, size=True, position=False, grids=[self.grid])

    def reset(self):
        if not self.tracker.save(asksave=True):
            return

        self.model = None
        self.backgrounder(self.load, self.client.get, self.SRC_URL, users=','.join(self.user_universe))

    def load(self):
        self.setEnabled(False)
        try:
            content = yield

            fred = {'tracker': self.tracker}
            for u in self.user_universe:
                fred['user_{}'.format(u)] = UserIndexer(u)
            self.MyUserRoleMapperRowMixin = type('MyUserRoleMapperRowMixin', (UserRoleMapperRowMixin,), fred)

            with self.tracker.loading():
                self.records = content.main_table(mixin=self.MyUserRoleMapperRowMixin)
                self.users = content.named_table('usernames')
                self.users.rows.sort(key=lambda x: x.username)

                for row in self.records.rows:
                    if row.user_list == None:
                        row.user_list = []

            columns = [c for c in self.records.columns if c.attr in ['username']]
            for u in self.users.rows:
                columns.append(apputils.field('user_{}'.format(u.id), u.username, type_='boolean', checkbox=True, editable=True))
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
            apputils.exception_message(self, 'There was an error loading {}.'.format(self.TITLE))

    def save_targets(self):
        try:
            tosend = self.records.duplicate(rows=self.tracker.modified)
            data = {'users': ','.join(self.user_universe)}
            files = {'userroles': tosend.as_http_post_file(exclusions=['username'])}

            self.client.put(self.SRC_URL, data=data, files=files)
        except Exception:
            apputils.exception_message(self.window(), 'Error saving {}.'.format(self.TITLE))
            raise

    def closeEvent(self, event):
        if not self.tracker.save(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(UserRoleMapperTargetsByUser, self).closeEvent(event)


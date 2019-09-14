import uuid
from QtShim import QtCore, QtWidgets
import rtlib
import apputils
import apputils.widgets as widgets
import apputils.viewmenus as viewmenus
from client.qt import winlist
from client.qt import valqt
from client.qt import gridmgr

def attr_2_label(attr):
    if attr == None:
        return ''
    if attr.startswith('api_'):
        attr = attr[4:]
    if attr.startswith('put_api_'):
        attr = attr[8:]
    if attr.startswith('delete_'):
        attr = attr[7:]
    if attr.startswith('post_api_'):
        attr = attr[9:]
    return attr.replace('_', ' ').title()

class ActivitiesEditing:
    # TODO: write the setattr with tracker notify!

    @classmethod
    def from_unregistered(kls, row):
        self = kls()
        self.id = uuid.uuid1().hex
        self.act_name = row.act_name
        self.description = row.description if row.description not in ['', None] else attr_2_label(row.act_name)
        self.url = row.url
        self.save = row.act_name not in ['', None]
        return self

class ManageActivities(QtWidgets.QMainWindow):
    ID = 'admin_write_activities'
    TITLE = 'Manage Activities List'
    SRC_URL = 'api/activities'

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
        self.grid.setObjectName('content')
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
        self.tracker = valqt.SaveButtonDocumentTracker(self.btn_save, self.save_activities)

        self.geo = apputils.WindowGeometry(self, size=True, position=False, grids=[self.grid])

        if unregistered:
            self.backgrounder(self.load_unregistered, self.client.get, 'api/endpoints', unregistered=True)

    def load_unregistered(self):
        self.center.setEnabled(False)
        try:
            content = yield
            loaded = content.main_table()

            columns = [ \
                    ('id', {'type': 'x_data'}),
                    ('description', {'check_attr': 'save', 'editable': True}),
                    ('act_name', None),
                    ('url', None)]

            self.records = rtlib.ClientTable(columns, [], mixin=ActivitiesEditing)

            for row in loaded.rows:
                self.records.rows.append(self.records.DataRow.from_unregistered(row))

            with self.geo.grid_reset(self.grid):
                self.gridmgr.set_client_table(self.records)

            self.center.setEnabled(True)
        except:
            apputils.exception_message(self, 'There was an error loading {}.'.format(self.TITLE))

    def save_activities(self):
        try:
            tosend = self.records.duplicate(rows=[r for r in self.records.rows if r.save])
            files = {'activities': tosend.as_http_post_file()}

            self.client.put(self.SRC_URL, files=files)
        except Exception:
            apputils.exception_message(self.window(), 'Error saving {}.'.format(self.TITLE))
            raise

    def closeEvent(self, event):
        if not self.tracker.save(asksave=True):
            event.ignore()
            return
        winlist.unregister(self)
        return super(ManageActivities, self).closeEvent(event)

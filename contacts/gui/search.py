from PySide2 import QtWidgets
import client.qt as qt
import apputils
import apputils.widgets as widgets

class ContactsList(QtWidgets.QWidget):
    TITLE = 'Contacts'
    ID = 'contact-search'
    URL_SEARCH = 'api/personas/list'

    def __init__(self, parent, session):
        super(ContactsList, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.search_edit = apputils.construct('search')
        self.layout.addWidget(self.search_edit)

        self.grid = widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)
        self.layout.addWidget(self.grid)

        self.client = session.std_client()

        self.search_edit.applyValue.connect(self.search_now)

    def search_now(self):
        self.backgrounder(self.load_data, self.client.get, self.URL_SEARCH,
                frag=self.search_edit.value())

    def load_data(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        self.gridmgr.set_client_table(self.table)

def list_widget(parent, session):
    view = ContactsList(parent, session)
    return view

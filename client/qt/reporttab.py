from PySide2 import QtCore, QtWidgets
import rtlib
import apputils
import apputils.widgets as widgets
from . import utils
from . import gridmgr

class ReportTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ReportTab, self).__init__(parent)

        self.grid = widgets.TableView()
        self.grid.setObjectName('content')

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.grid)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.splitter)
        self.grid.setSortingEnabled(True)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton('&Refresh', QDB.ApplyRole).clicked.connect(self.refresh)
        self.export_button = self.buttons.addButton('&Export', QDB.ApplyRole)

        self.export_menu = QtWidgets.QMenu(self)
        self.export_menu.aboutToShow.connect(self.fill_export_menu)
        self.export_button.setMenu(self.export_menu)

        self.layout.addWidget(self.buttons)

        self.init_view()

    def fill_export_menu(self):
        self.export_menu.addAction(self.action_full_report)
        self.export_menu.addSeparator()
        self.export_menu.addAction(self.action_custom)

    def init_view(self):
        self.action_custom = QtWidgets.QAction('&Customize', self)
        self.action_custom.triggered.connect(lambda: utils.to_be_implemented(self.window(), 'Show options for inserting page breaks & filtering rows & columns.'))
        self.action_full_report = QtWidgets.QAction('&All', self)
        self.action_full_report.triggered.connect(self.export)
        self.export_button.clicked.connect(self.export)

    def filterable_model(self, model):
        self._core_model = model
        return model

    def load(self):
        self.setEnabled(False)
        try:
            content = yield
            self.records = content.main_table()
            self.headers = content.keys['headers']

            self.model = self.filterable_model(gridmgr.client_table_as_model(self.records, self))

            with self.geo.grid_reset(self.grid):
                self.grid.setModel(self.model)

            self.ctxmenu.update_model()
            gridmgr.apply_column_url_views(self.ctxmenu, self._core_model)

            self.setEnabled(True)
        except:
            apputils.exception_message(self, f'There was an error loading the {self.TITLE}.')

    def refresh(self):
        self.backgrounder(self.load, self.client.get, self.URL_TAIL)

    def export(self, options=None):
        fname = self.exports_dir.user_output_filename(self.TITLE, 'xlsx')

        if fname != None:
            rtlib.server.export_view(fname, self.grid, self.headers, options=options)
            utils.xlsx_start_file(self.window, fname)

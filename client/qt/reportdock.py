import itertools
import requests
from PySide6 import QtCore, QtGui, QtWidgets
import rtlib
import apputils
import apputils.widgets as widgets
import apputils.models as models
import apputils.viewmenus as viewmenus
from . import utils
from . import icons


class RoleReportHeader:
    def __init__(self, role, inners):
        self.role = role
        self.inners = list(inners)

    @property
    def description(self):
        return self.role

    @property
    def model_children(self):
        return self.inners


class BranchedFilterProxyModel(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow(self, sourceRow, sourceParent):
        if sourceParent.isValid():
            # only one layer deep
            return QtCore.QSortFilterProxyModel.filterAcceptsRow(
                self, sourceRow, sourceParent
            )
        else:
            # check children, include parent if including me
            p = self.sourceModel().index(sourceRow, 0, sourceParent)
            for row in range(self.sourceModel().rowCount(p)):
                if QtCore.QSortFilterProxyModel.filterAcceptsRow(self, row, p):
                    return True
            return False


class ReportsDock(QtWidgets.QWidget):
    ID = "reports_dock"
    TITLE = "Reports"

    def __init__(self, session, exports_dir, parent=None):
        super(ReportsDock, self).__init__(parent)

        # 1) Init window
        self.setWindowTitle(self.TITLE)
        self.setWindowIcon(QtWidgets.QApplication.instance().icon)
        self.setObjectName(self.ID)

        # 2) Init connections
        self.client = session.std_client()
        self.exports_dir = exports_dir
        self.backgrounder = apputils.Backgrounder(self)

        # 3) Make widgets
        self.action_refresh_list = QtGui.QAction("Refresh", self)
        self.action_refresh_list.setIcon(QtGui.QIcon(":/clientshell/view-refresh.png"))
        self.action_refresh_list.triggered.connect(self.reload_reports)

        self.search_edit = widgets.SearchEdit()
        self.refresh_btn = QtWidgets.QToolButton()
        self.refresh_btn.setDefaultAction(self.action_refresh_list)
        self.grid = widgets.TreeView()
        self.grid.header().setStretchLastSection(True)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editrow = QtWidgets.QHBoxLayout()
        self.editrow.addWidget(self.search_edit)
        self.editrow.addWidget(self.refresh_btn)
        self.layout.addLayout(self.editrow)
        self.layout.addWidget(self.grid)

        self.search_edit.textEdited.connect(self.refilter)

        self.model2 = BranchedFilterProxyModel(self)
        self.model2.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.model2.setFilterKeyColumn(0)

        self.action_add_fave = QtGui.QAction("Add &Favorite", self)
        self.action_add_fave.triggered.connect(self.add_favorite)
        self.ctxmenu = viewmenus.ContextMenu(self.grid, self)
        self.ctxmenu.contextActionsUpdate.connect(self.update_contextmenu)
        self.ctxmenu.current_row_update.connect(self.update_selection)

        # 4) Launch
        self.geo = apputils.WindowGeometry(self, grids=[self.grid])

        self.reload_reports()

    def closeEvent(self, event):
        if len(self.backgrounder.futures) > 0:
            event.ignore()
            return False
        return super(ReportsDock, self).closeEvent(event)

    def reload_reports(self):
        url = "api/user/logged-in/reports"
        self.backgrounder(self.load_reports_model, self.client.get, url)

    def load_reports_model(self):
        self.setEnabled(False)
        try:
            content = yield
            self.reports_data = content.main_table()

            self.model = models.ObjectQtModel(
                descendant_attr="model_children",
                columns=[models.field("description", "Report")],
            )

            for x in self.reports_data.rows:
                x.model_children = []

            self.role_headers = []
            rolekey = lambda x: (
                x.role_sort,
                x.role,
                x.description if x.description != None else "",
            )
            self.reports_data.rows.sort(key=rolekey)
            rolekey = lambda x: (x.role_sort, x.role)
            for k, g in itertools.groupby(self.reports_data.rows, key=rolekey):
                self.role_headers.append(RoleReportHeader(k[1], list(g)))
            self.model.set_rows(self.role_headers)
            self.model2.setSourceModel(self.model)

            with self.geo.grid_reset(self.grid):
                self.grid.setModel(self.model2)
                self.grid.expandAll()

            self.ctxmenu.update_model()
        except requests.exceptions.ConnectionError:
            # avoid a message on a refresh that fails
            pass
        except:
            utils.exception_message(
                self.window(), f"There was an error loading the {self.TITLE}."
            )
        finally:
            self.setEnabled(True)

    def refilter(self, newText):
        self.model2.setFilterFixedString(newText)

    def update_contextmenu(self, index, menu):
        row = index.data(models.ObjectRole)
        if isinstance(row, RoleReportHeader):
            return
        menu.addAction(self.action_add_fave)

    def add_favorite(self):
        row = self.ctxmenu.active_index.data(models.ObjectRole)
        favetable = rtlib.ClientTable([("activityid", None)], [])
        favetable.rows.append(favetable.DataRow(row.id))
        try:
            self.client.put(
                "api/user/logged-in/faves",
                files={"faves": favetable.as_http_post_file()},
            )
            self.main_window.dashboard.reload_reports("faves")
        except:
            utils.exception_message(
                self.window(), "There was an error saving the favorite."
            )

    def update_selection(self):
        if not self.ctxmenu.active_index:
            return

        row = self.ctxmenu.active_index.data(models.ObjectRole)
        if isinstance(row, RoleReportHeader):
            # ignore if on header
            return

        self.main_window.report_manager.preview(row)

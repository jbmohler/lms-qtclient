from PySide6 import QtCore, QtWidgets
import client.qt as qt
import cliutils
import apputils
import apputils.widgets as widgets


class DataBitMixin:
    @property
    def html_view(self):
        data = self.data if self.data else ""

        base = """
<h1>
{}
</h1>
<p>
{}
</p>""".format(
            self.caption, data.replace("\n", "<br />")
        )

        if self.website not in ["", None]:
            base += "<br /><a href='{0}'>{0}</a>".format(self.website)
        if self.uname not in ["", None]:
            base += f"<br /><b>Username: </b>{self.uname}"
        if self.pword not in ["", None]:
            base += f"<br /><b>Password: </b>{self.pword}"

        return base


class EditDataBit(QtWidgets.QDialog):
    TITLE = "DataBit Edit View"
    ID = "dlg-edit-databit"

    def __init__(self, parent):
        super(EditDataBit, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.backgrounder = apputils.Backgrounder(self)

        self.binder = qt.Binder(self)

        sb = self.binder
        sb.construct("caption", "basic")
        sb.construct("data", "multiline")
        sb.construct("website", "basic")
        sb.construct("uname", "basic")
        sb.construct("pword", "basic")

        self.form = QtWidgets.QFormLayout()
        self.form.addRow("Caption", sb.widgets["caption"])
        self.form.addRow("Data", sb.widgets["data"])
        self.form.addRow("Web Site", sb.widgets["website"])
        self.form.addRow("Username", sb.widgets["uname"])
        self.form.addRow("Password", sb.widgets["pword"])

        self.buttons = QtWidgets.QDialogButtonBox()
        self.buttons.addButton(self.buttons.Ok).clicked.connect(self.accept)
        self.buttons.addButton(self.buttons.Cancel).clicked.connect(self.reject)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttons)

    def load(self, client, databit):
        self.client = client

        self.backgrounder(
            self._load, self.client.get, "api/databits/bit/{}", databit.id
        )

    def load_new(self, client):
        self.client = client

        self.backgrounder(self._load, self.client.get, "api/databits/bit/new")

    def _load(self):
        content = yield apputils.AnimateWait(self)

        self.databit = content.main_table()
        self.editrow = self.databit.rows[0]
        self.binder.bind(self.editrow, self.databit.columns)

    def accept(self):
        self.binder.save(self.editrow)

        with apputils.animator(self) as p:
            p.background(
                self.client.put,
                "api/databits/bit/{}",
                self.editrow.id,
                files={"bit": self.databit.as_http_post_file()},
            )

        return super(EditDataBit, self).accept()


class DataBitView(QtWidgets.QWidget):
    TITLE = "DataBit"
    ID = "databit-view"
    SRC_INSTANCE_URL = "api/databits/bit/{}"
    refresh = QtCore.Signal()

    def __init__(self, parent, session):
        super(DataBitView, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.added = False

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)
        self.btn_new = self.buttons.addButton(
            "New", self.buttons.ActionRole
        ).clicked.connect(self.cmd_new_databit)
        self.btn_edit = self.buttons.addButton(
            "Edit", self.buttons.ActionRole
        ).clicked.connect(self.cmd_edit_databit_current)

        self.layout.addWidget(self.buttons)

        self.view = QtWidgets.QTextBrowser()
        self.view.setStyleSheet("QTextEdit { font-size: 14px }")
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.action_triggered)
        self.layout.addWidget(self.view)

        self.clear()

    def action_triggered(self, url):
        if url.scheme() == "local":
            pass
        else:
            cliutils.xdg_open(url.toString())

    def clear(self):
        self.view.setHtml(
            """
<html>
<body>
<p style="color: gray">select a databit</p>
</body>
</html>
"""
        )

    def highlight(self, row):
        if row == None:
            self.clear()
            return
        self.loadrow = row
        self.reload()

    def reload(self):
        self.backgrounder(
            self.load_view, self.client.get, self.SRC_INSTANCE_URL, self.loadrow.id
        )

    def load_view(self):
        content = yield apputils.AnimateWait(self)

        self.bit = content.named_table("bit", mixin=DataBitMixin).rows[0]

        self.view.setHtml(
            f"""
<html>
<body>
{self.bit.html_view}
</body>
</html>
"""
        )

    def init_grid_menu(self, gridmgr):
        self.gridmgr = gridmgr

        if not self.added:
            self.added = True
            self.gridmgr.add_action(
                "&Edit Databit",
                triggered=self.cmd_edit_databit,
                role_group="add_remove",
                default=True,
                shortcut="Ctrl+E",
                shortcut_parent=gridmgr.parent(),
            )
            self.gridmgr.add_action(
                "&New Databit",
                triggered=self.cmd_new_databit,
                role_group="add_remove",
                shortcut="Ctrl+N",
                shortcut_parent=gridmgr.parent(),
            )
            self.gridmgr.add_action(
                "&Delete Databit",
                triggered=self.cmd_delete_databit,
                role_group="add_remove",
            )

    def window(self):
        return self.gridmgr.grid.window()

    def cmd_new_databit(self):
        dlg = EditDataBit(self)
        dlg.load_new(self.client)

        if dlg.Accepted == dlg.exec_():
            self.reload()
            self.refresh.emit()

    def cmd_edit_databit_current(self):
        self.cmd_edit_databit(self.bit)

    def cmd_edit_databit(self, row):
        dlg = EditDataBit(self)
        dlg.load(self.client, row)

        if dlg.Accepted == dlg.exec_():
            self.reload()
            self.refresh.emit()

    def cmd_delete_databit(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f'Are you sure that you wish to delete the databit "{row.caption}"?',
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.id)
                self.refresh.emit()
            except:
                qt.exception_message(self.window(), "The databit could not be deleted.")


class DataBitsList(QtWidgets.QWidget):
    TITLE = "DataBits"
    ID = "databit-search"
    URL_SEARCH = "api/databits/bits/list"

    def __init__(self, parent, session):
        super(DataBitsList, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.search_edit = apputils.construct("search")
        self.layout.addWidget(self.search_edit)
        self.setFocusProxy(self.search_edit)

        self.sublay = qt.RevealedSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)
        self.sublay.addWidget(self.grid)

        self.sidebar = DataBitView(self, session)
        self.sublay.addWidget(self.sidebar)
        self.layout.addWidget(self.sublay)
        if self.sidebar != None and hasattr(self.sidebar, "init_grid_menu"):
            self.sidebar.init_grid_menu(self.gridmgr)

        self.client = session.std_client()

        self.preview_timer = qt.StdActionPause()
        self.preview_timer.timeout.connect(
            lambda: self.sidebar.highlight(self.gridmgr.selected_row())
        )
        self.gridmgr.current_row_update.connect(self.preview_timer.ui_start)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.search_now)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

    def search_now(self):
        self.backgrounder(
            self.load_data,
            self.client.get,
            self.URL_SEARCH,
            frag=self.search_edit.value(),
        )

    def load_data(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        self.gridmgr.set_client_table(self.table)


def list_widget(parent, session):
    view = DataBitsList(parent, session)
    return view

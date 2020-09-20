import json
from PySide2 import QtCore, QtGui, QtWidgets
import rtlib
from . import models
from . import widgets
from . import messages
from . import geometry

COLUMN_MIME_TYPE = "application/x-rtx-columns+json"


def model_columns_json(model, selected):
    if len(selected):
        sortable_index_list = [
            (i.column(), i.data(models.ColumnMetaRole)) for i in selected
        ]
        if len(sortable_index_list) > len(set([i for i, _ in sortable_index_list])):
            # There are distinct column objects for a single column index which
            # implies this is a hierarchical tree model.  The json clipboard
            # format is not designed with that in mind and therefore we jump
            # out here.
            return None
        cols = sorted(set(sortable_index_list))
        columns = [{"attr": c.attr, "label": c.label} for _, c in cols]
        return json.dumps(columns)
    return None


def model_html_copy(model, selected):
    def index_row_lineage(index):
        r = []
        while index.isValid():
            r.append(index.row())
            index = index.parent()
        r.reverse()
        return tuple(r)

    rows = []
    if len(selected):
        sortable_index_list = [
            (
                index_row_lineage(i),
                i.data(models.ObjectRole),
                i.column(),
                i.data(models.ColumnMetaRole),
                i,
            )
            for i in selected
        ]
        cols = list(set([x[2:4] for x in sortable_index_list]))
        cols.sort(key=lambda x: x[0])
        cols = [c[1] for c in cols]

        rows = list(set([x[0:2] for x in sortable_index_list]))
        rows.sort()
        rows = [r[1] for r in rows]

        t = rtlib.TypedTable(cols, rows)
        return t.as_html(cellspacing=0, border=1)
    return None


def model_tsv_copy(model, selected):
    """
    Fill and return a QMimeData with the text in the indexes listed.  The copied 
    data is a rectangular array of the selected cells.  Cells not selected that 
    fall with-in a row or column of the enclosing rectangle, are indicated only by 
    an empty string in the tab delimited grid.
    """

    def index_row_lineage(index):
        r = []
        while index.isValid():
            r.append(index.row())
            index = index.parent()
        r.reverse()
        return tuple(r)

    def row_data(full_cols, my_indexes):
        result = []
        my_cols = dict([(i.column(), i) for i in my_indexes])
        for x in full_cols:
            r = ""
            if x in my_cols:
                cellData = model.data(my_cols[x], QtCore.Qt.DisplayRole)
                if (
                    cellData is None
                    and model.data(my_cols[x], QtCore.Qt.CheckStateRole) is not None
                ):
                    cellData = (
                        model.data(my_cols[x], QtCore.Qt.CheckStateRole)
                        == QtCore.Qt.Checked
                    )
                r = str(cellData).replace("\n", " ") if cellData != None else ""
            result.append(r)
        return result

    rows = []
    if len(selected):
        sortable_index_list = [(index_row_lineage(i), i.column(), i) for i in selected]
        cols = list(set([x[1] for x in sortable_index_list]))
        cols.sort()

        rows = list(set([x[0] for x in sortable_index_list]))
        rows.sort()

        headers = [
            model.headerData(x, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
            for x in cols
        ]
        headers = [h.replace("\n", " ") for h in headers]
        textrows = ["\t".join(headers)]
        for y in rows:
            my_indexes = [x[2] for x in sortable_index_list if x[0] == y]
            textrows.append("\t".join(row_data(cols, my_indexes)))
        return "\n".join(textrows)
    return None


class ActionPushButton(QtWidgets.QPushButton):
    def setAction(self, action):
        self._action = action
        self._action.changed.connect(self.update_from_action)
        self.clicked.connect(self._action.triggered.emit)
        self.update_from_action()

    def update_from_action(self):
        self.setText(self._action.text())
        self.setEnabled(self._action.isEnabled())


class FindDialog(QtWidgets.QDialog):
    def __init__(self, view, parent=None):
        super(FindDialog, self).__init__(parent)

        self.setWindowTitle("Find/Filter Grid")
        self.setObjectName("find-dialog")
        self.layout = QtWidgets.QVBoxLayout(self)

        self.view = view
        self.model = view.model()

        self.value = QtWidgets.QLineEdit()

        self.form = QtWidgets.QFormLayout()
        self.form.addRow("&Find", self.value)
        self.layout.addLayout(self.form)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)
        self.btn_find = self.buttons.addButton("&Find", self.buttons.ActionRole)
        self.btn_find.clicked.connect(self.find_now)
        self.btn_filter = self.buttons.addButton("&Filter", self.buttons.ActionRole)
        self.btn_filter.clicked.connect(self.filter_now)
        self.btn_unfind = self.buttons.addButton("&Reset", self.buttons.ActionRole)
        self.btn_unfind.clicked.connect(self.unfilter)
        self.btn_close = self.buttons.addButton("&Close", self.buttons.RejectRole)
        self.btn_close.clicked.connect(lambda *args: self.close())
        self.layout.addWidget(self.buttons)

    def unfilter(self):
        self.model.unfilter()
        self.model.set_highlight_string(None)

    def find_now(self):
        t = self.value.text()

        invalid = QtCore.QModelIndex()
        found = None
        for r1 in range(self.model.rowCount(invalid)):
            for c1 in range(self.model.columnCount(invalid)):
                i1 = self.model.index(r1, c1, invalid)
                d1 = self.model.data(i1, QtCore.Qt.DisplayRole)
                if d1 != None and d1.lower().find(t) >= 0:
                    self.view.setCurrentIndex(i1)
                    found = i1
                    break
            if found != None:
                break

        self.model.unfilter()
        self.model.set_highlight_string(t)

    def filter_now(self):
        def text_match_predicate(row, columns, text):
            for c in columns:
                v = getattr(row, c.attr)
                if v == None:
                    continue
                v = c.formatter(v)
                if v == None:
                    continue
                if v.lower().find(text.lower()) >= 0:
                    return True
            return False

        c = [col for col in self.model.columns if not getattr(col, "is_numeric", False)]
        t = self.value.text()
        pred = lambda row, columns=c, text=t: text_match_predicate(row, columns, text)
        self.model.filter_by_predicate(pred)
        self.model.set_highlight_string(t)


def hline():
    toto = QtWidgets.QFrame()
    toto.setFrameShape(QtWidgets.QFrame.HLine)
    toto.setFrameShadow(QtWidgets.QFrame.Sunken)
    return toto


class ModelImportError(RuntimeError):
    pass


class Importer(QtWidgets.QDialog):
    ID = "delimited-import"
    TITLE = "Import Delimited Text"

    def __init__(self, parent):
        super(Importer, self).__init__(parent)

        self.setObjectName(self.ID)
        self.setWindowTitle(self.TITLE)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.hlay = QtWidgets.QHBoxLayout()
        self.hlay.setContentsMargins(0, 0, 0, 0)
        self.settings = QtWidgets.QFormLayout()

        self.delimiter_edit = QtWidgets.QComboBox()
        self.delimiter_edit.setEditable(True)
        for ch in [",", "<tab>", "|", ";", "<space>"]:
            self.delimiter_edit.addItem(ch)
        self.delimiter_edit.setMaximumWidth(75)
        self.quote_opt_edit = QtWidgets.QCheckBox("Remove Quote &Character")
        self.quote_edit = QtWidgets.QLineEdit()
        self.quote_edit.setMaximumWidth(75)
        self.header_edit = QtWidgets.QCheckBox("&Header")
        self.header_edit.clicked.connect(lambda *args: self.reparse_text())

        self.column_edit = QtWidgets.QComboBox()
        self.column_edit.currentIndexChanged.connect(self.reset_column_label)

        self.layout.addLayout(self.hlay)
        self.hlay.addLayout(self.settings, 3)

        self.settings.addRow("&Delimiter", self.delimiter_edit)
        self.settings.addRow(self.quote_opt_edit, self.quote_edit)
        self.settings.addRow(None, self.header_edit)

        self.commlay = QtWidgets.QVBoxLayout()
        self.commlay.setContentsMargins(0, 0, 0, 0)
        self.btn_auto_map = QtWidgets.QPushButton("&Auto-Map")
        self.btn_auto_map.clicked.connect(self.auto_map_columns)
        self.commlay.addStretch(2)
        self.commlay.addWidget(self.btn_auto_map)
        self.hlay.addLayout(self.commlay)

        self.layout.addWidget(hline())

        self.set2 = QtWidgets.QFormLayout()
        self.set2.addRow("&Import Selected Column As", self.column_edit)
        self.layout.addLayout(self.set2)

        self.grid = widgets.TableView()
        self.grid.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectColumns)
        self.grid.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.layout.addWidget(self.grid, 3)

        QDB = QtWidgets.QDialogButtonBox
        self.buttons = QDB(QtCore.Qt.Horizontal)
        self.buttons.addButton(QDB.Ok).clicked.connect(self.accept)
        self.buttons.addButton(QDB.Cancel).clicked.connect(self.reject)

        self.layout.addWidget(self.buttons)

        self.model = None

        self.geo = geometry.WindowGeometry(self, position=False)

        self.delimiter_edit.lineEdit().setText("<tab>")
        QtCore.QTimer.singleShot(100, self.prepare_from_clipboard)

    def receiving_columns(self):
        req = (
            []
            if self.importer.required_columns == None
            else self.importer.required_columns
        )
        for column in self.ambient_model.columns:
            if column.editable or column.attr in req:
                yield column

    def set_model(self, model, importer):
        self.ambient_model = model
        self.importer = importer
        self.column_edit.addItem("<skip>", None)
        for column in self.receiving_columns():
            self.column_edit.addItem(column.label.replace("\n", " "), column.attr)

    def auto_map_columns(self):
        options = [column for column in self.receiving_columns()]
        if self.importer.assess_row != None:
            data_columns = self.model.columns[1:]
        else:
            data_columns = self.model.columns[:]
        for index, head in enumerate(self.raw_headline):
            col = data_columns[index]
            for c in options:
                if head == c.attr or head == c.label:
                    col.label = c.label
                    col.import_attr = c.attr

        self.model.headerDataChanged.emit(
            QtCore.Qt.Horizontal, 0, len(self.raw_headline)
        )

        self.amalgamate_data()

    def reset_column_edit(self, index, oldindex):
        col = self.model.columns[index.column()]
        idx = self.column_edit.findText(col.label)
        self.column_edit.setCurrentIndex(idx)

    def reset_column_label(self, idx):
        if self.model == None:
            return

        index = self.grid.currentIndex()
        col = self.model.columns[index.column()]
        if col.attr == "status":
            return
        col.label = self.column_edit.currentText()
        col.import_attr = self.column_edit.itemData(self.column_edit.currentIndex())

        self.model.headerDataChanged.emit(QtCore.Qt.Horizontal, index, index)

        self.amalgamate_data()

    def prepare_from_clipboard(self):
        clipboard = QtWidgets.QApplication.instance().clipboard()
        mime = clipboard.mimeData()

        if mime.hasText():
            columns = None
            if mime.hasFormat(COLUMN_MIME_TYPE):
                b1 = mime.data(COLUMN_MIME_TYPE)
                try:
                    p1 = str(b1.data(), "ascii")
                    columns = json.loads(p1)
                except:
                    pass
            if columns != None:
                self.header_edit.setChecked(True)

            text = mime.text()
            if len(text) > 2 ** 25:
                messages.information(self, "Text from clipboard exceeds maximum size.")
            else:
                self.raw_text = text
                self.reparse_text()

            if columns != None:
                data_columns = self.model.columns
                if self.importer.assess_row != None:
                    data_columns = self.model.columns[1:]
                editable = [column.attr for column in self.receiving_columns()]
                for c_head, c_data in zip(columns, data_columns):
                    if c_head["attr"] in editable:
                        c_data.label = c_head["label"]
                        c_data.import_attr = c_head["attr"]

                self.amalgamate_data()
        else:
            messages.information(self, "Unparseable text data on clipboard.")

    def reparse_text(self):
        delimiter = self.delimiter_edit.currentText()
        delimiter = delimiter.replace("<tab>", "\t").replace("<space>", " ")

        lines = [ll.strip() for ll in self.raw_text.split("\n") if ll.strip() != ""]
        if self.header_edit.isChecked():
            self.raw_headline = lines[0].split(delimiter)
            lines = lines[1:]
        self.btn_auto_map.setEnabled(self.header_edit.isChecked())
        lines = [ll.split(delimiter) for ll in lines]

        if len(lines) == 0:
            messages.information(self, "The clipboard is empty.")
            QtCore.QTimer.singleShot(0, self.close)
            return

        columns = max([len(v) for v in lines])
        pad = [None] * columns
        lines = [(v + pad)[:columns] for v in lines]

        if columns > 999:
            messages.information(self, "There are too many columns.")
            QtCore.QTimer.singleShot(0, self.close)
            return

        cols = []
        if self.importer.assess_row != None:
            cols += [models.field("status", "Incoming")]
        cols += [models.field(f"v{i:03n}", "<skip>") for i in range(columns)]
        for col in cols:
            if col.attr != "status":
                col.import_attr = None

        if self.importer.assess_row != None:
            self.MyDataRow = rtlib.fixedrecord(
                "MyDataRow", ["status"] + [f"v{i:03n}" for i in range(columns)]
            )
            rows = [self.MyDataRow(None, *v) for v in lines]
        else:
            self.MyDataRow = rtlib.fixedrecord(
                "MyDataRow", [f"v{i:03n}" for i in range(columns)]
            )
            rows = [self.MyDataRow(*v) for v in lines]

        self.model = models.ObjectQtModel(cols, parent=self)
        self.model.set_rows(rows)
        self.grid.setModel(self.model)
        self.selmodel = self.grid.selectionModel()
        self.selmodel.currentChanged.connect(self.reset_column_edit)

        self.amalgamate_data()

    def parametrized_imports(self):
        if self.importer.required_columns != None:
            sourced = [
                col.import_attr
                for col in self.model.columns
                if col.attr != "status" and col.import_attr != None
            ]
            missing = set(self.importer.required_columns).difference(sourced)
            if len(missing) == 1:
                raise ModelImportError(
                    f'Column "{missing.pop()}" is required for the import.'
                )
            if len(missing) > 1:
                raise ModelImportError(
                    'Columns "{}" are required for the import.'.format(
                        '", "'.join(sorted(missing))
                    )
                )

        m = {
            col.attr: col.import_attr
            for idx, col in enumerate(self.model.columns)
            if col.attr != "status" and col.import_attr != None
        }

        for row in self.model.rows:
            yield row, {v: getattr(row, k, None) for k, v in m.items()}

    def amalgamate_data(self):
        if self.importer.assess_row == None:
            return

        try:
            for row, kwargs in self.parametrized_imports():
                row.status = self.importer.assess_row(**kwargs)
        except ModelImportError:  # as e:
            # self.error_msg.setText(e)
            pass

    def accept(self):
        try:
            for _, kwargs in self.parametrized_imports():
                self.importer.import_row(**kwargs)
        except ModelImportError as e:
            # self.error_msg.setText(e)
            messages.information(self, str(e))
            return

        super(Importer, self).accept()


class ContextMenu(QtCore.QObject):
    triggerReload = QtCore.Signal(object)
    contextActionsUpdate = QtCore.Signal(object, object)
    statisticsUpdate = QtCore.Signal(object)
    current_row_update = QtCore.Signal()

    def __init__(self, view, parent, no_shortcut=None):
        super(ContextMenu, self).__init__(parent)

        self.importer = None

        self.actions = []
        self.active_index = None
        self._default_action = None
        self._selmodel = None
        self._view = view
        self._view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self.show_menu)
        self._view.doubleClicked.connect(self.default_action)
        self._view.installEventFilter(self)

        self.buttons = []

        if no_shortcut == None:
            no_shortcut = []

        # global grid actions
        self.action_findfilter = QtWidgets.QAction("Find/Fil&ter...", self)
        if "find" not in no_shortcut:
            self.action_findfilter.setShortcut("Ctrl+F")
            self.action_findfilter.setShortcutContext(QtCore.Qt.WidgetShortcut)
        self.action_findfilter.triggered.connect(self.find_or_filter)
        self._view.addAction(self.action_findfilter)
        self.action_copy_selection_formatted = QtWidgets.QAction(
            "Copy &Formatted", self
        )
        if "copy" not in no_shortcut:
            self.action_copy_selection_formatted.setShortcut(QtGui.QKeySequence.Copy)
            self.action_copy_selection_formatted.setShortcutContext(
                QtCore.Qt.WidgetShortcut
            )
        self.action_copy_selection_formatted.triggered.connect(self.copy_selected_cells)
        self._view.addAction(self.action_copy_selection_formatted)
        self.action_copy_selection_unformatted = QtWidgets.QAction(
            "Copy &Unformatted", self
        )
        self.action_copy_selection_unformatted.triggered.connect(
            self.copy_selected_cells_unformatted
        )
        self._view.addAction(self.action_copy_selection_unformatted)
        self.action_import_clipboard = QtWidgets.QAction("&Import from Clipboard", self)
        self.action_import_clipboard.triggered.connect(self.import_rows)
        self.action_tree_collapse = QtWidgets.QAction("Collapse All", self)
        self.action_tree_collapse.triggered.connect(lambda: self._view.collapseAll())

    def eventFilter(self, obj, event):
        if (
            obj == self._view
            and event.type() == QtCore.QEvent.KeyPress
            and event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]
            and self.active_index != None
        ):
            self.default_action(self.active_index, row=True)
            return True
        return super(ContextMenu, self).eventFilter(obj, event)

    def update_model(self):
        self._selmodel = self._view.selectionModel()
        self._selmodel.currentRowChanged.connect(self.update_active)
        self._selmodel.selectionChanged.connect(self.selection_changed)

        self.update_active_index(None)

    def update_active_index(self, active):
        self.active_index = active
        for act in self.actions:
            if act._oncurrent:
                act.setEnabled(self.active_index != None)
        self.current_row_update.emit()

    def update_active(self, current, previous):
        self.update_active_index(current)

    def advance_highlight(self):
        current = self._view.currentIndex()
        m = self._view.model()
        row = current.row() + 1
        if 0 <= row < m.rowCount(None):
            rowpair = m.index_row(row)
            itemsel = QtCore.QItemSelection(*rowpair)
            self._selmodel.setCurrentIndex(
                rowpair[0], QtCore.QItemSelectionModel.SelectCurrent
            )
            self._selmodel.select(itemsel, QtCore.QItemSelectionModel.SelectCurrent)

    def selection_changed(self, selected, deselected):
        values = [
            index.data(models.DecimalRole) for index in self._selmodel.selectedIndexes()
        ]
        values = [v for v in values if v != None]
        self.statisticsUpdate.emit(values)

    def selected_indexes(self):
        if self._selmodel == None:
            # just in time recheck initialization
            self._selmodel = self._view.selectionModel()
        return self._selmodel.selectedIndexes()

    def default_action(self, index, row=False):
        self.active_index = index

        action_attr = lambda action: getattr(action, "dbl_click_attr", None)

        attr = index.data(models.ColumnAttributeRole)
        thisact = self._default_action
        for act in self.actions:
            if not row and action_attr(act) == attr:
                thisact = act
                break
        else:
            attr = action_attr(self._default_action)
            if attr != None:
                row = index.data(models.ObjectRole)
                if not hasattr(row, attr):
                    thisact = None
        if thisact != None:
            thisact.trigger()

    def add_action(self, act, default=False, oncurrent=False):
        act._oncurrent = oncurrent
        self.actions.append(act)
        if default:
            self._default_action = act

    def reset_action_list(self):
        self.actions = []
        self._default_action = None

    def find_or_filter(self):
        dlg = FindDialog(self._view, self._view.window())
        dlg.show()

    def copy_selected_cells_unformatted(self):
        self.copy_selected_cells(with_html=False)

    def copy_selected_cells(self, with_html=True):
        m = QtCore.QMimeData()
        if len(self.selected_indexes()) == 1:
            index = self.selected_indexes()[0]
            if with_html:
                column = index.data(models.ColumnMetaRole)
                html = rtlib.html_cell(column, index.data(models.ObjectRole))
                m.setData("text/html", html)
            m.setText(index.data(QtCore.Qt.DisplayRole))
        else:
            tsv = model_tsv_copy(self._view.model(), self.selected_indexes())
            # I would read the documentation on setText to do exactly what the setData
            # line does.  However, that doesn't seem to be the case.  I prefer the
            # setData as it seems more fundamental, but maybe that is just silly.
            # m.setData('text/plain', tsv)
            m.setText(tsv)
            if with_html:
                html = model_html_copy(self._view.model(), self.selected_indexes())
                m.setData("text/html", html)
            m.setData(
                COLUMN_MIME_TYPE,
                model_columns_json(self._view.model(), self.selected_indexes()),
            )

        cb = QtWidgets.QApplication.instance().clipboard()
        cb.setMimeData(m)

    def import_rows(self):
        d = Importer(self._view.parent())
        d.set_model(self._view.model(), self.importer)
        d.exec_()

    def show_menu(self, point):
        index = self._view.indexAt(point)
        if not index.isValid():
            return

        self.active_index = index

        menu = QtWidgets.QMenu()
        for a in self.actions:
            f_appear = getattr(a, "should_appear", None)
            if f_appear != None and not f_appear(index):
                continue
            f_enabled = getattr(a, "is_enabled", None)
            if f_enabled != None:
                a.setEnabled(f_enabled(index))
            menu.addAction(a)
        self.contextActionsUpdate.emit(index, menu)
        gridacts = []
        if self._view.model() != None and len(self.selected_indexes()) > 0:
            gridacts.append(self.action_findfilter)
            gridacts.append(self.action_copy_selection_formatted)
            gridacts.append(self.action_copy_selection_unformatted)
        if self.importer != None:
            gridacts.append(self.action_import_clipboard)
        if isinstance(self._view, widgets.TreeView):
            gridacts.append(self.action_tree_collapse)

        if len(menu.actions()) > 0 and len(gridacts) > 0:
            menu.addSeparator()
        if len(gridacts) > 0:
            for g in gridacts:
                menu.addAction(g)

        menu.exec_(self._view.viewport().mapToGlobal(point))

    def get_button(self, act):
        b = ActionPushButton()
        b.setAction(act)
        self.buttons.append(b)
        return b

    def fill_button_box(self, bb):
        for a in self.actions:
            b = ActionPushButton()
            b.setAction(a)
            self.buttons.append(b)
            bb.addButton(b, QtWidgets.QDialogButtonBox.ActionRole)

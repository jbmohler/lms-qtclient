import contextlib
from PySide6 import QtCore, QtGui, QtWidgets
import apputils
from . import columnchooser
import apputils.models as models


class ViewBaseMixin:
    def init_column_choose(self):
        self.header().setSectionsMovable(True)

        self.choose_action = QtGui.QAction("&Manage Columns", self)
        self.choose_action.triggered.connect(self.choose_columns)
        self.header().addAction(self.choose_action)
        self.header().setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def choose_columns(self):
        if None == apputils.base_columned_model(self.model()):
            apputils.information(
                self.window(), "Column management is not available for this list."
            )
            return
        m = columnchooser.ModelColumnChooser(self.window())
        m.set_view(self)
        m.exec_()

    def commit_editors(self):
        self.itemDelegate().commit_current()


class TreeView(QtWidgets.QTreeView, ViewBaseMixin):
    def __init__(self, parent=None, column_choosing=True):
        super(TreeView, self).__init__(parent)

        self.setItemDelegate(ReportCoreModelDelegate())
        self.itemDelegate().view = self

        self._gridlines = False

        if column_choosing:
            self.init_column_choose()

    def setGridLines(self, b):
        self._gridlines = bool(b)

    def gridLines(self):
        return self._gridlines

    def paintEvent(self, event):
        old = self.selectionBehavior()
        # The Qt qs60style.cpp appears to have special code for anything other
        # than SelectItem and I prefer that painting style.  I do not
        # understand at a technical level why the QTableView and QTreeView
        # paint differently for SelectItems mode.
        self.setSelectionBehavior(self.SelectRows)

        x = super(TreeView, self).paintEvent(event)

        self.setSelectionBehavior(old)
        return x


class TableView(QtWidgets.QTableView, ViewBaseMixin):
    def __init__(self, parent=None, column_choosing=True):
        super(TableView, self).__init__(parent)

        self.setItemDelegate(ReportCoreModelDelegate())
        self.itemDelegate().view = self

        if column_choosing:
            self.init_column_choose()

    def header(self):
        return self.horizontalHeader()


class ReportCoreModelDelegate(QtWidgets.QStyledItemDelegate):
    def setEditorData(self, editor, index):
        try:
            # TODO:  acclimate this qtalchemy-ism
            cls = index.model().cls
            if cls:
                c = index.model().columns[index.column()]
                userattr = getattr(cls, c.attr if hasattr(c, "attr") else c)
                if userattr is not None and hasattr(userattr, "WidgetBind"):
                    userattr.WidgetBind(
                        editor, index.model().row_object_by_index(index)
                    )
        except AttributeError:
            pass

        if not hasattr(editor, "_delegate_setup_done_"):
            if isinstance(editor, QtWidgets.QComboBox):
                editor.currentIndexChanged.connect(
                    lambda _, _ed=editor: self.commit_trigger(_ed)
                )
            editor._delegate_setup_done_ = True

        # http://bugreports.qt.nokia.com/browse/QTBUG-428 - combo boxes don't play nice with qdatawidget mapper
        if apputils.is_modifiable(editor):
            editor.setValue(index.data(QtCore.Qt.EditRole))
        elif isinstance(editor, QtWidgets.QComboBox):
            text = index.data()
            if text == None:
                text = ""
            if editor.isEditable():
                editor.setEditText(text)
            else:
                editor.setCurrentIndex(editor.findText(text))
        else:
            QtWidgets.QStyledItemDelegate.setEditorData(self, editor, index)

        if apputils.is_modifiable(editor):
            editor.setWidgetModified(False)

    def commit_trigger(self, editor):
        self.commitData.emit(editor)

    def commit_current(self):
        if getattr(self, "current_editor", None) != None:
            self.commit_trigger(self.current_editor)

    def _mass_edit_indices(self, index):
        if self.view != None:
            indices = []
            for index2 in self.view.selectedIndexes():
                if (
                    index.parent() == index2.parent()
                    and index.column() == index2.column()
                ):
                    indices.append(index2)
            # This exception clause makes checking an index only
            # work en-masse if the check/uncheck action is in
            # the selection.  Programmatically it feels odd
            # (IMO) that you can check/uncheck a cell with-out
            # changing the selection.  In the UI it feels pretty
            # natural though.
            if index.row() not in [i.row() for i in indices]:
                indices = [index]
            return indices
        return [index]

    @contextlib.contextmanager
    def fakeMass(self):
        yield

    def massEdit(self, model, index):
        if hasattr(model, "massEditProxies"):
            indices = self._mass_edit_indices(index)
            return model.massEditProxies(indices)
        else:
            return self.fakeMass()

    def setModelData(self, editor, model, index):
        if apputils.is_modifiable(editor) and not editor.widgetModified():
            # no changes!
            return

        with self.massEdit(model, index):
            try:
                if self.view != None and apputils.is_modifiable(editor):
                    # Apply the new value to each selected item in the same column
                    v = editor.value()
                    model.setData(index, v)
                elif isinstance(editor, QtWidgets.QComboBox):
                    model.setData(index, editor.currentText())
                else:
                    QtWidgets.QStyledItemDelegate.setModelData(
                        self, editor, model, index
                    )
            except models.ValueSetRefusal:
                pass

    def editorEvent(self, event, model, option, index):
        with self.massEdit(model, index):
            return QtWidgets.QStyledItemDelegate.editorEvent(
                self, event, model, option, index
            )

    def createEditor(self, parent, option, index):
        column = index.model().columns[index.column()]
        if column.widget_factory != None:
            editor = column.widget_factory(parent, **column.widget_kwargs)
            # See also fidolib.qt.bindings.Binder.bind
            if isinstance(editor, QtWidgets.QLineEdit) and column.max_length != None:
                editor.setMaxLength(column.max_length)
            if self.view != None and apputils.is_modifiable(editor):
                editor.persister = lambda value: index.model().setData(index, value)
            self.current_editor = editor
            return editor
        return QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)

    def paint(self, painter, option, index):
        if index.data(models.RenderRole) == models.RenderHtml:
            self._html_paint(painter, option, index)
            return

        if (
            self.view != None
            and hasattr(self.view, "gridLines")
            and self.view.gridLines()
        ):
            painter.save()
            painter.setPen(QtGui.QColor(QtCore.Qt.lightGray))
            painter.drawRect(option.rect)
            painter.restore()
            # offset to not obscure gridlines with back color
            option.rect.adjust(+1, +1, 0, 0)

        return QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, option, index):
        if index.data(models.RenderRole) == models.RenderHtml:
            return self._html_sizeHint(option, index)

        m = QtGui.QFontMetrics(option.font)
        w = m.boundingRect(index.data(QtCore.Qt.DisplayRole)).width()
        pad = 0
        if option.decorationSize.width() > 0:
            pad = option.decorationSize.width()
        return QtCore.QSize(w + pad, m.height() * 2)

    def _html_paint(self, painter, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)

        style = (
            QtWidgets.QApplication.style()
            if options.widget is None
            else options.widget.style()
        )

        doc = QtGui.QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        options.text = ""
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, options, painter)

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        # if (optionV4.state & QStyle::State_Selected)
        #   ctx.palette.setColor(QPalette::Text, optionV4.palette.color(QPalette::Active, QPalette::HighlightedText))

        textRect = (
            options.rect
        )  # style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, options,)
        if index.flags() & QtCore.Qt.ItemIsUserCheckable:
            textRect = textRect.adjusted(options.decorationSize.width(), 0, 0, 0)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def _html_sizeHint(self, option, index):
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)

        doc = QtGui.QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        return QtCore.QSize(doc.idealWidth(), doc.size().height())


class EditableTableView(TableView):
    def __init__(self, parent=None):
        super(EditableTableView, self).__init__(parent)
        # self.use_edit_tab_semantics = False

        self.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)


class EditableTreeView(TreeView):
    def __init__(self, parent=None):
        super(EditableTreeView, self).__init__(parent)
        # self.use_edit_tab_semantics = False

        self.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)

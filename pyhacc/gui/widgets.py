from QtShim import QtCore, QtGui, QtWidgets
import client
import valix
import rtlib
import apputils
import apputils.widgets as base
import apputils.models as models
import client.qt as qt

AccountMiniInfo = rtlib.fixedrecord('AccountMiniInfo', ['id', 'name'])
AccountTypeMiniInfo = rtlib.fixedrecord('AccountTypeMiniInfo', ['id', 'name'])

class STATIC:
    account_types = 'account_types'
    journals = 'journals'

class UnknownKey(apputils.ModValueError):
    pass


class IdentifierEdit(base.KeyEdit):
    # TODO:  document server & URL requirements for IdentifierEdit & friends
    def __init__(self, parent=None):
        super(IdentifierEdit, self).__init__(parent)

        #self._validator = base.UpperValidator(self)
        #self.setValidator(self._validator)
        self.popup_list = None

        app = QtWidgets.QApplication.instance()
        self.client = app.session.std_client()
        self.backgrounder = apputils.Backgrounder(self)

        self._static_key = None

        self.pause_autofill = False
        self.textEdited.connect(self.update_prefix)

        self.action_lookup = None
        if hasattr(self, 'LOOKUP_URL_CONSTRUCTION'):
            self.action_lookup = QtWidgets.QAction('&Look-up...', self)
            self.action_lookup.setShortcut(QtGui.QKeySequence('Ctrl+F4'))
            self.action_lookup.setShortcutContext(QtCore.Qt.WidgetShortcut)
            self.action_lookup.triggered.connect(self.std_url_lookup)
            self.addAction(self.action_lookup)

        self._init_popup()

    INVALID = "QLineEdit{ background: --; }".replace('--', valix.INVALID_RGBA)
    VALID = "QLineEdit{}"

    def set_invalid_feedback(self, invalid=True):
        if invalid:
            self.setStyleSheet(self.INVALID)
        else:
            self.setStyleSheet(self.VALID)
        self.style().unpolish(self)
        self.style().polish(self)

    def exact_object_match(self, objs):
        raise NotImplementedError('override this method to determine if any of the passed objects matches the current text')

    def construct_popup_model(self):
        raise NotImplementedError('override this method to build the model for the self.popup_list')

    def set_value_from_object(self, obj):
        raise NotImplementedError('override this method to set text and static primary key')

    def std_url_lookup(self):
        if self._static_key != None:
            url = self.LOOKUP_URL_CONSTRUCTION.format(self._static_key)
            import fidolib.framework.fidoglob as fg
            fg.show_fido_link_parented(self.window(), url)

    def clear_value(self):
        self._static_key = None
        self.editingFinished.emit()

    def clear_static_key(self):
        if hasattr(self, '_static_key'):
            del self._static_key

    def set_static_key(self, value):
        self._static_key = value

    def get_static_key(self):
        if hasattr(self, '_static_key'):
            return self._static_key
        raise UnknownKey('no static key matches value or value is unverified')

    def _init_popup(self):
        if self.popup_list is not None:
            return

        # configure the popup view as a popup
        # lots of logic copied from http://qt.gitorious.org/qt/qt/blobs/4.7/src/gui/util/qcompleter.cpp
        self.popup_list = QtWidgets.QTableView()
        self.popup_list.verticalHeader().hide()
        self.popup_list.verticalHeader().setDefaultSectionSize(18)
        self.popup_list.setSelectionMode(self.popup_list.SingleSelection)
        self.popup_list.setParent(self, QtCore.Qt.Popup)
        self.popup_list.setFocusPolicy(QtCore.Qt.NoFocus)
        self.popup_list.setFocusProxy(self)
        self.popup_list.installEventFilter(self)

        self.popup_list.clicked.connect(self.selection_on_list)
        self.popup_list.activated.connect(self.selection_on_list)

        self._popup_model = self.construct_popup_model()
        self.popup_list.setModel(self._popup_model)

    def selection_on_list(self, index):
        obj = index.data(models.ObjectRole)
        self.set_value_from_object(obj)
        self.popup_list.hide()

    def shutdown(self, obj):
        if self.popup_list is not None:
            self.popup_list.hide()
            self.popup_list.close()
            self.popup_list = None

    def event(self, e):
        if e.type() in [QtCore.QEvent.KeyPress]:
            self.pause_autofill = e.key() in [QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete]
        if e.type() in [QtCore.QEvent.Hide]:
            self.shutdown(self)
        if e.type() in [QtCore.QEvent.Show]:
            self._init_popup()
        return super(IdentifierEdit, self).event(e)

    def eventFilter(self, o, e):
        if o is not self.popup_list:
            return super(IdentifierEdit, self).eventFilter(o, e)

        if e.type() == QtCore.QEvent.KeyPress:
            if e.key() in [QtCore.Qt.Key_Escape, QtCore.Qt.Key_Return, QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab]:
                self.popup_list.hide()
            if e.key() in [QtCore.Qt.Key_Escape]:
                return True

            self.event(e)
            if e.isAccepted():
                return True

        if e.type() == QtCore.QEvent.MouseButtonPress:
            if self.popup_list.isVisible() and not self.popup_list.underMouse():
                self.popup_list.hide()

        return super(IdentifierEdit, self).eventFilter(o, e)

    def update_prefix(self, text):
        self.clear_static_key()
        sc = lambda prefix=text: self.show_completions(prefix)
        self.backgrounder.named['auto-complete'](sc, self.client.get, self.PREFIX_COMPLETIONS_URL, prefix=text)

    def show_completions(self, prefix):
        try:
            completions = yield
            self.refine_popup(prefix, completions)
        except:
            qt.exception_message(self.window(), 'Completions failed')

    def refine_popup(self, prefix, content):
        self.popup_data = content.main_table()

        if len(self.popup_data.rows) > 0:
            self._popup_model.set_rows(self.popup_data.rows)
            rect = self.rect()
            self.popup_list.move(self.mapToGlobal(rect.bottomLeft()))
            self.popup_list.show()
            if self.popup_list.width() < self.width():
                self.popup_list.resize(self.width(), self.popup_list.viewport().height())
            self.popup_list.resizeColumnsToContents()
            self.setFocus(QtCore.Qt.PopupFocusReason)
        else:
            self.popup_list.hide()

        selstart = self.selectionStart()
        if selstart == -1:
            selstart = self.cursorPosition()
        if len(prefix) == selstart and self.text()[:selstart] == prefix:
            if len(self.popup_data.rows) == 0:
                # none available
                #self.clear_static_key() -- already done in update_prefix
                self.set_invalid_feedback()
                self.editingFinished.emit()
            elif self.pause_autofill:
                # if exact match found, then claim object
                match = self.exact_object_match(self.popup_data.rows)
                if match == None:
                    if len(prefix) == 0:
                        self.set_invalid_feedback()
                        self.clear_value()
                    else:
                        self.editingFinished.emit()
                else:
                    self.set_invalid_feedback(False)
                    self.set_value_from_object(match)
            else:
                self.set_invalid_feedback(False)
                self.set_value_from_object(self.popup_data.rows[0])
                self.setSelection(selstart, len(self.text()))

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if self.action_lookup != None:
            sep = QtWidgets.QAction(self)
            sep.setSeparator(True)
            menu.addAction(sep)
            menu.addAction(self.action_lookup)
        menu.exec_(event.globalPos())

    def set_static_key_public(self, key):
        if key == None:
            self.setText('')
            self.set_static_key(None)
        else:
            content = self.client.get(self.AUTOID_RESOLVE_URL.format(key), minimal=True)
            table = rtlib.ClientTable(*content[1:])
            self.set_value_mini(table.rows[0])

    def set_value_from_object(self, obj):
        self.set_value_mini(obj)
        self.editingFinished.emit()


class AccountEdit(IdentifierEdit):
    PREFIX_COMPLETIONS_URL = 'api/accounts/completions'

    def __init__(self, parent=None):
        super(AccountEdit, self).__init__(parent)

        self.buttonPressed.connect(self.clicked)

    def clicked(self):
        import pyhacclib.glaccounts as glaccounts
        app = QtWidgets.QApplication.instance()
        v = glaccounts.AccountSearch(app.session, app.exports_dir)
        dlg = SearchShell(self.window(), v)
        dlg.show()
        if dlg.Accepted == dlg.exec_():
            if hasattr(self, 'persister'):
                self.persister(dlg.inside.ctxmenu.active_index.data(models.ObjectRole).account)
                return
            self.set_invalid_feedback(False)
            self.set_value_from_object(dlg.inside.ctxmenu.active_index.data(models.ObjectRole))

    def construct_popup_model(self):
        columns = [ \
                models.Column('acc_name', 'Account'),
                models.Column('type', 'Type'),
                models.Column('description', 'Description')]
        return models.ObjectQtModel(columns)

    def exact_object_match(self, objs):
        t = self.text()
        for obj in objs:
            if obj.account == t:
                return obj
        return None

    def get_value_mini(self):
        if self.get_static_key() == None:
            return None
        else:
            return AccountMiniInfo(id=self.get_static_key(), acc_name=self.text())

    def set_value_mini(self, value):
        if value != None:
            self.setText(value.acc_name)
            self.set_static_key(value.id)
        else:
            self.setText('')
            self.clear_static_key()


class AccountingWidgetsPlugin:
    def polish(self, attr, type_, meta):
        if type_ == 'pyhacc_account':
            meta['formatter'] = lambda x: x.acc_name
            meta['coerce_edit'] = lambda x: x

    def widget_map(self):
        return { \
            'pyhacc_account': pyhacc_account_tuple_edit,
            'pyhacc_account.autoid': pyhacc_account_autoid_edit,
            'pyhacc_account.name': pyhacc_account_acc_name_edit,
            'pyhacc_accounttype.id': pyhacc_static_settings_value_combo(STATIC.account_types),
            'pyhacc_journal.id': pyhacc_static_settings_value_combo(STATIC.journals)}
            #'pyhacc_accounttype': pyhacc_static_settings_value_combo(STATIC.account_types, AccountTypeMiniInfo)}


LOCAL_STATIC_SETTINGS = []

def verify_settings_load(parent, client, widgets):
    if isinstance(widgets, qt.Binder):
        widgets = list(widgets.widgets.values())

    global LOCAL_STATIC_SETTINGS
    needs_load = lambda w: getattr(w, 'STATIC_SETTINGS_NAME', None) not in [None]+LOCAL_STATIC_SETTINGS
    to_load_widgets = [w for w in widgets if needs_load(w)]

    client.session.ensure_static_settings(list(set([w.STATIC_SETTINGS_NAME for w in to_load_widgets])))

    for w in to_load_widgets:
        w.load_static_settings()

def static_settings(settings_name, withkey=True):
    app = QtWidgets.QApplication.instance()
    return app.session.static_settings(settings_name, withkey=withkey)

def load_static_settings(self):
    try:
        self._combo.clear()
        items = static_settings(self.STATIC_SETTINGS_NAME, withkey=False)
        if getattr(self, 'all_option', False):
            self._combo.addItem('All', None)
        else:
            self._combo.addItem('', None)
        for value in items:
            if value == None:
                # already added
                continue
            self._combo.addItem(value, value)
    except RuntimeError:
        pass

class DualComboBoxStatic(base.DualComboBoxBase):
    def userrole_value(self):
        return self._combo.itemData(self._combo.currentIndex(), QtCore.Qt.UserRole)

    def userrole_set_value(self, value):
        self._combo.setCurrentIndex(self._combo.findData(value, QtCore.Qt.UserRole))
        self._redit.setText(self._combo.currentText())


def pyhacc_static_settings_combo(settings_name):
    def pyhacc_static_settings_factory(parent, all_option=False):
        Klass = apputils.as_modifiable(DualComboBoxStatic)
        Klass.STATIC_SETTINGS_NAME = settings_name
        Klass.value = DualComboBoxStatic.userrole_value
        Klass.setValue = DualComboBoxStatic.userrole_set_value
        Klass.load_static_settings = load_static_settings
        w = Klass(parent)
        w.all_option = all_option
        w.load_static_settings()
        w._combo.currentIndexChanged.connect(lambda *args: w.setWidgetModified(True))
        w._combo.currentIndexChanged.connect(lambda *args: w.setValueApplied())
        return w
    return pyhacc_static_settings_factory

def load_static_settings_value(self):
    try:
        self._combo.clear()
        items = static_settings(self.STATIC_SETTINGS_NAME, withkey=True)
        for shown, value in items:
            self._combo.addItem(shown, value)
    except RuntimeError:
        pass

def pyhacc_static_settings_value_combo(settings_name):
    def pyhacc_static_settings_value_factory(parent):
        Klass = apputils.as_modifiable(DualComboBoxStatic)
        Klass.STATIC_SETTINGS_NAME = settings_name
        Klass.value = DualComboBoxStatic.userrole_value
        Klass.setValue = DualComboBoxStatic.userrole_set_value
        Klass.load_static_settings = load_static_settings_value
        w = Klass(parent)
        w.load_static_settings()
        w._combo.currentIndexChanged.connect(lambda *args: w.setWidgetModified(True))
        w._combo.currentIndexChanged.connect(lambda *args: w.setValueApplied())
        return w
    return pyhacc_static_settings_value_factory

def pyhacc_account_tuple_edit(parent):
    Klass = apputils.as_modifiable(AccountEdit)
    Klass.value = Klass.get_value_mini
    Klass.setValue = Klass.set_value_mini
    w = Klass(parent)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w

def pyhacc_account_acc_name_edit(parent):
    Klass = apputils.as_modifiable(AccountEdit)
    Klass.value = lambda self: self.text()
    Klass.value2 = Klass.get_value_mini
    Klass.setValue = lambda self, value: self.setText(value)
    Klass.setValue2 = Klass.set_value_mini
    w = Klass(parent)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w

def pyhacc_account_autoid_edit(parent):
    Klass = apputils.as_modifiable(AccountEdit)
    Klass.value = Klass.get_static_key
    Klass.value2 = Klass.get_value_mini
    Klass.setValue = Klass.set_static_key
    w = Klass(parent)
    w.textChanged.connect(lambda *args: w.setWidgetModified(True))
    w.editingFinished.connect(lambda *args: w.setValueApplied())
    return w

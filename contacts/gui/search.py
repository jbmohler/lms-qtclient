from PySide2 import QtCore, QtWidgets
import client.qt as qt
import apputils
import apputils.widgets as widgets


class PersonaMixin:
    @property
    def full_name(self):
        if self.f_name in ['', None]:
            return self.l_name
        else:
            return self.f_name + ' ' + self.l_name

class BitMixin:
    @property
    def html_view(self):
        bd = self.bit_data
        if self.bit_type == 'street_addresses':
            addr3 = [
                    bd['city'] if bd['city'] not in ['', None] else None,
                    bd['state'] if bd['state'] not in ['', None] else None,
                    bd['zip'] if bd['zip'] not in ['', None] else None]

            addresses = [
                    bd['address1'] if bd['address1'] not in ['', None] else None,
                    bd['address2'] if bd['address2'] not in ['', None] else None,
                    ' '.join(addr3),
                    bd['country'] if bd['country'] not in ['', None] else None]
            x = '\n'.join([x for x in addresses if x != None])
        elif self.bit_type == 'urls':
            lines = []
            lines.append(('URL', bd['url']))
            if bd['username'] not in ['', None] or bd['password'] not in ['', None]:
                lines.append(('Username', bd['username']))
                lines.append(('Password', bd['password']))
            x = '<br />'.join(['{}: {}'.format(*x) for x in lines])
        elif self.bit_type == 'phone_numbers':
            x = bd['number']
        elif self.bit_type == 'email_addresses':
            x = bd['email']
        else:
            x = str(self.bit_data)
        if self.memo in ['', None]:
            return x
        else:
            return '{}\n(memo)'.format(x)


class BitUrlView(QtWidgets.QDialog):
    pass

class BitPhoneView(QtWidgets.QDialog):
    pass

class BitEmailView(QtWidgets.QDialog):
    pass

class BitStreetView(QtWidgets.QDialog):
    pass

class ContactHeadView(QtWidgets.QDialog):
    pass

class ContactView(QtWidgets.QWidget):
    TITLE = 'Contact'
    ID = 'contact-view'
    URL_PERSONA = 'api/persona/{}'

    def __init__(self, parent, session):
        super(ContactView, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = QtWidgets.QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.action_triggered)
        self.layout.addWidget(self.view)

        self.clear()

    def action_triggered(self, url):
        print(url)

    def clear(self):
        self.view.setHtml("""
<html>
<body>
<p style="color: gray">select a contact</p>
</body>
</html>
""")

    def highlight(self, row):
        if row == None:
            self.clear()
            return
        self.backgrounder(self.load_view, self.client.get, self.URL_PERSONA, row.id)

    def load_view(self):
        content = yield apputils.AnimateWait(self)

        persona = content.named_table('persona', mixin=PersonaMixin).rows[0]
        bits = content.named_table('bits', mixin=BitMixin)

        chunks = []
        chunks.append('<h1>{}</h1>'.format(persona.full_name))
        chunks.append(persona.memo)
        for b in bits.rows:
            chunks.append(b.bit_type)
            chunks.append(b.html_view)

        self.view.setHtml("""
<html>
<body>
{}
</body>
</html>
""".format("<br />".join(chunks)))


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

        self.sublay = qt.RevealedSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TableView()
        self.grid.setSortingEnabled(True)
        self.grid.verticalHeader().hide()
        self.gridmgr = qt.GridManager(self.grid, self)
        self.sublay.addWidget(self.grid)

        self.sidebar = ContactView(self, session)
        self.sublay.addWidget(self.sidebar)
        self.layout.addWidget(self.sublay)

        self.client = session.std_client()

        self.preview_timer = qt.StdActionPause()
        self.preview_timer.timeout.connect(lambda: self.sidebar.highlight(self.gridmgr.selected_row()))
        self.gridmgr.current_row_update.connect(self.preview_timer.ui_start)
 
        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.search_now)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

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

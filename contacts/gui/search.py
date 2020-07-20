import functools
import urllib.parse
from PySide2 import QtCore, QtWidgets
import client.qt as qt
import cliutils
import apputils
import apputils.widgets as widgets
from . import icons


class PersonaMixin:
    @property
    def full_name(self):
        if self.f_name in ["", None]:
            return self.l_name
        else:
            return self.f_name + " " + self.l_name


class BitMixin:
    @property
    def html_view(self):
        edurl = "local:bit/edit?id={}&type={}".format(self.id, self.bit_type)
        dturl = "local:bit/delete?id={}&type={}".format(self.id, self.bit_type)
        x = [
            '<a href="{}"><img src="{}"></a>'.format(
                edurl, "qrc:/contacts/default-edit.png"
            ),
            '<a href="{}"><img src="{}"></a>'.format(
                dturl, "qrc:/contacts/bit-delete.png"
            ),
            "<p>{}</p>".format(self.html_chunk()),
        ]
        return "<tr><td>{}{}</td><td>{}</td></tr>".format(x[0], x[1], x[2])

    def html_chunk(self):
        bd = self.bit_data
        if self.bit_type == "street_addresses":
            addr3 = [
                bd["city"] if bd["city"] not in ["", None] else "",
                bd["state"] if bd["state"] not in ["", None] else "",
                bd["zip"] if bd["zip"] not in ["", None] else "",
            ]

            addresses = [
                bd["address1"] if bd["address1"] not in ["", None] else None,
                bd["address2"] if bd["address2"] not in ["", None] else None,
                " ".join(addr3),
                bd["country"] if bd["country"] not in ["", None] else None,
            ]
            x = "<br />".join([x for x in addresses if x != None])
        elif self.bit_type == "urls":
            lines = []
            xurl = (
                '<a href="{0}">{0}</a>'.format(bd["url"])
                if bd["url"] not in ["", None]
                else " -- "
            )
            lines.append(("URL", xurl))
            if bd["username"] not in ["", None] or bd["password"] not in ["", None]:
                lines.append(("Username", bd["username"]))
                localurl = "local:bit/copy-password?password={}".format(
                    urllib.parse.quote(bd["password"])
                )
                lines.append(
                    ("Password", '<a href="{}">Copy Password</a>'.format(localurl))
                )
            x = "<br />".join(["{}: {}".format(*x) for x in lines])
        elif self.bit_type == "phone_numbers":
            x = bd["number"]
        elif self.bit_type == "email_addresses":
            x = bd["email"]
        else:
            x = str(self.bit_data)
        if self.name not in ["", None]:
            x = "<b>{}: </b>".format(self.name) + x
        if self.memo in ["", None]:
            return x
        else:
            return "{}\n(memo)".format(x)

    def delete_message(self):
        msg = "Are you sure that you want to delete this contact data?"
        return msg


class BasicBitView(QtWidgets.QDialog):
    ID = "persona-bit-editor"
    TITLE = "Contact Bit"

    def __init__(self, parent):
        super(BasicBitView, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.backgrounder = apputils.Backgrounder(self)

        self.binder = qt.Binder(self)

        self.form = self.prepare_form_body(self.binder)

        self.buttons = QtWidgets.QDialogButtonBox()

        self.buttons.addButton(self.buttons.Ok).clicked.connect(self.accept)
        self.buttons.addButton(self.buttons.Cancel).clicked.connect(self.reject)

        self.add_buttons()

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttons)

    def add_buttons(self):
        pass

    def load(self, client, bb):
        self.client = client

        self.backgrounder(
            self._load,
            self.client.get,
            "api/persona/{}/bit/{}",
            bb.persona_id,
            bb.id,
            bit_type=bb.bit_type,
        )

    def load_new(self, client, per, bit_type):
        self.client = client

        self.backgrounder(
            self._load,
            self.client.get,
            "api/persona/{}/bit/new",
            per.id,
            bit_type=bit_type,
        )

    def _load(self):
        content = yield apputils.AnimateWait(self)

        self.bits = content.main_table()
        self.editrow = self.bits.rows[0]
        self.binder.bind(self.editrow, self.bits.columns)

    def accept(self):
        self.binder.save(self.editrow)

        with apputils.animator(self) as p:
            p.background(
                self.client.put,
                "api/persona/{}/bit/{}",
                self.editrow.persona_id,
                self.editrow.persona_id,
                files={"bit": self.bits.as_http_post_file()},
            )

        return super(BasicBitView, self).accept()


class BitUrlView(BasicBitView):
    def prepare_form_body(self, sb):
        sb = self.binder
        sb.construct("name", "basic")
        sb.construct("is_primary", "boolean", label="Primary")
        sb.construct("url", "basic")
        sb.construct("username", "basic")
        sb.construct("password", "basic")
        sb.construct("memo", "multiline")

        form = QtWidgets.QFormLayout()
        form.addRow("Name", sb.widgets["name"])
        form.addRow(None, sb.widgets["is_primary"])
        form.addRow("URL", sb.widgets["url"])
        form.addRow("Username", sb.widgets["username"])
        form.addRow("Password", sb.widgets["password"])
        form.addRow("Memo", sb.widgets["memo"])

        return form

    def add_buttons(self):
        self.buttons.addButton("Generate", self.buttons.ActionRole).clicked.connect(
            self.gen_new_password
        )

    def gen_new_password(self):
        dlg = QtWidgets.QDialog()

        dlg.layout = QtWidgets.QVBoxLayout(dlg)

        modes = ["pronounciable", "words", "random", "alphanumeric"]

        dlg.mode_edit = apputils.construct(
            "options", options=[(m.title(), m) for m in modes]
        )
        dlg.bits_edit = apputils.construct("integer")
        dlg.bits_edit.setValue(50)

        dlg.form = QtWidgets.QFormLayout()
        dlg.form.addRow("Mode", dlg.mode_edit)
        dlg.form.addRow("Bits", dlg.bits_edit)

        dlg.buttons = QtWidgets.QDialogButtonBox()

        dlg.buttons.addButton(dlg.buttons.Ok).clicked.connect(dlg.accept)
        dlg.buttons.addButton(dlg.buttons.Cancel).clicked.connect(dlg.reject)

        dlg.layout.addLayout(dlg.form)
        dlg.layout.addWidget(dlg.buttons)

        if dlg.exec_() == dlg.Accepted:
            with apputils.animator(self) as p:
                content = p.background(
                    self.client.get,
                    "api/password/generate",
                    mode=dlg.mode_edit.value(),
                    bits=dlg.bits_edit.value(),
                )

            apputils.information(self, content.keys["password"])


class BitPhoneView(BasicBitView):
    def prepare_form_body(self, sb):
        sb = self.binder
        sb.construct("name", "basic")
        sb.construct("is_primary", "boolean", label="Primary")
        sb.construct("number", "basic")
        sb.construct("memo", "multiline")

        form = QtWidgets.QFormLayout()
        form.addRow("Name", sb.widgets["name"])
        form.addRow(None, sb.widgets["is_primary"])
        form.addRow("Phone No", sb.widgets["number"])
        form.addRow("Memo", sb.widgets["memo"])

        return form


class BitEmailView(BasicBitView):
    def prepare_form_body(self, sb):
        sb = self.binder
        sb.construct("name", "basic")
        sb.construct("is_primary", "boolean", label="Primary")
        sb.construct("email", "basic")
        sb.construct("memo", "multiline")

        form = QtWidgets.QFormLayout()
        form.addRow("Name", sb.widgets["name"])
        form.addRow(None, sb.widgets["is_primary"])
        form.addRow("E-Mail", sb.widgets["email"])
        form.addRow("Memo", sb.widgets["memo"])

        return form


class BitStreetView(BasicBitView):
    pass


class EditPersona(QtWidgets.QDialog):
    TITLE = "Persona Edit View"
    ID = "dlg-edit-persona"

    def __init__(self, parent):
        super(EditPersona, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.backgrounder = apputils.Backgrounder(self)

        self.binder = qt.Binder(self)

        sb = self.binder
        sb.construct("title", "basic")
        sb.construct("f_name", "basic")
        sb.construct("l_name", "basic")
        sb.construct("memo", "multiline")
        sb.construct("birthday", "date")

        self.form = QtWidgets.QFormLayout()
        self.form.addRow("Title", sb.widgets["title"])
        self.form.addRow("First Name", sb.widgets["f_name"])
        self.form.addRow("Last Name", sb.widgets["l_name"])
        self.form.addRow("Memo", sb.widgets["memo"])
        self.form.addRow("Birthday", sb.widgets["birthday"])

        self.buttons = QtWidgets.QDialogButtonBox()
        self.buttons.addButton(self.buttons.Ok).clicked.connect(self.accept)
        self.buttons.addButton(self.buttons.Cancel).clicked.connect(self.reject)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttons)

    def load(self, client, persona):
        self.client = client

        self.backgrounder(self._load, self.client.get, "api/persona/{}", persona.id)

    def load_new(self, client):
        self.client = client

        self.backgrounder(self._load, self.client.get, "api/persona/new")

    def _load(self):
        content = yield apputils.AnimateWait(self)

        self.persona = content.main_table()
        self.editrow = self.persona.rows[0]
        self.binder.bind(self.editrow, self.persona.columns)

    def accept(self):
        self.binder.save(self.editrow)

        with apputils.animator(self) as p:
            p.background(
                self.client.put,
                "api/persona/{}",
                self.editrow.id,
                files={"persona": self.persona.as_http_post_file()},
            )

        return super(EditPersona, self).accept()


class ContactView(QtWidgets.QWidget):
    TITLE = "Contact"
    ID = "contact-view"
    URL_PERSONA = "api/persona/{}"

    def __init__(self, parent, session):
        super(ContactView, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)
        self.btn_new = self.buttons.addButton(
            "New", self.buttons.ActionRole
        ).clicked.connect(self.cmd_new_persona)
        self.btn_edit = self.buttons.addButton(
            "Edit", self.buttons.ActionRole
        ).clicked.connect(self.cmd_edit_persona)
        self.btn_newbit = self.buttons.addButton("New Bit", self.buttons.ActionRole)
        self.bitmenu = QtWidgets.QMenu()
        self.bitmenu.addAction("URL/Login...").triggered.connect(
            functools.partial(self.cmd_newbit, "urls")
        )
        self.bitmenu.addAction("E-Mail...").triggered.connect(
            functools.partial(self.cmd_newbit, "email_addresses")
        )
        self.bitmenu.addAction("Phone...").triggered.connect(
            functools.partial(self.cmd_newbit, "phone_numbers")
        )
        self.bitmenu.addAction("Street Address...").triggered.connect(
            functools.partial(self.cmd_newbit, "street_addresses")
        )
        self.btn_newbit.setMenu(self.bitmenu)

        self.layout.addWidget(self.buttons)

        self.view = QtWidgets.QTextBrowser()
        self.view.setStyleSheet("QTextEdit { font-size: 14px }")
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.action_triggered)
        self.layout.addWidget(self.view)

        self.clear()

    def cmd_new_persona(self, bittype):
        dlg = EditPersona(self)
        dlg.load_new(self.client)

        if dlg.Accepted == dlg.exec_():
            self.reload()

    def cmd_edit_persona(self, bittype):
        dlg = EditPersona(self)
        dlg.load(self.client, self.persona)

        if dlg.Accepted == dlg.exec_():
            self.reload()

    def cmd_newbit(self, bittype):
        dlgclass = {
            "street_addresses": BitStreetView,
            "phone_numbers": BitPhoneView,
            "urls": BitUrlView,
            "email_addresses": BitEmailView,
        }

        dlg = dlgclass[bittype](self)
        dlg.load_new(self.client, self.persona, bittype)

        if dlg.Accepted == dlg.exec_():
            self.reload()

    def action_triggered(self, url):
        if url.scheme() == "local":
            values = qt.url_params(url)
            if url.path() == "bit/copy-password":
                app = QtCore.QCoreApplication.instance()
                app.clipboard().setText(values["password"])
            if url.path() == "bit/edit":
                bitmap = {(x.bit_type, x.id): x for x in self.bits.rows}
                bb = bitmap[(values["type"], values["id"])]

                dlgclass = {
                    "street_addresses": BitStreetView,
                    "phone_numbers": BitPhoneView,
                    "urls": BitUrlView,
                    "email_addresses": BitEmailView,
                }

                dlg = dlgclass[values["type"]](self)
                dlg.load(self.client, bb)

                if dlg.Accepted == dlg.exec_():
                    self.reload()
            if url.path() == "bit/delete":
                bitmap = {(x.bit_type, x.id): x for x in self.bits.rows}
                bb = bitmap[(values["type"], values["id"])]
                msg = bb.delete_message()
                if "Yes" == apputils.message(self, msg, buttons=["Yes", "No"]):
                    with apputils.animator(self):
                        self.client.delete(
                            "api/persona/{}/bit/{}".format(
                                self.persona.id, bb.id
                            )
                        )
                        self.reload()
        else:
            cliutils.xdg_open(url.toString())

    def clear(self):
        self.view.setHtml(
            """
<html>
<body>
<p style="color: gray">select a contact</p>
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
            self.load_view, self.client.get, self.URL_PERSONA, self.loadrow.id
        )

    def load_view(self):
        content = yield apputils.AnimateWait(self)

        self.persona = content.named_table("persona", mixin=PersonaMixin).rows[0]
        self.bits = content.named_table("bits", mixin=BitMixin)

        chunks = []
        chunks.append("<h1>{}</h1>".format(self.persona.full_name))
        if self.persona.memo != None:
            chunks.append(self.persona.memo.replace("\n", "<br />"))

        tablerows = []
        for b in self.bits.rows:
            # chunks.append(b.bit_type)
            tablerows.append(b.html_view)
        chunks.append('<table cellpadding="4">' + "\n".join(tablerows) + "</table>")

        self.view.setHtml(
            """
<html>
<body>
{}
</body>
</html>
""".format(
                "".join(["\n".join(["<p>", c, "</p>", ""]) for c in chunks])
            )
        )


class ContactsList(QtWidgets.QWidget):
    TITLE = "Contacts"
    ID = "contact-search"
    URL_SEARCH = "api/personas/list"

    def __init__(self, parent, session):
        super(ContactsList, self).__init__(parent)

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

        self.sidebar = ContactView(self, session)
        self.sublay.addWidget(self.sidebar)
        self.layout.addWidget(self.sublay)

        self.client = session.std_client()

        self.preview_timer = qt.StdActionPause()
        self.preview_timer.timeout.connect(
            lambda: self.sidebar.highlight(self.gridmgr.selected_row())
        )
        self.gridmgr.current_row_update.connect(self.preview_timer.ui_start)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.search_now)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

        self.geo = apputils.WindowGeometry(self, size=False, position=False, grids=[self.grid])

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

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.table)


def list_widget(parent, session):
    view = ContactsList(parent, session)
    return view

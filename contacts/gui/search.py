import functools
import urllib.parse
from PySide6 import QtCore, QtWidgets
import client.qt as qt
import cliutils
import apputils
import apputils.widgets as widgets
from . import icons


class PersonaMixin:
    pass


class PasswordGenerator(QtWidgets.QDialog):
    MODES = ["pronounciable", "words", "random", "alphanumeric"]

    def __init__(self, parent):
        super(PasswordGenerator, self).__init__(parent)

        self.setWindowTitle("Password Generator")

        self.layout = QtWidgets.QVBoxLayout(self)

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.regen4)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(20)
        self.slider.setMaximum(120)
        self.slider.setValue(50)
        self.slider.valueChanged.connect(lambda _: self.load_timer.ui_start())

        self.layout.addWidget(self.slider)

        self.edits = {}

        for m in self.MODES:
            row = QtWidgets.QHBoxLayout()

            edit = QtWidgets.QLineEdit()
            self.edits[m] = edit
            row.addWidget(edit)

            b = QtWidgets.QPushButton(f"Choose {m.title()}")
            b.clicked.connect(lambda *, mode=m: self.accept_mode(mode))
            row.addWidget(b)

            self.layout.addLayout(row)

        self.setMinimumWidth(60 * apputils.get_char_width())

    def regen4(self):
        value = self.slider.value()

        with apputils.animator(self) as p:
            for m in self.MODES:
                content = p.background(
                    self.client.get, "api/password/generate", mode=m, bits=value
                )

                pwd = content.keys["password"]
                self.edits[m].setText(pwd)

    def accept_mode(self, mode):
        self.new_password = self.edits[mode].text()
        self.accept()


class BitMixin:
    def html_view(self, printable=False):
        htmlbit = f"<p>{self.html_chunk(printable)}</p>"
        if printable:
            bt = self.bit_type[0].upper()
            line1 = f"<tr><td><b>{bt}</b></td><td style='border-top: 1pt solid #686868;'>{htmlbit}</td></tr>"
            if self.memo not in ["", None]:
                memo = self.memo.replace("\n", "<br />")
                line2 = f"<tr><td></td><td style='margin-left: 40px; background: #E8E8E8;'>{memo}</td></tr>"
                return "\n".join([line1, line2])
            else:
                return line1
        else:
            edurl = f"local:bit/edit?id={self.id}&type={self.bit_type}"
            dturl = f"local:bit/delete?id={self.id}&type={self.bit_type}"
            commands = [
                f'<a href="{edurl}"><img src="qrc:/contacts/default-edit.png"></a>',
                f'<a href="{dturl}"><img src="qrc:/contacts/bit-delete.png"></a>',
            ]
            return f"<tr><td>{commands[0]}{commands[1]}</td><td>{htmlbit}</td></tr>"

    def html_chunk(self, printable):
        es = lambda x: x if x is not None else ""
        ns = lambda x: x if x != "" else None
        bd = self.bit_data
        if self.bit_type == "street_addresses":
            addr3 = [es(bd["city"]), es(bd["state"]), es(bd["zip"])]

            addresses = [
                ns(bd["address1"]),
                ns(bd["address2"]),
                " ".join(addr3),
                ns(bd["country"]),
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
                if ns(bd["username"]) is None:
                    un = "(empty)"
                else:
                    un = bd["username"]
                lines.append(("Username", un))
                if ns(bd["password"]) is None:
                    hlink = "(empty)"
                elif printable:
                    hlink = f'<code>{bd["password"]}</code>'
                else:
                    qpass = urllib.parse.quote(bd["password"])
                    localurl = f"local:bit/copy-password?password={qpass}"
                    hlink = f'<a href="{localurl}">Copy Password</a>'
                lines.append(("Password", hlink))
            x = "<br />".join(["{}: {}".format(*x) for x in lines])
        elif self.bit_type == "phone_numbers":
            x = bd["number"]
        elif self.bit_type == "email_addresses":
            x = bd["email"]
        else:
            x = str(self.bit_data)
        if self.name not in ["", None]:
            x = f"<b>{self.name}: </b>" + x
        # note: when deliverying print-ready, we take the memo outside
        if self.memo in ["", None] or printable:
            return x
        else:
            return f"{x}\n(memo)"

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
                self.editrow.id,
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
        dlg = PasswordGenerator(self)
        dlg.client = self.client
        dlg.regen4()

        if dlg.exec_() == dlg.Accepted:
            if self.editrow.password not in ["", None]:
                m = "" if self.editrow.memo in ["", None] else self.editrow.memo
                self.editrow.memo = f"Last password:  {self.editrow.password}\n{m}"

            self.editrow.password = dlg.new_password
            self.binder.load(self.editrow)


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


class EntityTaggerMixin:
    def _rtlib_init_(self):
        self.subtags = []

    @property
    def is_tagged(self):
        return self.id in self.ambient_persona.active_tag_list()

    @is_tagged.setter
    def is_tagged(self, v):
        if v:
            self.ambient_persona.add_tag(self)
        else:
            self.ambient_persona.remove_tag(self)


class EntityEditMixin:
    def _rtlib_init_(self):
        self.tags_add = []
        self.tags_remove = []

    def active_tag_list(self):
        orig_tags = [] if self.tag_ids == None else self.tag_ids

        return set(orig_tags).difference(self.tags_remove).union(self.tags_add)

    def add_tag(self, tag):
        orig_tags = [] if self.tag_ids == None else self.tag_ids

        try:
            self.tags_remove.remove(tag.id)
        except ValueError:
            pass
        if tag.id not in orig_tags:
            self.tags_add.append(tag.id)

    def remove_tag(self, tag):
        orig_tags = [] if self.tag_ids == None else self.tag_ids

        try:
            self.tags_add.remove(tag.id)
        except ValueError:
            pass
        if tag.id in orig_tags:
            self.tags_remove.append(tag.id)


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
        sb.construct("l_name#company", "basic")
        sb.construct("l_name#individual", "basic")
        sb.construct("memo", "multiline")
        sb.construct("birthday", "date")
        sb.construct("organization", "basic")

        self.tabs = QtWidgets.QTabWidget()

        self.tab_main_info = QtWidgets.QWidget()
        self.tab_main_info_layout = QtWidgets.QVBoxLayout(self.tab_main_info)

        self.name_radio_company = QtWidgets.QRadioButton("&Company")
        self.name_radio_individual = QtWidgets.QRadioButton("&Individual")
        self.name_radio_grp = QtWidgets.QButtonGroup()
        self.name_radio_grp.setExclusive(True)
        self.name_radio_grp.addButton(self.name_radio_company, 1)
        self.name_radio_grp.addButton(self.name_radio_individual, 2)
        self.name_radio_layout = QtWidgets.QHBoxLayout()
        self.tab_main_info_layout.addLayout(self.name_radio_layout)
        for btn in self.name_radio_grp.buttons():
            self.name_radio_layout.addWidget(btn)

        self.namestack = QtWidgets.QStackedWidget()

        self.m2w = QtWidgets.QWidget()
        m2 = QtWidgets.QFormLayout(self.m2w)
        m2.addRow("Name", sb.widgets["l_name#company"])
        self.namestack.addWidget(self.m2w)

        self.m3w = QtWidgets.QWidget()
        m3 = QtWidgets.QFormLayout(self.m3w)
        m3.addRow("Title", sb.widgets["title"])
        m3.addRow("First Name", sb.widgets["f_name"])
        m3.addRow("Last Name", sb.widgets["l_name#individual"])
        self.namestack.addWidget(self.m3w)

        self.tab_main_info_layout.addWidget(self.namestack)

        self.editrow = None

        def join_null(values, sep):
            values = [v for v in values if v not in ["", None]]
            return sep.join(values)

        def stack_update(id_, toggled):
            if self.editrow:
                row = self.editrow
                if id_ == 1:
                    # selected corporate entity
                    row.l_name = join_null([row.title, row.f_name, row.l_name], " ")
                    row.f_name = None
                    row.title = None
                    for attr in ["l_name", "f_name", "title"]:
                        self.binder.reset_from_row(row, attr)
                if toggled:
                    row.corporate_entity = {1: True, 2: False}[id_]
            if toggled:
                w = {1: self.m2w, 2: self.m3w}
                self.namestack.setCurrentWidget(w[id_])

        self.name_radio_grp.idToggled.connect(stack_update)
        self.name_radio_company.setChecked(True)

        m5 = QtWidgets.QFormLayout()
        m5.addRow("Memo", sb.widgets["memo"])
        self.tab_main_info_layout.addLayout(m5)

        self.tab_aux_info = QtWidgets.QWidget()
        m4 = QtWidgets.QFormLayout(self.tab_aux_info)
        m4.addRow("Birthday", sb.widgets["birthday"])
        m4.addRow("Organization", sb.widgets["organization"])

        self.tab_tags_info = QtWidgets.QWidget()
        m4 = QtWidgets.QVBoxLayout(self.tab_tags_info)
        self.tags_grid = widgets.TreeView()
        self.tags_grid.header().hide()
        self.tags_gridmgr = qt.GridManager(self.tags_grid, self)
        m4.addWidget(self.tags_grid)

        self.tabs.addTab(self.tab_main_info, "Contact")
        self.tabs.addTab(self.tab_tags_info, "Tags")
        self.tabs.addTab(self.tab_aux_info, "Extra")

        self.buttons = QtWidgets.QDialogButtonBox()
        self.buttons.addButton(self.buttons.Ok).clicked.connect(self.accept)
        self.buttons.addButton(self.buttons.Cancel).clicked.connect(self.reject)

        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.buttons)

    def load(self, client, persona):
        self.client = client

        self.backgrounder(self._load, self.client.get, "api/persona/{}", persona.id)

    def load_new(self, client):
        self.client = client

        self.backgrounder(self._load, self.client.get, "api/persona/new")

    def _load(self):
        content = yield apputils.AnimateWait(self)

        self.persona = content.main_table(mixin=EntityEditMixin)

        self.editrow = None
        if self.persona.rows[0].corporate_entity:
            self.name_radio_company.setChecked(True)
        else:
            self.name_radio_individual.setChecked(True)

        self.editrow = self.persona.rows[0]

        class ThisPersonaMixin(EntityTaggerMixin):
            pass

        ThisPersonaMixin.ambient_persona = self.editrow

        # TODO cache this
        tags = self.client.get("api/tags/list")
        self.tagstable = tags.main_table(mixin=ThisPersonaMixin)

        self.tagmap = {tag.id: tag for tag in self.tagstable.rows}

        for row in self.tagstable.rows:
            if row.parent_id != None:
                parent = self.tagmap[row.parent_id]
                parent.subtags.append(row)

        columns = [apputils.field("name", "Name", check_attr="is_tagged")]

        self.tags_model = apputils.ObjectQtModel(columns, descendant_attr="subtags")

        self.tags_grid.setModel(self.tags_model)
        self.tags_model.set_rows(
            [tag for tag in self.tagstable.rows if tag.parent_id == None]
        )

        self.binder.bind(self.editrow, self.persona.columns)

    def accept(self):
        self.binder.save(self.editrow)

        with apputils.animator(self) as p:
            p.background(
                self.client.put,
                "api/persona/{}",
                self.editrow.id,
                files={
                    "persona": self.persona.as_http_post_file(
                        exclusions=["entity_name", "tag_ids"]
                    ),
                    "tagdeltas": self.persona.as_http_post_file(
                        inclusions=["tags_add", "tags_remove"]
                    ),
                },
            )

        return super(EditPersona, self).accept()


class ContactView(QtWidgets.QWidget):
    TITLE = "Contact"
    ID = "contact-view"
    URL_PERSONA = "api/persona/{}"

    update_ambient = QtCore.Signal(str)

    def __init__(self, parent, state):
        super(ContactView, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.setObjectName(self.ID)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = state.session.std_client()
        self.exports_dir = state.exports_dir

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Horizontal)

        # Entity Button with menu
        self.btn_entity = self.buttons.addButton("Entity", self.buttons.ActionRole)
        self.entmenu = QtWidgets.QMenu()
        self.entmenu.addAction("New").triggered.connect(self.cmd_new_persona)
        self.entmenu.addSeparator()
        self.entmenu.addAction("Edit").triggered.connect(self.cmd_edit_persona)
        self.entmenu.addAction("Printable").triggered.connect(self.cmd_printable)
        self.entmenu.addAction("Delete").triggered.connect(self.cmd_delete_persona)
        self.btn_entity.setMenu(self.entmenu)

        # Bit Button with menu
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

    def cmd_printable(self):
        chunks = []
        chunks.append(f"<h1>{self.persona.entity_name}</h1>")
        if self.persona.memo != None:
            chunks.append(self.persona.memo.replace("\n", "<br />"))

        tablerows = []
        for b in self.bits.rows:
            # chunks.append(b.bit_type)
            tablerows.append(b.html_view(printable=True))
        chunks.append('<table cellpadding="4">' + "\n".join(tablerows) + "</table>")

        joined = "".join(["\n".join(["<p>", c, "</p>", ""]) for c in chunks])
        html = f"""
<html>
<body>
{joined}
</body>
</html>
"""

        fname = self.exports_dir.user_output_filename(
            f"persona-{self.persona.entity_name}", "html"
        )

        with open(fname, "w") as htmlfile:
            htmlfile.write(html)

        qt.xlsx_start_file(self.window(), fname)

    def cmd_new_persona(self):
        dlg = EditPersona(self)
        dlg.load_new(self.client)

        if dlg.Accepted == dlg.exec_():
            self.update_ambient.emit(dlg.editrow.id)
            # self.reload()

    def cmd_edit_persona(self):
        dlg = EditPersona(self)
        dlg.load(self.client, self.persona)

        if dlg.Accepted == dlg.exec_():
            self.update_ambient.emit(dlg.editrow.id)
            self.reload()

    def cmd_delete_persona(self):
        row = self.persona
        if "Yes" == apputils.message(
            self.window(),
            f"Are you sure that you wish to delete the entity '{row.entity_name}'?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.URL_PERSONA, row.id)
                self.reload()
            except:
                qt.exception_message(self.window(), "The entity could not be deleted.")

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
                        self.client.delete(f"api/persona/{self.persona.id}/bit/{bb.id}")
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
        chunks.append(f"<h1>{self.persona.entity_name}</h1>")
        if self.persona.memo != None:
            chunks.append(self.persona.memo.replace("\n", "<br />"))

        tablerows = []
        for b in self.bits.rows:
            # chunks.append(b.bit_type)
            tablerows.append(b.html_view())
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


class PersonaCommandSidebar(QtCore.QObject):
    SRC_INSTANCE_URL = "api/persona/{}"
    refresh = QtCore.Signal()

    def __init__(self, parent, state):
        super(PersonaCommandSidebar, self).__init__(parent)
        self.client = state.session.std_client()
        self.added = False

    def init_grid_menu(self, gridmgr):
        self.gridmgr = gridmgr

        if not self.added:
            self.added = True
            self.gridmgr.add_action("&Add Entity", triggered=self.cmd_add_persona)
            self.gridmgr.add_action("&Edit Entity", triggered=self.cmd_edit_persona)
            self.gridmgr.add_action("&Delete Entity", triggered=self.cmd_delete_persona)

    def window(self):
        return self.gridmgr.grid.window()

    def cmd_add_persona(self):
        dlg = EditPersona(self.window())
        dlg.load_new(self.client)

        if dlg.Accepted == dlg.exec_():
            self.refresh.emit()

    def cmd_edit_persona(self, row):
        dlg = EditPersona(self.window())
        dlg.load(self.client, row)

        if dlg.Accepted == dlg.exec_():
            self.refresh.emit()

    def cmd_delete_persona(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f"Are you sure that you wish to delete the entity '{row.entity_name}'?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(self.SRC_INSTANCE_URL, row.id)
                self.refresh.emit()
            except:
                qt.exception_message(self.window(), "The entity could not be deleted.")


class ContactsList(QtWidgets.QWidget):
    TITLE = "Contacts"
    ID = "contact-search"
    URL_SEARCH = "api/personas/list"

    def __init__(self, parent, state):
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

        self.sidebar2 = PersonaCommandSidebar(self, state)
        if self.sidebar2 != None and hasattr(self.sidebar2, "init_grid_menu"):
            self.sidebar2.init_grid_menu(self.gridmgr)

        self.sidebar = ContactView(self, state)
        self.sidebar.update_ambient.connect(self.reload_from_persona)
        self.sublay.addWidget(self.sidebar)
        self.layout.addWidget(self.sublay)

        self.client = state.session.std_client()

        self.preview_timer = qt.StdActionPause()
        self.preview_timer.timeout.connect(
            lambda: self.sidebar.highlight(self.gridmgr.selected_row())
        )
        self.gridmgr.current_row_update.connect(self.preview_timer.ui_start)

        self.last_edit = None

        self.load_timer = qt.StdActionPause()
        self.load_timer.timeout.connect(self.search_now)
        self.search_edit.applyValue.connect(self.load_timer.ui_start)

        self.change_listener = qt.ChangeListener(
            self.backgrounder, self.client, self.push_refresh, "personas"
        )

        self.geo = apputils.WindowGeometry(
            self, size=False, position=False, grids=[self.grid]
        )

    def reload_from_persona(self, per_id):
        self.last_edit = per_id
        self.base_refresh()

    def search_now(self):
        self.last_edit = None
        self.base_refresh()

    def push_refresh(self):
        self.base_refresh()

    def base_refresh(self):
        self.backgrounder(
            self.load_data,
            self.client.get,
            self.URL_SEARCH,
            frag=self.search_edit.value(),
            included=self.last_edit,
        )

    def load_data(self):
        content = yield apputils.AnimateWait(self)
        self.table = content.main_table()

        with self.geo.grid_reset(self.grid):
            self.gridmgr.set_client_table(self.table)

        i1 = None
        if self.last_edit != None:
            row = [xx for xx in self.table.rows if xx.id == self.last_edit]
            if len(row) > 0:
                i1, _ = self.grid.model().index_object(row[0])
        elif len(self.table.rows) == 1:
            row = self.table.rows[:]
            i1, _ = self.grid.model().index_object(row[0])
        if i1:
            self.grid.setCurrentIndex(i1)
            self.sidebar.highlight(row[0])

    def focus_search(self):
        def _focus_search():
            self.search_edit.setFocus(QtCore.Qt.PopupFocusReason)
            self.search_edit.selectAll()

        QtCore.QTimer.singleShot(100, _focus_search)

    def closeEvent(self, event):
        self.change_listener.close()
        return super(ContactsList, self).closeEvent(event)

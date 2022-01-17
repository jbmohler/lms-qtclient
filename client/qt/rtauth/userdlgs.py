import markupsafe
from PySide6 import QtCore, QtGui, QtWidgets
import apputils
import apputils.widgets as widgets
import client.qt as qt


class UserAddressDialog(QtWidgets.QDialog):
    TITLE = "User Address"
    ID = "dlg-edit-address"
    SRC_INSTANCE_URL = "api/user/{}/address/{}"

    def __init__(self, parent, session):
        super(UserAddressDialog, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.main = QtWidgets.QVBoxLayout(self)
        self.body = QtWidgets.QHBoxLayout()
        self.main.addLayout(self.body)

        options = [("Phone (SMS)", "phone"), ("E-mail", "email")]

        self.bind = qt.Binder(self)
        form = QtWidgets.QFormLayout()
        form.addRow(
            "&Type", self.bind.construct("addr_type", "options", options=options)
        )
        form.addRow("&Address", self.bind.construct("address", "basic"))
        form.addRow(self.bind.construct("is_primary", "boolean", label="&Primary"))
        form.addRow(
            self.bind.construct("is_2fa_target", "boolean", label="&Use for 2FA device")
        )
        self.label_verified = QtWidgets.QLabel()
        form.addRow(self.label_verified)

        self.body.addLayout(form)

        QDB = QtWidgets.QDialogButtonBox
        buttons = QDB(QDB.Ok | QDB.Cancel, QtCore.Qt.Horizontal)
        self.main.addWidget(buttons)
        buttons.accepted.connect(self.cmd_accept)
        buttons.rejected.connect(self.reject)

    def loadrec(self, userid, addrid):
        self.userid = userid
        # NOTE: addrid may be new
        self.addrid = addrid

        with self.backgrounder.bulk(self.load_main) as bulk:
            bulk("addr_content", self.client.get, self.SRC_INSTANCE_URL, userid, addrid)

    def load_main(self, addr_content):
        self.data = addr_content
        self.addresses = self.data.main_table()
        self.editrec = self.addresses.rows[0]

        self.bind.bind(self.editrec, self.addresses.columns)

    def cmd_accept(self):
        if self.save():
            self.accept()

    def save(self):
        row = self.addresses.rows[0]

        files = {"address": self.addresses.as_http_post_file()}
        try:
            row = self.addresses.rows[0]
            self.client.put(self.SRC_INSTANCE_URL, self.userid, row.id, files=files)
            return True
        except:
            qt.exception_message(
                self, "There was an error adding/updating the user address."
            )


class EntityTaggerMixin:
    def _rtlib_init_(self):
        self.subtags = []

    @property
    def is_tagged(self):
        return self.id in self.ambient_user.active_tag_list()

    @is_tagged.setter
    def is_tagged(self, v):
        if v:
            self.ambient_user.add_tag(self)
        else:
            self.ambient_user.remove_tag(self)


class EntityEditMixin:
    def _rtlib_init_(self):
        self.roles_add = []
        self.roles_del = []

    def active_tag_list(self):
        orig_tags = [] if self.roles == None else self.roles

        return set(orig_tags).difference(self.roles_del).union(self.roles_add)

    def add_tag(self, tag):
        orig_tags = [] if self.roles == None else self.roles

        try:
            self.roles_del.remove(tag.id)
        except ValueError:
            pass
        if tag.id not in orig_tags:
            self.roles_add.append(tag.id)

    def remove_tag(self, tag):
        orig_tags = [] if self.roles == None else self.roles

        try:
            self.roles_add.remove(tag.id)
        except ValueError:
            pass
        if tag.id in orig_tags:
            self.roles_del.append(tag.id)


class AddressMixin:
    def html_view(self, printable=False):
        brtag = markupsafe.Markup("<br />")

        htmlbit = markupsafe.Markup("<p>{chunk}</p>").format(
            chunk=self.html_chunk(printable)
        )
        if printable:
            bt = self.bit_type[0].upper()
            line1 = markupsafe.Markup(
                "<tr><td><b>{bt}</b></td><td style='border-top: 1pt solid #686868;'>{htmlbit}</td></tr>"
            ).format(bt=bt, htmlbit=htmlbit)
            if self.memo not in ["", None]:
                memo = markupsafe.escape(self.memo).replace("\n", brtag)
                line2 = markupsafe.Markup(
                    "<tr><td></td><td style='margin-left: 40px; background: #E8E8E8;'>{memo}</td></tr>"
                ).format(memo=memo)
                return markupsafe.escape("\n").join([line1, line2])
            else:
                return line1
        else:
            edurl = markupsafe.Markup("local:address/edit?id={ss.id}").format(ss=self)
            dturl = markupsafe.Markup("local:address/delete?id={ss.id}").format(ss=self)
            commands = [
                markupsafe.Markup(
                    '<a href="{edurl}"><img src="qrc:/contacts/default-edit.png"></a>'
                ).format(edurl=edurl),
                markupsafe.Markup(
                    '<a href="{dturl}"><img src="qrc:/contacts/bit-delete.png"></a>'
                ).format(dturl=dturl),
            ]
            return markupsafe.Markup(
                "<tr><td>{commands[0]}{commands[1]}</td><td>{htmlbit}</td></tr>"
            ).format(commands=commands, htmlbit=htmlbit)

    def html_chunk(self, printable):
        brtag = markupsafe.Markup("<br />")

        line1 = markupsafe.Markup("{row.addr_type}: {row.address}").format(row=self)
        line2 = markupsafe.Markup("Primary") if self.is_primary else None
        line3 = markupsafe.Markup("2FA Target") if self.is_2fa_target else None
        line4 = markupsafe.Markup("Verified") if self.is_verified else None

        lines = [x for x in [line1, line2, line3, line4] if x is not None]
        return brtag.join(lines)


class UserDialog(QtWidgets.QDialog):
    TITLE = "Edit User Details"
    ID = "dlg-edit-persona"
    SRC_INSTANCE_URL = "api/user/{}"

    def __init__(self, parent, session):
        super(UserDialog, self).__init__(parent)

        self.setWindowTitle(self.TITLE)
        self.backgrounder = apputils.Backgrounder(self)
        self.client = session.std_client()

        self.main = QtWidgets.QVBoxLayout(self)
        self.body = QtWidgets.QHBoxLayout()
        self.main.addLayout(self.body)

        self.left = QtWidgets.QVBoxLayout()
        self.body.addLayout(self.left)
        self.right = QtWidgets.QVBoxLayout()
        self.body.addLayout(self.right)

        # User Form #
        self.chk_changeset_password = QtWidgets.QCheckBox("Change/Set Password")

        self.bind = qt.Binder(self)
        form = QtWidgets.QFormLayout()
        form.addRow("&Full Name", self.bind.construct("full_name", "basic"))
        form.addRow("&User Name", self.bind.construct("username", "basic"))

        form.addRow(self.chk_changeset_password)
        form.addRow("&Password", self.bind.construct("password", "basic"))
        form.addRow("&Password (confirm)", self.bind.construct("password2", "basic"))
        self.bind.widgets["password"].setEchoMode(QtWidgets.QLineEdit.Password)
        self.bind.widgets["password2"].setEchoMode(QtWidgets.QLineEdit.Password)
        self.chk_changeset_password.toggled.connect(self.toggle_changeset_password)

        form.addRow("", self.bind.construct("inactive", "boolean", label="Inactive"))
        form.addRow("&Description", self.bind.construct("descr", "multiline"))

        self.left.addLayout(form)

        # Roles Grid below the form #
        self.roles_grid = widgets.TableView()
        self.roles_grid.verticalHeader().hide()
        self.roles_grid.header().setStretchLastSection(True)
        self.roles_grid.setSortingEnabled(True)
        self.roles_gridmgr = qt.GridManager(self.roles_grid, self)
        self.left.addWidget(self.roles_grid)

        # User Addresses on the Right #
        self.address_html = QtWidgets.QTextBrowser()
        self.address_html.setStyleSheet("QTextEdit { font-size: 14px }")
        self.address_html.setOpenLinks(False)
        self.right.addWidget(self.address_html)
        self.address_html.setHtml("<p>add phone & emails here</p>")
        self.address_html.anchorClicked.connect(self.address_url_handler)

        QDB = QtWidgets.QDialogButtonBox
        buttons = QDB(QDB.Ok | QDB.Cancel, QtCore.Qt.Horizontal)
        if self.client.session.authorized("put_api_user_send_invite"):
            buttons.addButton("Reset/Invite...", QDB.ActionRole).clicked.connect(
                self.cmd_resetinvite_user
            )
        self.main.addWidget(buttons)
        buttons.accepted.connect(self.cmd_accept)
        buttons.rejected.connect(self.reject)

    def toggle_changeset_password(self, checked):
        self.bind.widgets["password"].setEnabled(checked)
        self.bind.widgets["password2"].setEnabled(checked)

    def cmd_resetinvite_user(self):
        with apputils.animator(self) as p:
            p.background(self.client.put, "api/user/{}/send-invite")

    def address_url_handler(self, url):
        if url.scheme() == "local":
            values = qt.url_params(url)

            row = None
            addrid = values.get("id", None)
            if addrid:
                matches = [r for r in self.addresses.rows if r.id == addrid]
                if matches:
                    row = matches[0]

            if url.path() == "address/new":
                self.cmd_new_address()
            elif url.path() == "address/edit":
                self.cmd_edit_address(row)
            elif url.path() == "address/delete":
                self.cmd_delete_address(row)
            else:
                qt.to_be_implemented(self, f"Url {url} is not handled.")

    def cmd_delete_address(self, row):
        if "Yes" == apputils.message(
            self.window(),
            f"Remove this address {row.address}?",
            buttons=["Yes", "No"],
        ):
            try:
                self.client.delete(
                    UserAddressDialog.SRC_INSTANCE_URL, self.userid, row.id
                )
                self.reload()
            except:
                qt.exception_message(
                    self.window(), "The user address could not be deleted."
                )

    def cmd_edit_address(self, row, new=False):
        w = UserAddressDialog(self, self.client.session)
        w.loadrec(self.editrec.id, row.id if not new else "new")
        if w.Accepted == w.exec_():
            self.reload()

    def cmd_new_address(self):
        if self.save():
            self.cmd_edit_address(None, new=True)

    def reload(self):
        self.loadrec(self.editrec.id)

    def loadrec(self, userid):
        # NOTE: self.userid may be "new"
        self.userid = userid

        with self.backgrounder.bulk(self.load_main) as bulk:
            bulk("roles_content", self.client.get, "api/roles/list")
            bulk("user_content", self.client.get, self.SRC_INSTANCE_URL, userid)

    def load_main(self, roles_content, user_content):
        self.chk_changeset_password.setChecked(False)
        self.toggle_changeset_password(False)

        self.data = user_content
        self.addresses = self.data.named_table("addresses", mixin=AddressMixin)
        self.users = self.data.main_table(mixin=EntityEditMixin)
        self.editrec = self.users.rows[0]

        self.editrec.password2 = None

        # Bind main form
        self.bind.bind(self.editrec, self.users.columns)

        # Load role grid
        self.roles = roles_content.main_table(
            mixin=EntityTaggerMixin, cls_members={"ambient_user": self.editrec}
        )

        columns = [apputils.field("role_name", "Role", check_attr="is_tagged")]

        self.roles_model = apputils.ObjectQtModel(columns)

        self.roles_grid.setModel(self.roles_model)
        self.roles_model.set_rows(self.roles.rows)

        # Load addresses
        address_chunks = "".join([a.html_view() for a in self.addresses.rows])
        html = f"""
{address_chunks}
<br />
<a href="local:address/new">New Address</a>
"""

        self.address_html.setHtml(html)

    def cmd_accept(self):
        if self.save():
            self.accept()

    def save(self):
        row = self.users.rows[0]
        excl = ["roles"]
        if self.chk_changeset_password.isChecked():
            if row.password != row.password2:
                apputils.information(
                    self, "Password and confirm password do not match."
                )
                return False
        else:
            excl.append("password")

        files = {
            "user": self.users.as_http_post_file(
                exclusions=["password2", *excl], extensions=["roles_add", "roles_del"]
            )
        }
        try:
            self.client.put(self.SRC_INSTANCE_URL, self.users.rows[0].id, files=files)
            return True
        except:
            qt.exception_message(self, "There was an error adding/updating the user.")


def edit_user_dlg(parentwin, userid):
    w = UserDialog(parentwin.window(), parentwin.client.session)
    w.loadrec(userid)
    return w.Accepted == w.exec_()

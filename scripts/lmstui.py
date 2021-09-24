import sys

from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import *
from picotui.defs import *

import client as climod
import localconfig


def server_login(appstate):
    def attempt_login(src):
        try:
            appstate.session.set_base_url(e_server.get())
            appstate.session.authenticate(e_username.get(), e_password.get())

            appstate.session.save_device_token()

        finally:
            pass

    def abort(src):
        pass

    d = Dialog(7, 6, 60, 8)

    # Can add a raw string to dialog, will be converted to WLabel
    d.add(1, 1, "Server:")
    e_server = WTextEntry(40, "")
    d.add(11, 1, e_server)

    d.add(1, 2, "Username:")
    e_username = WTextEntry(40, "")
    d.add(11, 2, e_username)

    d.add(1, 3, "Password:")
    e_password = WTextEntry(40, "")
    d.add(11, 3, e_password)

    b = WButton(9, "Login")
    d.add(20, 5, b)
    b.on("click", attempt_login)

    b = WButton(9, "Cancel")
    d.add(30, 5, b)
    b.finish_dialog = 7

    d.loop()


def contact_view(appstate):
    d = Dialog(7, 6, 73, 19)

    # Can add a raw string to dialog, will be converted to WLabel
    d.add(1, 1, "Search:")
    e_search = WTextEntry(40, "")
    e_search.on("sfasf", run_search)
    d.add(11, 1, e_search)

    b = WButton(9, "Search")
    d.add(53, 1, b)
    b.on("click", run_search)

    w_results = WListBox(40, 26, [])
    d.add(1, 3, w_results)

    d.loop()


class ParameterizedList(WListBox):
    def signal(self, sig, **kwargs):
        if sig in self.signals:
            self.signals[sig](self, **kwargs)

    def render_line(self, item):
        return item.render

    def handle_key(self, key):
        if key == KEY_ENTER:
            self.signal("activate", item=self.choice)
        return super().handle_key(key)

    def handle_mouse(self, x, y):
        if super().handle_mouse(x, y) == True:
            # (Processed) mouse click finishes selection
            return ACTION_OK


def contacts_lookup(appstate):
    def run_search(src):
        nonlocal e_search, w_results

        text = e_search.get()

        client = appstate.session.std_client()

        payload = client.get("api/personas/list", frag=text)

        table = payload.main_table()

        class RowItem:
            def __init__(self, render, obj):
                self.render = render
                self.obj = obj

        w_results.set_items([RowItem(row.entity_name, row) for row in table.rows])
        w_results.redraw()
        d.change_focus(w_results)

    d = Dialog(5, 5, 75, 20)

    # Can add a raw string to dialog, will be converted to WLabel
    d.add(1, 1, "Search:")
    e_search = WTextEntry(40, "")
    e_search.on("sfasf", run_search)
    d.add(11, 1, e_search)

    b = WButton(9, "Search")
    d.add(53, 1, b)
    b.on("click", run_search)

    def prompt_lookup(src, item):
        nonlocal w_results, appstate

        contact_view(appstate, item.object.id)

    w_results = ParameterizedList(40, 26, [])
    d.add(1, 3, w_results)
    w_results.on("activate", prompt_lookup)

    d.loop()


def transaction_lookup(appstate):
    def run_search(src):
        nonlocal e_search, w_results

        text = e_search.get()

        client = appstate.session.std_client()

        payload = client.get("api/transactions/list", fragment=text)

        table = payload.main_table()

        class RowItem:
            def __init__(self, obj):
                self.obj = obj

            @property
            def render(self):
                return f"{self.obj.payee} -- {self.obj.memo}"

        w_results.set_items([RowItem(row) for row in table.rows])
        w_results.redraw()
        d.change_focus(w_results)

    d = Dialog(5, 5, 75, 20)

    # Can add a raw string to dialog, will be converted to WLabel
    d.add(1, 1, "Search:")
    e_search = WTextEntry(40, "")
    e_search.on("sfasf", run_search)
    d.add(11, 1, e_search)

    b = WButton(9, "Search")
    d.add(53, 1, b)
    b.on("click", run_search)

    def prompt_lookup(src, item):
        nonlocal w_results, appstate

        transaction_view(appstate, item.object.id)

    w_results = ParameterizedList(40, 26, [])
    d.add(1, 3, w_results)
    w_results.on("activate", prompt_lookup)

    d.loop()


if __name__ == "__main__":
    view = sys.argv[1] if len(sys.argv) >= 2 else None
    if view is None:
        view = "contacts"

    with Context():

        Screen.attr_color(C_WHITE, C_BLUE)
        Screen.cls()
        Screen.attr_reset()

        localconfig.set_identity()

        class AppState:
            pass

        appstate = AppState()
        appstate.session = climod.auto_session()

        if not appstate.session.access_token:
            server_login(appstate)

        if not appstate.session.access_token:
            sys.exit()

        if view == "contacts":
            contacts_lookup(appstate)
        elif view == "trans":
            transaction_lookup(appstate)

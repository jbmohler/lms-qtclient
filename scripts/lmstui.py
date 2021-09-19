from picotui.context import Context
from picotui.screen import Screen
from picotui.widgets import *
from picotui.defs import *

import client as climod
import localconfig

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
    b.on("select", prompt_lookup)

    d.loop()


if __name__ == "__main__":
    with Context():

        Screen.attr_color(C_WHITE, C_BLUE)
        Screen.cls()
        Screen.attr_reset()

        localconfig.set_identity()

        class AppState:
            pass

        appstate = AppState()
        appstate.session = climod.auto_session()

        contacts_lookup(appstate)

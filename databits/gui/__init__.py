from . import search


class DataBitExtensions:
    def show_link_parented(self, state, parent, url):
        if url.scheme() != "lmsdatabits":
            return False

        if url.path() == "databits/list":
            if parent.foreground_tab("databit_search"):
                return True
            view = search.list_widget(parent, state.session)
            parent.adopt_tab(view, "databit_search", "Data Bits")
        return True

    def get_menus(self):
        contact_menu_schematic = [
            (
                "ClientURLMenuItem",
                (
                    "DataBit &List",
                    "lmsdatabits:databits/list",
                    "get_api_databits_bits_list",
                ),
            )
        ]
        yield ("&DataBits", contact_menu_schematic)

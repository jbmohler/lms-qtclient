from . import search


class ContactExtensions:
    def show_link_parented(self, state, parent, url):
        if url.scheme() != "lmscontacts":
            return False

        if url.path() == "contacts/list":
            if parent.foreground_tab("contact_search"):
                return True
            view = search.ContactsList(parent, state)
            parent.adopt_tab(view, "contact_search", "Contacts")
        elif url.path() == "contact/edit":
            dlg = search.EditPersona(parent)

            dlg.session = state.session
            dlg.client = dlg.session.std_client()

            class X:
                pass

            x = X()
            x.id = url.parameters()["key"]
            dlg.load(dlg.client, x)
            dlg.exec_()
        return True

    def get_menus(self):
        contact_menu_schematic = [
            (
                "ClientURLMenuItem",
                (
                    "Contact &List",
                    "lmscontacts:contacts/list",
                    "get_api_personas_list",
                    "Ctrl+J",
                ),
            )
        ]
        yield ("&Contacts", contact_menu_schematic)

    def load_sidebar(self, state, name):
        if name == "persona_general":
            return search.ContactView(None, state)


class WidgetsPlugin:
    def polish(self, attr, type_, meta):
        if type_ == "lms_personas_persona.name":
            meta[
                "url_factory"
            ] = lambda *args: f"lmscontacts:contact/edit?key={args[1]}"
        if type_ == "lms_personas_persona.surrogate":
            meta[
                "url_factory"
            ] = lambda *args: f"lmscontacts:contact/edit?key={args[0]}"

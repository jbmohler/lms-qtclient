from . import search

class ContactExtensions:
    def show_link_parented(self, state, parent, url):
        if url.scheme() != 'lmscontacts':
            return False

        if url.path() == 'contacts/list':
            if parent.foreground_tab('contact_search'):
                return True
            view = search.list_widget(parent, state.session)
            parent.adopt_tab(view, 'contact_search', 'Contacts')
        return True

    def get_menus(self):
        contact_menu_schematic = [
                ('ClientURLMenuItem', ('Contact &List', 'lmscontacts:contacts/list', 'get_api_personas_list'))]
        yield ('&Contacts', contact_menu_schematic)

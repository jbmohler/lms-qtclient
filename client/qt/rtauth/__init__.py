from . import useradmin
from . import useradmin_setactivities as activities

class RtAuthPlugs:
    def show_link_parented(self, state, parent, url):
        if url.scheme() not in ('yenot', 'rtauth'):
            return False

        if url.path() in useradmin.SIMPLE_LIST_MAP:
            widclass = useradmin.SIMPLE_LIST_MAP[url.path()]
            parent.create_or_adopt_tab(widclass)
        elif url.path() == 'endpoints/list-surrounding-error':
            list_surrounding(state, parent, url.parameters()['event_id'])
        elif url.path() == 'activities/register':
            w = activities.ManageActivities(state.session, state.exports_dir, parent=parent, unregistered=True)
            w.show()
        else:
            return False
        return True

    def get_menus(self):
        admin_schematic = [
                ('ClientURLMenuItem', ('Active &Sessions', 'rtauth:administrative/sessions', 'get_api_sessions_active')),
                ('ClientURLMenuItem', ('&Role List', 'rtauth:administrative/roles', 'get_api_roles_list')),
                ('ClientURLMenuItem', ('&Activities', 'rtauth:administrative/activities', 'get_api_activities_list')),
                ('ClientURLMenuItem', ('&User List', 'rtauth:administrative/users', 'get_api_users_list')),
                ('SeparatorMenuItem', ()),
                ('ClientURLMenuItem', ('&Database Connections', 'rtauth:administrative/dbconnections', 'api_database_connections')),
                ('ClientURLMenuItem', ('Active Database &Locks', 'rtauth:administrative/dblocks', 'api_database_locks'))]
        yield ('&Administrative', admin_schematic)

    def load_sidebar(self, state, name):
        if name == 'get_api_users_list':
            return useradmin.UserListSidebar(None, state)

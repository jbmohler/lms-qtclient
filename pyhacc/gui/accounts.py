import client.qt as qt
from . import widgets

URL_BASE = 'api/account/{}'

def edit_account(session, acntid='new'):
    dlg = qt.FormEntryDialog('PyHacc Account')

    dlg.add_form_row('acc_name', 'Account', 'basic')
    dlg.add_form_row('type_id', 'Type', 'pyhacc_accounttype.id')
    dlg.add_form_row('journal_id', 'Journal', 'pyhacc_journal.id')
    dlg.add_form_row('description', 'Description', 'multiline')

    client = session.std_client()

    payload = client.get(URL_BASE, acntid)
    table = payload.main_table()

    def apply(bound):
        nonlocal client, table
        client.put(URL_BASE, bound.id, files={'account':
            table.as_http_post_file(exclusions=['atype_name', 'jrn_name'])})
        return True

    widgets.verify_settings_load(dlg, client, dlg.binder)

    dlg.bind(table.rows[0])
    dlg.applychanges = apply
    dlg.exec_()

__all__ = ['edit_account']

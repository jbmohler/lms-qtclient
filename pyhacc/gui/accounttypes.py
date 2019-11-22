import client.qt as qt
from . import widgets

URL_BASE = 'api/accounttype/{}'

def edit_account_type(session, acnttypeid='new'):
    dlg = qt.FormEntryDialog('PyHacc Account Type')

    dlg.add_form_row('atype_name', 'Type', 'basic')
    dlg.add_form_row('description', 'Description', 'basic')
    dlg.add_form_row('balance_sheet', 'Balance Sheet', 'boolean')
    dlg.add_form_row('debit', 'Debit', 'boolean')
    dlg.add_form_row('retained_earnings', 'Retained Earnings', 'boolean')

    client = session.std_client()

    payload = client.get(URL_BASE, acnttypeid)
    table = payload.main_table()

    def apply(bound):
        nonlocal client, table
        client.put(URL_BASE, bound.id, files={'accounttype': table.as_http_post_file()})
        return True

    widgets.verify_settings_load(dlg, client, dlg.binder)

    dlg.bind(table.rows[0])
    dlg.applychanges = apply
    dlg.exec_()

__all__ = ['edit_account_type']

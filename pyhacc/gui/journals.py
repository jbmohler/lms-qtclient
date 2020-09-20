import client.qt as qt

URL_BASE = "api/journal/{}"


def edit_journal(session, jrnid="new"):
    dlg = qt.FormEntryDialog("PyHacc Journal")

    dlg.add_form_row("jrn_name", "Journal", "basic")
    dlg.add_form_row("description", "Description", "multiline")

    client = session.std_client()

    payload = client.get(URL_BASE, jrnid)
    table = payload.main_table()

    def apply(bound):
        nonlocal client, table
        client.put(URL_BASE, bound.id, files={"journal": table.as_http_post_file()})
        return True

    dlg.bind(table.rows[0])
    dlg.applychanges = apply
    dlg.exec_()


__all__ = ["edit_journal"]

import os
import datetime
import rtlib
import replicate as api

cli = api.get_global_router()

@cli.command
def roscoe(cmd, args):
    client = cli.session.std_client()

    content = client.get('api/roscoe/unprocessed')
    table = content.main_table()
    api.show_table(table)

@cli.command
def roscoe_mark(cmd, args):
    client = cli.session.std_client()

    client.put('api/roscoe/mark-processed')


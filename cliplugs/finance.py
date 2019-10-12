import os
import datetime
import rtlib
import replicate as api

cli = api.get_global_router()

def get_field(label, default, type_='basic'):
    prompt = '{} [{}]:  '.format(label, default)
    value = input(prompt)
    if value == '':
        value = default
    col = rtlib.field('xx', label, type_=type_)
    value = col.coerce_edit(value)
    return value

class TranController:
    def __init__(self, template):
        self.trans = template.named_table('trans')
        self.splits = template.named_table('splits')

        self.tranrow = self.trans.rows[0]

    def text_repr(self):
        lines = []
        if self.tranrow.trandate != None:
            lines.append("Date:  {0}".format(self.tranrow.trandate))
        if self.tranrow.tranref not in [None, ""]:
            lines.append("Reference:  {0}".format(self.tranrow.tranref))
        if self.tranrow.payee not in [None, ""]:
            lines.append("Payee:  {0}".format(self.tranrow.payee))
        if self.tranrow.memo not in [None, ""]:
            lines.append("Memo:  {0}".format(self.tranrow.memo))
        lines.append("-"*(20+1+12+1+12))
        #for x in self.splits.rows:
        #    lines.append("{0.account:<20} {0.debit:12.2f} {0.credit:12.2f}".format(x))
        lines.append("-"*(20+1+12+1+12))

        return '\n'.join(lines)

@cli.command
def tran_new(cmd, args):
    date = get_field('transaction date', 'today', type_='date')
    payee = get_field('payee', '')
    memo = get_field('memo', '')
    dracc = get_field('debit account', '', type_='pyhacc_account')
    dramt = get_field('debit amount', '', type_='currency_usd')
    cracc = get_field('credit account', '', type_='pyhacc_account')
    cramt = get_field('credit amount', dramt, type_='currency_usd')

    client = cli.session.std_client()

    template = client.get('api/transaction/new')
    ctlr = TranController(template)

    ctlr.tranrow.trandate = date
    ctlr.tranrow.payee = payee
    ctlr.tranrow.memo = memo
    with ctlr.splits.adding_row() as r2:
        r2.account_id = dracc
        r2.sum = dramt
    with ctlr.splits.adding_row() as r2:
        r2.account_id = cracc
        r2.sum = -cramt

    print(ctlr.text_repr())

    confirm = get_field('commit transaction', 'yes', type_='boolean')

    if confirm:
        client.put('api/transaction/{}/document', ctlr.tranrow.id,
                files=ctlr.tran_files())

@cli.command
def month(cmd, args):
    if len(args) == 0:
        raise api.UserError('specify an output directory for the month files')
    dump_prior_month(cli.session, args[0])

@cli.command
def dumpyears(cmd, args):
    if len(args) == 0:
        raise api.UserError('specify an output directory for the month files')
    dump_data(cli.session, args[0])

html_template = """\
<html>
 <head>
  <title>{title}</title>
  <meta name="GENERATOR" content="Yenot {version}" />
  <meta name="DESCRIPTION" content="{rptclass}" />
 </head>
 <body>
  <h1>{title}</h1>
  {table}
 </body>
</html>
"""

def content_write_html(content, outfile, rptclass):
    table = content.main_table()
    lines = table.rows
    cols = [c for c in table.columns if not c.hidden]

    def bracket_list(l, td, join=''):
        return join.join(["<{0}>{1}</{0}>".format(td, i) for i in l])

    def format(p, c):
        v = getattr(p, c.attr)
        if c.type_ == 'currency_usd':
            if v == None:
                v = '--'
            else:
                v = '{:.2f}'.format(v)
        else:
            if v == None:
                v = ''
        return v

    header = [bracket_list([c.label.replace('\n', '<br />') for c in cols], "th")]
    header += [bracket_list([format(p, c) for c in cols], "td") for p in lines]
    table = bracket_list(header, "tr", join='\n')

    with open(outfile, 'w') as outf:
        outf.write(html_template.format(
            title=content.keys['headers'][0],
            version='0.0.1', 
            rptclass=rptclass,
            table="<table>" + table + "</table>"))

def dump_data(session, outdir):
    client = session.std_client()

    ycontent = client.get('api/transactions/years')
    years = ycontent.main_table()

    small_year, big_year = years.rows[0].year, years.rows[-1].year

    datadir = outdir

    for year in range(small_year, big_year+1):
        dest = os.path.join(datadir, str(year))
        if not os.path.exists(dest):
            os.makedirs(dest)

        bscontent = client.get('api/gledger/balance-sheet',
                date=datetime.date(year, 12, 31))
        bsfile = os.path.join(datadir, str(year),
                'bal_sheet_{}.html'.format(year))
        content_write_html(bscontent, bsfile, 'BalanceSheet')

        trancontent = client.get('api/transactions/list',
                date1=datetime.date(year, 1, 1),
                date2=datetime.date(year, 12, 31))
        tranfile = os.path.join(datadir, str(year),
                'transactions_{}.html'.format(year))
        content_write_html(trancontent, tranfile, 'TransactionList')

        plcontent = client.get('api/gledger/detailed-pl',
                date1=datetime.date(year, 1, 1),
                date2=datetime.date(year, 12, 31))
        plfile = os.path.join(datadir, str(year),
                'detail_pl_{}.html'.format(year))
        content_write_html(plcontent, plfile, 'DetailedProfitAndLoss')


def dump_prior_month(session, outdir):
    client = session.std_client()

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    td = datetime.date.today()
    year, month = td.year, td.month
    if month == 1:
        year, month = year-1, 12
    else:
        year, month = year, month-1
    month_begin = datetime.date(year, month, 1)
    month_end = td - datetime.timedelta(days=td.day)

    print('Dumping history {} to {}'.format(month_begin, month_end))

    bscontent = client.get('api/gledger/balance-sheet',
            date=month_end)
    bsfile = os.path.join(outdir, 'BalanceSheet.html')
    content_write_html(bscontent, bsfile, 'BalanceSheet')

    plcontent = client.get('api/gledger/detailed-pl',
            date1=month_begin, date2=month_end)
    plfile = os.path.join(outdir, 'DetailedProfitLoss.html')
    content_write_html(plcontent, plfile, 'DetailPL')

    plcontent = client.get('api/gledger/interval-p-and-l',
            ending_date=month_end, intervals=3, length=6)
    plfile = os.path.join(outdir, 'IntervalPL.html')
    content_write_html(plcontent, plfile, 'IntervalPL')

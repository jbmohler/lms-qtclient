
def show_table(table, max_rows=25, max_columns=14, max_colwidth=20):
    columns = []
    for c in table.columns:
        if c.hidden:
            continue
        if c.attr in table.DataRow.model_columns:
            columns.append(c)
        if len(columns) >= max_columns:
            break

    def full_format(row, c):
        v = getattr(row, c.attr)
        return c.formatter(v)

    for index, row in enumerate(table.rows[:max_rows]):
        values = [full_format(row, c) for c in columns]
        for cin, c in enumerate(columns):
            this = min(len(values[cin]), max_colwidth)
            prior = getattr(c, 'cli_width', 1)
            c.cli_width = max(this, prior)
    for cin, c in enumerate(columns):
        this = min(max(6, len(c.label)), max_colwidth)
        prior = getattr(c, 'cli_width', 1)
        c.cli_width = max(this, prior)

    def head_formatter(c):
        s = c.label.replace('\n', '')
        # last minute sanitize
        s = s.encode('cp437', 'replace').decode('cp437')
        if c.alignment == 'right':
            return s.rjust(c.cli_width)
        else:
            return s.ljust(c.cli_width)

    def formatter(row, c):
        v = getattr(row, c.attr)
        if c.type_ == 'boolean':
            # customize
            s = {True: 'x', False: ''}[v]
        else:
            s = c.formatter(v)
        if len(s) > c.cli_width:
            s = s[:c.cli_width-3]+'...'
        # last minute sanitize
        s = s.encode('cp437', 'replace').decode('cp437')
        if c.alignment == 'right':
            return s.rjust(c.cli_width)
        else:
            return s.ljust(c.cli_width)

    x = ['    ']+['{:s}']*len(columns)+['']
    args = [head_formatter(c) for c in columns]
    print('|'.join(x).format(*args))

    for index, row in enumerate(table.rows[:max_rows]):
        x = ['.{:>3n}']+['{:s}']*len(columns)+['']
        args = [index+1]
        args += [formatter(row, c) for c in columns]
        print('|'.join(x).format(*args))
    if len(table.rows) > max_rows:
        print('{} rows; first {}'.format(len(table.rows), max_rows))

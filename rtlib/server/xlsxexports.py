"""
This module has tools to export a QAbstractItemView linked to an
apputils.ObjectQtModel to an xslx MS Excel file.  It matches column widths on
screen with (possibly relative) column widths in the Excel document.

Some options include:

    - header data put at the top of the page or document
    - "group by" which inserts page breaks when the key changes
    - column exclusions & order according to the view

In the future this aims to support more options:

    - set landscape/portrait
    - fit page option when sizing columns
    - row exclusions
"""
import xlsxwriter
import xlsxwriter.utility as xlutil
import rtlib
from . import evaluator

# NOTE:  Excel caps number of URLs at about 65,000, but in practice it becomes
# slow well before that.  I chose a much higher limit here to probe the 65,000.
EXCEL_MAX_URLS = 1e8
EXCEL_HARD_MAX = 65530

class WorkbookHelpers:
    """
    This class is set of callback helpers for rtlib family grouped reports.
    """
    def __init__(self, workbook):
        self.bold_format = workbook.add_format({\
                        'bold': True})
        self.wrapped_format = workbook.add_format({\
                        'text_wrap': True})
        self.boldwrap_format = workbook.add_format({\
                        'bold': True,
                        'text_wrap': True})
        self.group_header = workbook.add_format({\
                        'align': 'center',
                        'bold': True,
                        'font_size': 14,
                        'bottom': 2})
        self.url_format = workbook.add_format({\
                        'font_color': 'blue',
                        'underline': 1})
        self.url_right_format = workbook.add_format({\
                        'font_color': 'blue',
                        'underline': 1, 
                        'align': 'right'})
        self.right_format = workbook.add_format({\
                        'align': 'right'})
        self.date_format = workbook.add_format({\
                        'num_format': 'mm/dd/yyyy',
                        'align': 'left'})
        self.datetime_format = workbook.add_format({\
                        'num_format': 'mm/dd/yyyy hh:mm:ss', 
                        'align': 'left'})
        self.percent_format = workbook.add_format({\
                        'num_format': '0%'})
        self.bold_currency_format = workbook.add_format({\
                        'bold': True,
                        'num_format': '#,##0.00'})
        self.currency_accounting_truncated_format = workbook.add_format({\
                        'num_format': '#,##0_);(#,##0)'})
        self.currency_format = workbook.add_format({\
                        'num_format': '#,##0.00'})

class BBColumn:
    def __init__(self, index, letter, attr):
        self.index = index
        self.letter = letter
        self.attr = attr

    def cell(self, index):
        return f'{self.letter}{index + 1}'

class BBRow:
    def __init__(self, index, row):
        self.index = index
        self.row = row

class TableBoundingBox:
    def __init__(self):
        self.columns = []
        self.bound_rows = []

    @property
    def row_index_start(self):
        return self.bound_rows[0].index

    @property
    def row_index_end(self):
        return self.bound_rows[-1].index

    @property
    def rows(self):
        return [b.row for b in self.bound_rows]

def export_view(fname, view, headers=None, options=None, sort_key=None,
        max_url=EXCEL_MAX_URLS, suppress_grouped_column=False, group_start_callback=None, group_end_callback=None, hyperlinks=True):
    """
    Export a grid to an excel xlsx file with column order and widths matching
    the passed view.

    Optional filters & controls are included in the options dictionary:

    - row_filter:  only include a row if this filter expression returns true on
      the row
    - row_group:  insert a group every time the value of this expression on the
      row changes
    - hpagebreak:  insert a page break every time the value of this expression
      on the row changes.

    NOTE:  The options hpagebreak & row_group are both grouping tools.   They
    are mutually exclusive.  The only difference is that hpagebreak inserts a
    horizontal page break after every group.
    """
    workbook = xlsxwriter.Workbook(fname)
    wbhelper = WorkbookHelpers(workbook)

    worksheet = workbook.add_worksheet()

    if headers == None:
        headers = []
    if options == None:
        options = {}

    model = view.model()
    if hasattr(view, 'header'):
        header = view.header()
        columns_visible = [(c, index) for index, c in enumerate(model.columns) if not header.isSectionHidden(index)]
        columns_visible.sort(key=lambda x: header.visualIndex(x[1]))
        columns = [c for c, _ in columns_visible]
    else:
        columns_visible = [(c, index) for index, c in enumerate(model.columns)]
        columns = [c for c in model.columns]
    if hasattr(model, 'exportcolumns'):
        columns = [c for c in columns if c.attr in model.exportcolumns]
    if suppress_grouped_column and 'row_group' in options:
        columns = [c for c in columns if c.attr != options['row_group']]

    def print_headers(row):
        for index, head in enumerate(headers):
            worksheet.write(row+index, 0, head)

    print_headers(0)

    grid_left = 0
    grid_top = (len(headers) + 1) if len(headers) > 0 else 0

    for index, __c_index in enumerate(columns_visible):
        _, c_index = __c_index
        worksheet.set_column(index, index, view.columnWidth(c_index)/view.logicalDpiX()*12)

    def print_column_headers(row):
        for index, header in enumerate(columns):
            worksheet.write(row, grid_left+index, header.label, wbhelper.boldwrap_format)

    pagebreaks = []
    group_expr = None
    page_break_groups = False
    row_filter_expr = None
    if 'hpagebreak' in options:
        group_expr = evaluator.PreparedEvaluator(options['hpagebreak'])
        page_break_groups = True
    if 'row_group' in options:
        group_expr = evaluator.PreparedEvaluator(options['row_group'])
    if 'row_filter' in options:
        row_filter_expr = evaluator.PreparedEvaluator(options['row_filter'])

    if row_filter_expr != None:
        row_predicate = row_filter_expr.evaluate
        filtered_rows = [r for r in model.rows if row_predicate(r)]
    else:
        filtered_rows = list(model.rows)

    if sort_key != None:
        expr = evaluator.PreparedEvaluator(sort_key)
        filtered_rows.sort(key=expr.evaluate)

    filtered = len(filtered_rows)
    if filtered == 0:
        filtered = 1
    allowed_columns = max_url // filtered
    columns_to_link = []
    # cleverly choose columns to show links for
    if hyperlinks:
        for col in columns:
            if col.represents and col.url_factory != None and len(columns_to_link) < allowed_columns:
                columns_to_link.append(col.attr)
        for col in columns:
            if not col.represents and col.url_factory != None and len(columns_to_link) < allowed_columns:
                columns_to_link.append(col.attr)

    box = TableBoundingBox()
    for index, col in enumerate(columns):
        gridindex = grid_left+index
        box.columns.append(BBColumn(gridindex, xlutil.xl_col_to_name(gridindex), col.attr))

    link_count = 0
    offset = 0
    prior = None
    row_group = []
    for index2, row_in in enumerate(filtered_rows):
        if group_expr != None:
            thisrow = group_expr.evaluate(row_in)
            if prior == None:
                prior = thisrow

                if group_start_callback != None:
                    rows_used = group_start_callback(wbhelper, worksheet, box, row_in, grid_top+index2+offset)
                    offset += rows_used
                print_column_headers(grid_top+index2+offset)
                offset += 1

                row_group = [BBRow(grid_top+index2+offset, row_in)]
            elif thisrow != prior:
                if group_end_callback != None:
                    box.bound_rows = row_group
                    rows_used = group_end_callback(wbhelper, worksheet, box, grid_top+index2+offset)
                    offset += rows_used

                pagebreaks.append(grid_top+index2+offset)
                prior = thisrow

                # repeat header
                if page_break_groups:
                    print_headers(grid_top+index2+offset)
                    offset += len(headers) + 1

                if group_start_callback != None:
                    rows_used = group_start_callback(wbhelper, worksheet, box, row_in, grid_top+index2+offset)
                    offset += rows_used
                print_column_headers(grid_top+index2+offset)
                offset += 1

                row_group = [BBRow(grid_top+index2+offset, row_in)]
            else:
                row_group.append(BBRow(grid_top+index2+offset, row_in))
        elif index2 == 0:
            # only print this the first time around
            print_column_headers(grid_top+index2+offset)
            offset += 1

        for index, col in enumerate(columns):
            v = getattr(row_in, col.attr)
            if isinstance(v, tuple):
                if v[0] == v[1]:
                    v = v[0]
                else:
                    v = str(v)
            if isinstance(v, str) and col.alignment == 'right':
                v = v.lstrip()
            if col.formatter != None and hasattr(col.formatter, 'as_xlsx'):
                fmtfunc = col.formatter.as_xlsx
                v = fmtfunc(v)
            link = None
            if hyperlinks:
                if col.attr in columns_to_link:# and link_count < EXCEL_HARD_MAX:
                    link = rtlib.column_url(col, row_in)
            if col.checkbox:
                worksheet.write_boolean(grid_top+index2+offset, grid_left+index, v)
            elif link != None:
                link_count += 1
                v2 = '=hyperlink("{}", "{}")'.format(link, v.replace('"', '""'))
                worksheet.write_formula(grid_top+index2+offset, grid_left+index, v2, wbhelper.url_right_format if col.alignment == 'right' else wbhelper.url_format)
                #worksheet.write_url(grid_top+index2+offset, grid_left+index, link, wbhelper.url_right_format if col.alignment == 'right' else wbhelper.url_format, v)
            elif col.type_ == 'currency_usd' and v != None:
                worksheet.write(grid_top+index2+offset, grid_left+index, v, wbhelper.currency_format)
            elif col.type_ == 'percent' and v != None:
                worksheet.write(grid_top+index2+offset, grid_left+index, v, wbhelper.percent_format)
            elif col.type_ == 'date' and v != None:
                worksheet.write_datetime(grid_top+index2+offset, grid_left+index, v, wbhelper.date_format)
            elif col.type_ == 'datetime' and v != None:
                worksheet.write_datetime(grid_top+index2+offset, grid_left+index, v, wbhelper.datetime_format)
            else:
                worksheet.write(grid_top+index2+offset, grid_left+index, v, wbhelper.right_format if col.alignment == 'right' else None)

    if group_end_callback != None:
        box.bound_rows = row_group
        rows_used = group_end_callback(wbhelper, worksheet, box, grid_top+index2+offset+1)

    if page_break_groups:
        worksheet.set_h_pagebreaks(pagebreaks)

    workbook.close()

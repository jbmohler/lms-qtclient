import io
import rtlib
from . import xlsxexports


class UnifiedViewModel(rtlib.ModelMixin):
    CHAR_PIXELS = 10

    def model(self):
        # This is the point, they are unified!
        return self

    def columnWidth(self, i):
        col = self.columns[i]
        cw = col.char_width if col.char_width else 30
        if col.max_length and col.max_length < cw:
            cw = col.max_length
        return cw * self.CHAR_PIXELS

    def logicalDpiX(self):
        return self.CHAR_PIXELS * 8


def uview_from_client_table(table):
    uview = UnifiedViewModel([col for col in table.columns if not col.hidden])
    uview.set_rows(table.rows)
    return uview


def stdresponse_to_xlsx(sresponse, filename=None, preparsed=False):
    """
    This function sets up whatever it takes to make xlsxexport.export_view
    function.
    """
    if filename == None:
        output = io.BytesIO()
    else:
        output = filename

    keys, columns, rows = sresponse
    headers = keys["headers"]
    if preparsed:
        table = rtlib.UnparsingClientTable(columns, rows)
    else:
        table = rtlib.ClientTable(columns, rows)
    view = UnifiedViewModel(table.columns)
    view.set_rows(table.rows)

    xlsxexports.export_view(output, view, headers=headers, max_url=20000)

    if filename == None:
        output.seek(0)
        return output.read()

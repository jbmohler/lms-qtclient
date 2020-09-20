import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
from . import reportcore

def tabulate(headers, rows, tid=None, tclass=None):
    kwargs = {}
    if tid != None:
        kwargs['id'] = tid
    if tclass != None:
        kwargs['class'] = tclass
    table = ET.Element('table', **kwargs)

    head = ET.SubElement(table, 'thead')
    headtr = ET.SubElement(head, 'tr')
    for h in headers:
        ET.SubElement(headtr, 'th').text = h

    body = ET.SubElement(table, 'tbody')
    for row in rows:
        rowtr = ET.SubElement(body, 'tr')
        for item in row:
            if isinstance(item, ET.Element):
                ET.SubElement(rowtr, 'td').append(item)
            else:
                ET.SubElement(rowtr, 'td').text = str(item)
    return ET.tostring(table, method='html')

def _cell_internal(column, row):
    try:
        v = getattr(row, column.attr)
    except AttributeError:
        v = None
    if v == None:
        return None, None
    link = reportcore.column_url(column, row)
    if column.formatter != None:
        v = column.formatter(v)
    return v, link

def rc_value(column, row):
    v, link = _cell_internal(column, row)
    if v == None:
        return ''
    elif link == None:
        return v
    else:
        elt = ET.Element('a', attrib={'href': link})
        elt.text = v.strip()
        return ET.tostring(elt, method='html').decode('utf8')

def cell(column, row):
    """
    This function applies the logic of a reportcore.Column to constructing a td
    element for an html table.

    Return a TD element formatting the value in row corresponding to column
    according to the rules of column.
    """
    tdkwargs = {}
    if column.alignment == 'right':
        tdkwargs['align'] = 'right'
    td = ET.Element('td', **tdkwargs)
    v, link = _cell_internal(column, row)
    if v == None:
        pass
    elif column.type_ == 'html':
        td.append(ET.fromstring(f'<p>{v}</p>'))
    elif column.type_ == 'multiline':
        v = saxutils.escape(v).replace('\n', '<br />')
        td.append(ET.fromstring(f'<p>{v}</p>'))
    elif column.type_ == 'boolean':
        td.attrib['align'] = 'center'
        td.append(ET.fromstring(f'<p>{v}</p>'))
    elif link == None:
        td.text = str(v) if str(v) != '' else '\u00a0'
    else:
        attrs = {'href': link}
        if column.url_new_window:
            attrs['target'] = '_blank'
        elt = ET.SubElement(td, 'a', attrib=attrs)
        elt.text = v.strip()
    return td

def html_cell(column, row):
    td = cell(column, row)
    return ET.tostring(td, method='html').decode('utf8')

def html_table(columns, rows, **kwargs):
    table = ET.Element('table', **kwargs)

    head = ET.SubElement(table, 'thead')
    headtr = ET.SubElement(head, 'tr')
    for h in columns:
        ET.SubElement(headtr, 'th').text = h.label

    # construct td elements
    rows2 = []
    for row in rows:
        r = [cell(h, row) for h in columns]
        rows2.append(r)

    body = ET.SubElement(table, 'tbody')
    for row in rows2:
        rowtr = ET.SubElement(body, 'tr')
        rowtr.extend(row)
    return table

def styled_html_table(columns, rows, tid=None, tclass=None, **kwargs):
    """
    Generate an HTML table based on reportcore columns.
    """
    attrkwargs = {}
    if tid != None:
        attrkwargs['id'] = tid
    if tclass != None:
        attrkwargs['class'] = tclass
    for k, v in kwargs.items():
        attrkwargs[k] = str(v)
    table = html_table(columns, rows, **attrkwargs)
    return ET.tostring(table, method='html')

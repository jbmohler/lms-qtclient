html_template = """\
<html>
 <head>
  <title>{title}</title>
  <meta name="GENERATOR" content="Yenot {version}" />
  <meta name="DESCRIPTION" content="{rptclass}" />
 </head>
 <body>
  <h1>{title}</h1>
{heads}
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
        if c.formatter != None:
            v = c.formatter(v)
        return v

    header = [bracket_list([c.label.replace('\n', '<br />') for c in cols], "th")]
    header += [bracket_list([format(p, c) for c in cols], "td") for p in lines]
    table = bracket_list(header, "tr", join='\n')

    heads = ["  <p>{}</p>".format(x) for x in content.keys['headers'][1:]]
    heads = "\n".join(heads)

    with open(outfile, 'w') as outf:
        outf.write(html_template.format(
            title=content.keys['headers'][0],
            version='0.0.1', 
            rptclass=rptclass,
            heads=heads,
            table="<table>\n" + table + "\n</table>"))

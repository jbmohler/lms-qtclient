import contextlib
import collections
from . import reportcore
from . import html
from . import server


def augment_table(table, insert_columns, xform):
    columns = table.DataRow.__slots__
    for instuple in insert_columns:
        if instuple[0] == 0:
            columns = list(instuple)[1:] + columns
        else:
            index = columns.find(instuple[0])
            columns = columns[:index] + list(instuple)[1:] + columns[index:]
    tx = simple_table(columns)
    rlist = []
    for oldrow in table.rows:
        row = tx.DataRow(**oldrow._as_dict())
        xform(oldrow, row)
        rlist.append(row)
    tx.rows = rlist
    return tx


def simple_table(columns, column_map=None):
    if column_map == None:
        column_map = {}
    return ClientTable([(c, column_map.get(c, None)) for c in columns], [])


class TypedTable:
    """
    This class and ClientTable present the same html generating API.
    """

    def __init__(self, columns, rows):
        self.rows = rows[:]
        self.columns = columns

    def as_html(self, **kwargs):
        return html.styled_html_table(self.columns, self.rows, **kwargs).decode("utf8")

    def as_html_xml(self, **kwargs):
        return html.html_table(self.columns, self.rows, **kwargs)

    def as_form_html(self, row=None, exclude=None, include=None, labels=True):
        if exclude != None and include != None:
            raise RuntimeError("unclear meaning")

        if exclude != None:
            c2 = [c for c in self.columns if c.attr not in exclude]
        elif include != None:
            c2 = [c for c in self.columns if c.attr in include]
        else:
            c2 = self.columns[:]

        lines = []
        if row == None:
            row = self.rows[0]
        for c in c2:
            if labels:
                lines.append(f"<b>{c.label}</b>:  {html.rc_value(c, row)}")
            else:
                lines.append(html.rc_value(c, row))
        return "<br />".join(lines)


class ExpansionAlignment:
    def __init__(self, *args):
        self.fillouts = [None] * len(args)
        agg_col = collections.OrderedDict()
        for index, colset in enumerate(args):
            prior_to_this_level = set(agg_col.keys())
            this_level = set()
            for attr, meta in colset:
                this_level.add(attr)
                agg_col[attr] = meta
            after_this_level = set(agg_col.keys())

            for prior in range(index):
                self.fillouts[prior] += list(after_this_level - prior_to_this_level)
            self.fillouts[index] = list(prior_to_this_level - this_level)

        self.aggregate = list(agg_col.items())


class ClientTable:
    """
    This class and TypedTable present the same html generating API.   This
    class could be considered derived from TypedTable, but I'm uncomfortable
    with directly implementing it in that way.
    """

    def __init__(self, columns, rows, mixin=None, cls_members=None, to_localtime=True):
        self.to_localtime = to_localtime
        f = self.row_factory(columns, mixin=mixin, cls_members=cls_members)
        self.rows = [f(x) for x in rows]

        # initialize pkey for deletion
        pkey = [
            col[0]
            for col in columns
            if col[1] != None and col[1].get("primary_key", False)
        ]
        self.pkey = pkey

        self.columns = reportcore.parse_columns(columns)
        self.columns_full = reportcore.parse_columns_full(columns)
        self.DataRow.model_columns = {c.attr: c for c in self.columns}

        self.deleted_rows = []

    def duplicate(self, rows, deleted="duplicate"):
        # TODO:  make sure that deleted rows don't show up here as rows to save
        x = self.__class__.__new__(self.__class__)
        x.DataRow = self.DataRow
        x.rows = rows[:]
        x.columns = self.columns
        x.columns_full = self.columns_full
        x.pkey = self.pkey
        if deleted == "duplicate":
            x.deleted_rows = list(self.deleted_rows)
        else:
            raise NotImplementedError("this value of deleted not handled")
        return x

    def converter(self, row_field_list):
        return reportcore.as_python(row_field_list, to_localtime=self.to_localtime)

    def row_factory(self, row_field_list, mixin, cls_members=None):
        self.DataRow = reportcore.fixedrecord(
            "DataRow",
            [r[0] for r in row_field_list],
            mixin=mixin,
            cls_members=cls_members,
        )
        to_python = self.converter(row_field_list)

        def init_bare(r):
            nonlocal to_python, self
            return self.DataRow(*to_python(r))

        def init_custom(r):
            nonlocal to_python, self
            x = self.DataRow(*to_python(r))
            x._rtlib_init_()
            return x

        return init_custom if hasattr(self.DataRow, "_rtlib_init_") else init_bare

    def recorded_delete(self, row):
        index = self.rows.index(row)
        if index < 0:
            return

        # TODO:  this is a dirty hack to get into setattr which will set the screen dirty
        row.__deleted__ = True

        self.deleted_rows.append(row)
        del self.rows[index]

    @contextlib.contextmanager
    def adding_row(self):
        row = self.flipper_row()
        yield row
        self.rows.append(row)
        if hasattr(row, "_row_added_"):
            row._row_added_()

    def flipper_row(self):
        newself = self.DataRow.__new__(self.DataRow)
        try:
            newself._init_block = True
            newself.__init__(**{a: None for a in self.DataRow.__slots__})
            if hasattr(newself, "_init_flipper_"):
                newself._init_flipper_()
            return newself
        finally:
            newself._init_block = False

    def as_html(self, **kwargs):
        return TypedTable(self.columns, self.rows).as_html(**kwargs)

    def as_html_xml(self, **kwargs):
        return TypedTable(self.columns, self.rows).as_html_xml(**kwargs)

    def as_form_html(self, row=None, exclude=None, include=None, labels=True):
        return TypedTable(self.columns, self.rows).as_form_html(
            row=row, exclude=exclude, include=include, labels=labels
        )

    def as_tab2(self, column_map=None):
        """
        This function is serializing function somewhat like as_http_post_file.
        Perhaps they should be more related.
        """
        # TODO: return meta constructed from columns?
        if column_map == None:
            column_map = {}
        columns = [(c, column_map.get(c, None)) for c in self.DataRow.__slots__]
        rows = [r._as_tuple() for r in self.rows]
        return columns, rows

    def as_writable(
        self, exclusions=None, inclusions=None, extensions=None, getter=None
    ):
        assert exclusions == None or inclusions == None

        skipped = [c.attr for c in self.columns_full if c.skip_write]
        # skipped is added to exclusions, but note that inclusions is evaluated first
        if len(skipped) > 0:
            if exclusions == None:
                exclusions = []
            exclusions += skipped

        if (
            exclusions == None
            and inclusions == None
            and extensions == None
            and getter == None
        ):
            attrs = self.DataRow.__slots__
            slimrows = [r._as_tuple() for r in self.rows]
        else:
            if inclusions != None:
                attrs = list(inclusions)
            elif exclusions != None:
                attrs = [a for a in self.DataRow.__slots__ if a not in exclusions]
            else:
                attrs = list(self.DataRow.__slots__)
            if extensions != None:
                attrs += list(extensions)

            getter = getter if getter != None else getattr
            slimrows = []
            for r in self.rows:
                slim = [getter(r, a) for a in attrs]
                slimrows.append(slim)

        keys = {}
        if len(self.deleted_rows):
            if len(self.pkey) == 0:
                raise RuntimeError(
                    "no primary key declared; needed for deleted row set"
                )
            pfunc = lambda row: [getattr(row, p1) for p1 in self.pkey]
            keys["deleted"] = [pfunc(row) for row in self.deleted_rows]
        return (keys, attrs, slimrows)

    def as_http_post_file(self, *args, **kwargs):
        tab3 = self.as_writable(*args, **kwargs)
        return server.to_json(tab3)


class UnparsingClientTable(ClientTable):
    """
    This class reconstructs the ClientTable object model from rtlib table
    2-tuple which has not passed through JSON serialization.  A principle
    difference is that dates handled as their python native datetime types and
    not reconstructed from strings.  The general issue is that JSON has less
    native types than Python.
    """

    def converter(self, row_field_list):
        return reportcore.as_client(row_field_list, to_localtime=self.to_localtime)

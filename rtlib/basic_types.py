import datetime
from . import formatters
from . import reportcore


class BasicTypePlugin:
    def polish(self, attr, type_, meta):
        if type_ != None:
            if type_ == "boolean":
                meta["formatter"] = lambda v: "\u2713" if v else ""
                meta["alignment"] = "hcenter"
                meta["char_width"] = 6
                meta["coerce_edit"] = reportcore.parse_bool
            if type_ == "dictionary":
                f = lambda v: str(v)
                meta["formatter"] = formatters.as_xlsx(f)(
                    f
                )  # apply decorator in ugly way
            if type_ == "stringlist":
                f = (
                    lambda v: "; ".join([xx for xx in v if xx != None])
                    if v != None
                    else ""
                )
                meta["formatter"] = formatters.as_xlsx(f)(
                    f
                )  # apply decorator in ugly way
            if type_ == "integer":
                meta["formatter"] = formatters.integer_formatter
                meta["alignment"] = "right"
                meta["is_numeric"] = True
                meta["char_width"] = 10
            if type_ == "numeric":
                kw = meta.get("widget_kwargs", None)
                decimals = kw.get("decimals", 2) if kw != None else 2
                meta[
                    "formatter"
                ] = lambda value, decimals=decimals: formatters.fixedpoint_nan_formatter(
                    value, decimals
                )
                meta["coerce_edit"] = formatters.float_coerce
                meta["alignment"] = "right"
                meta["is_numeric"] = True
            if type_ == "percent":
                meta["formatter"] = formatters.percent_formatter
                meta["alignment"] = "right"
                meta["coerce_edit"] = float
                meta["is_numeric"] = True
                meta["char_width"] = 6
            if type_ == "filesize":
                meta["formatter"] = formatters.filesize_formatter
                meta["alignment"] = "right"
                meta["is_numeric"] = True
            if type_ == "html":
                meta["char_width"] = 30
            if type_ == "multiline":
                meta["char_width"] = 20
            if type_ == "date":
                meta["formatter"] = formatters.date_formatter
                meta["coerce_edit"] = formatters.date_coerce
                meta["char_width"] = 8
            if type_ == "datetime":
                meta["formatter"] = formatters.datetime_formatter
                meta["char_width"] = 16
            if type_ == "datetimeflex":
                meta["formatter"] = (
                    lambda v: formatters.datetime_formatter(v)
                    if isinstance(v, datetime.datetime)
                    else formatters.date_formatter(v)
                )
                meta["char_width"] = 16
            if type_ == "currency_usd":
                meta["alignment"] = "right"
                meta["is_numeric"] = True
                meta["char_width"] = 10
                kw = meta.get("widget_kwargs", {})
                if kw.get("blankzero", False):
                    meta["formatter"] = lambda v: formatters.dollar_formatter(
                        v, blankzero=True
                    )
                else:
                    meta["formatter"] = formatters.dollar_formatter
                meta["coerce_edit"] = formatters.currency_coerce

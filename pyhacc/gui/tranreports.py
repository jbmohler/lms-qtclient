import re
import itertools
import rtlib.server as rtserve


def group_header_profit(wbhelper, worksheet, bounding_box, first_row, header_index):
    merge = "{}:{}".format(
        bounding_box.columns[0].cell(header_index),
        bounding_box.columns[-1].cell(header_index),
    )
    worksheet.merge_range(merge, first_row.atype_name, wbhelper.group_header)

    return 1


def group_footer_profit(wbhelper, worksheet, bounding_box, footer_index):
    i1 = bounding_box.row_index_start
    i2 = bounding_box.row_index_end

    def is_totaled(col):
        return None != re.match("^(debit|credit|balance)(_|)[0-9]*$", col.attr)

    totaled = [col for col in bounding_box.columns if is_totaled(col)]

    for col in totaled:
        formula = f"=SUM({col.cell(i1)}:{col.cell(i2)})"
        total = sum(
            [
                getattr(row, col.attr)
                for row in bounding_box.rows
                if getattr(row, col.attr) != None
            ]
        )
        worksheet.write_formula(
            footer_index, col.index, formula, wbhelper.bold_currency_format, value=total
        )

    if len(totaled):
        totind = min(col.index for col in totaled)
        worksheet.write(footer_index, totind - 1, "Total", wbhelper.bold_format)

    return 2


class AccountTypeGrouped:
    TITLE = "Type Summarized Excel"

    def export(self, fname, v, content, hyperlinks=True):
        rtserve.export_view(
            fname,
            v,
            headers=content.keys["headers"],
            options={"row_group": "atype_name"},
            sort_key="(atype_sort, jrn_name, acc_name)",
            suppress_grouped_column=True,
            group_start_callback=group_header_profit,
            group_end_callback=group_footer_profit,
            hyperlinks=hyperlinks,
        )


def full_summary(wbhelper, worksheet, bounding_box, footer_index):
    i1 = bounding_box.row_index_start
    i2 = bounding_box.row_index_end

    def is_totaled(col):
        return None != re.match("^(debit|credit|balance|amount)(_|)[0-9]*$", col.attr)

    totaled = [col for col in bounding_box.columns if is_totaled(col)]

    for col in totaled:
        formula = f"=SUM({col.cell(i1)}:{col.cell(i2)})"
        total = sum(
            [
                getattr(row, col.attr)
                for row in bounding_box.rows
                if getattr(row, col.attr) != None
            ]
        )
        worksheet.write_formula(
            footer_index, col.index, formula, wbhelper.bold_currency_format, value=total
        )

    if len(totaled):
        totind = min(col.index for col in totaled)
        worksheet.write(footer_index, col.index, "Total", wbhelper.bold_format)

    return 2


class FullGrouped:
    TITLE = "Summarized Excel"

    def export(self, fname, v, content, hyperlinks=True):
        model = v.model()
        model.rows.sort(key=lambda x: x.payee)
        sums = []
        nz = lambda v: v if v != None else 0.0
        for key, xx in itertools.groupby(model.rows, lambda x: x.payee):
            sums.append((key, sum([nz(x.debit) - nz(x.credit) for x in xx])))
        sums.sort(key=lambda x: -x[1])
        assign = {}
        for index, tu in enumerate(sums):
            assign[tu[0]] = index
        for row in model.rows:
            row.sort_index = assign[row.payee]

        rtserve.export_view(
            fname,
            v,
            headers=content.keys["headers"],
            options={"row_group": "payee"},
            sort_key="(sort_index, payee, date)",
            group_end_callback=full_summary,
            hyperlinks=hyperlinks,
        )

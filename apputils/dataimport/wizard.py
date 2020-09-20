import os
import csv
import decimal
import datetime
from PySide2 import QtWidgets
import apputils
import apputils.models as models
import apputils.widgets as widgets
import fuzzyparsers


class ImportColumn:
    def __init__(self, identifier, label):
        self.identifier = identifier
        self.label = label


class ImportIntroPage(QtWidgets.QWizardPage):
    """
    This wizard page takes a class and displays the elements of that class for 
    import.
    """

    def __init__(self, parent=None):
        QtWidgets.QWizardPage.__init__(self, parent)
        self.setTitle("Data Import")
        self.setSubTitle(
            "\
The list of available fields in the import class are shown below.  Columns in \
import files are first matched with exact matches in the identifier list and then \
matched against prefixes of the labels."
        )

        main = QtWidgets.QVBoxLayout(self)
        self.table = widgets.TableView()
        main.addWidget(self.table)

        columns = [
            models.Column("identifier", "Identifier"),
            models.Column("label", "Label"),
        ]
        self.model = apputils.ObjectQtModel(columns)
        self.table.setModel(self.model)

    def load_import_column(self, columns):
        items = [ImportColumn(c.attr, c.label) for c in columns]
        items.sort(key=lambda x: x.label)
        self.model.set_rows(items)


class ImportDataSource(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        QtWidgets.QWizardPage.__init__(self, parent)
        self.setTitle("Data Import")
        self.setSubTitle("Select a file from which to import the data.")

        main = QtWidgets.QVBoxLayout(self)

        f2 = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        self.file_edit.textChanged.connect(lambda *args: self.completeChanged.emit())
        self.label = QtWidgets.QLabel("&Data File:")
        self.label.setBuddy(self.file_edit)
        self.browse = QtWidgets.QPushButton("Bro&wse...")
        self.browse.clicked.connect(self.import_browse)

        f2.addWidget(self.label)
        f2.addWidget(self.file_edit)
        f2.addWidget(self.browse)

        main.addLayout(f2)

    def import_browse(self):
        fileName = apputils.get_open_filename(
            self,
            "Data for Import",
            filter="Comma Separated Values (*.csv);;All Files (*.*)",
            dirname=self.master.dirname,
        )
        if fileName != None:
            self.file_edit.setText(fileName)
            self.completeChanged.emit()

    def isComplete(self):
        return os.path.isfile(self.file_edit.text())


class ImportDataPreview(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        QtWidgets.QWizardPage.__init__(self, parent)
        self.setTitle("Data Import")
        self.setSubTitle("Preview the imported data.")

        main = QtWidgets.QVBoxLayout(self)
        self.table = widgets.TableView()
        main.addWidget(self.table)

    def load_data(self, cls, columns, csv_file):
        imported_rows = []

        delimiter = ","
        with open(csv_file, "r") as f:
            firstline = f.readline()
            if "\t" in firstline:
                delimiter = "\t"

        errors = []
        warnings = []
        cols = None
        index = 0
        mapped_columns = []  # tuples of column index and target
        for row in csv.reader(open(csv_file, "r"), delimiter=delimiter):
            if cols is None:
                cols = []
                cm = {c.attr: c for c in columns}
                for index, header in enumerate(row):
                    target = None
                    h = header.strip()
                    if h in cm:
                        target = cm[h]
                    elif len(h) > 0:
                        for c in columns:
                            if c.label.lower().startswith(h.lower()):
                                target = c
                    if target != None:
                        cols.append(target)
                        mapped_columns.append((index, target))
                    else:
                        warnings.append(f"Heading {h} (column {index}) is ignored.")
            else:
                try:
                    index += 1
                    values = {}
                    for i, c in mapped_columns:
                        v = c.coerce_edit(row[i])
                        # type_ = str
                        # v = row[i]
                        # if type_ in (decimal.Decimal, int, float) and v == '':
                        #    v = '0'
                        # if type_ in (datetime.date, ):
                        #    v = fuzzyparsers.parse_date(v)
                        # if not isinstance(v, type_):
                        #    v = type_(v)

                        values[c.attr] = v
                    imported_rows.append(cls(**values))
                except Exception as e:
                    errors.append(f"Row {index}:  {str(e)}")

        errors = warnings + errors
        if len(errors) > 0 and len(errors) <= 5:
            text = """\
There were {0} errors or warnings importing the data.

\t{1}""".format(
                len(errors), "\n\t".join(errors)
            )
            apputils.message(self, text)
        elif len(errors) > 5:
            text = """\
There were {0} errors or warnings importing the data.  The first 5 are shown below.

\t{1}""".format(
                len(errors), "\n\t".join(errors[:5])
            )
            apputils.message(self, text)

        self.model = models.ObjectQtModel(cols)
        self.table.setModel(self.model)
        self.model.set_rows(imported_rows)

    def finishImport(self):
        self.master.imported_rows = self.model.rows


class ImportWizard(QtWidgets.QWizard):
    """
    Returns a QWizard to take rows given by the user and create an instance 
    of each cls from each row.  The rows may come from a csv file or via raw 
    entry in a table.

    Wizard Structure:

    - Intro page listing accepted elements of the class cls
    - Page asking for an input csv file or allowing raw entry
    - Page with list of data or allowing entry
    
    >>> from apputils.dataimport import *
    >>> import collections
    >>> from PySide import QtCore, QtGui
    >>> 
    >>> columns = [
    ...     models.Column('warehouse', 'Warehouse'),
    ...     models.Column('location', 'Location'),
    ...     models.Column('inventory_id', 'Item'),
    ...     models.Column('count', 'Count')]
    ... 
    >>> n = collections.namedtuple('MyImport', 'warehouse location inventory_id count'.split(' '))
    >>> app = apputils.transient_app()
    >>> wiz = ImportWizard(n, columns)
    >>> wiz.show()  #doctest: +SKIP
    >>> wiz.exec_()  #doctest: +SKIP
    >>> # for row in wiz.imported_rows:
    >>> #     do_something_with(row)
    """

    def __init__(self, cls, columns, dirname=None, parent=None):
        super(ImportWizard, self).__init__(parent)

        self.columns = columns
        self.cls = cls
        self.dirname = dirname

        self.setWindowTitle("Import Wizard")

        self.intro = ImportIntroPage()
        self.intro.load_import_column(columns)

        self.dataSource = ImportDataSource()
        self.dataSource.master = self

        self.dataPreview = ImportDataPreview()
        self.dataPreview.master = self

        self.introId = self.addPage(self.intro)
        self.sourceId = self.addPage(self.dataSource)
        self.previewId = self.addPage(self.dataPreview)

        self.currentIdChanged.connect(self.pageFlip)
        self.accepted.connect(self.dataPreview.finishImport)

    def pageFlip(self, newid):
        if newid == self.previewId:
            self.dataPreview.load_data(
                self.cls, self.columns, self.dataSource.file_edit.text()
            )

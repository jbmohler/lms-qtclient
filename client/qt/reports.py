"""
Reports list should have URL, title, prompts ...


Reports will have wonderful things like:

    - import print
    - (done) showing prompts
    - (done) export to excel
    - custom columns
    - (done) re-orderable columns

I don't yet know how to:

    - show crystal reports in this list
    - add reports in some abstract manor where the server doesn't know about
      the report
"""

import time
import datetime
import functools
import itertools
import collections
from PySide2 import QtCore, QtGui, QtWidgets
import rtlib
import apputils
import apputils.widgets as widgets
import apputils.models as models
import apputils.viewmenus as viewmenus
from . import utils
from . import dialogs
from . import layoututils
from . import gridmgr
from . import icons


def rtapp_report_sidebar(sbkey):
    app = QtCore.QCoreApplication.instance()
    if hasattr(app, 'report_sidebar'):
        return app.report_sidebar(sbkey, app.session, app.exports_dir)

def rtapp_report_export(expkey):
    app = QtCore.QCoreApplication.instance()
    if hasattr(app, 'report_export'):
        return app.report_export(expkey, app.session, app.exports_dir)

class SidebarInterface:
    def __init__(self, session, exports_dir, parent=None):
        """start it up"""
        pass

    def set_report_keys(self, keys, prompts):
        """
        Orient the sidebar to this report with keys return of report from the
        server.  This is called once.
        """
        pass

    def highlight(self, row):
        """
        This is called with the highlighted row when it changes.
        """
        pass


class ReportClientInfo:
    # prompts
    # defaults
    # description
    # url

    def __init__(self, report):
        self.description = report.description
        self.note = report.note
        self.id = report.id
        self.name = report.act_name
        if hasattr(report, 'role'):
            self.role = report.role
            self.role_sort = report.role_sort
        self.url = report.url
        if len(report.prompts) > 0 and not isinstance(report.prompts[0], rtlib.Column):
            self.prompts = rtlib.PromptList(report.prompts)
            self.defaults = self.prompts.defaults
        else:
            self.prompts = rtlib.PromptList()
            self.defaults = self.prompts.defaults

    def prepare_url(self, values):
        run = ReportRun()
        values = values.copy()
        run.prompt_values = values

        tail = self.url
        params = {}
        for prompt, default in zip(self.prompts, self.defaults):
            if prompt.attr in values:
                v = values[prompt.attr]
            else:
                v = default
                values[prompt.attr] = v
            placeholder = '<{}>'.format(prompt.attr)
            if tail.find(placeholder) >= 0:
                tail = tail.replace(placeholder, v)
            else:
                params[prompt.attr] = v
        return run, tail, params

class ReportRun:
    # info - ReportClientInfo
    # timestamp
    # prompt_values: {map prompt names to values}
    # content

    def set_content(self, content):
        self.content = content
        self.timestamp = datetime.datetime.now()


class TreeRowMixin:
    @property
    def _children(self):
        return self._inners if hasattr(self, '_inners') else []


class ReportLaunch(QtWidgets.QWidget):
    launch = QtCore.Signal()

    def __init__(self, previewer, report, parent=None):
        super(ReportLaunch, self).__init__(parent)

        self.previewer = previewer
        self.report = report
        self.obscured = parent
        self.obscured.installEventFilter(self)

        self.move(self.obscured.pos())
        self.resize(self.obscured.size())
        self.show()

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.l1 = QtWidgets.QVBoxLayout()
        self.l2 = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.l1)
        self.layout.addLayout(self.l2)

        #self.setAutoFillBackground(True)
        #p = self.palette()
        #p.setColor(self.backgroundRole(), QtGui.QColor('#c0c0c0'))
        #self.setPalette(p)

        self.gobutton = QtWidgets.QPushButton('Go')
        self.gobutton.setIcon(QtGui.QIcon(':/clientshell/play.png'))
        self.gobutton.clicked.connect(self.launch.emit)
        self.note = QtWidgets.QLabel(self.report.note)
        self.note.setWordWrap(True)
        self.note.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        self.l1.addWidget(self.gobutton)
        self.l1.addStretch(5)
        self.l2.addWidget(self.note)
        self.l2.addStretch(1)

    def eventFilter(self, obj, ev):
        if obj == self.obscured and ev.type() == QtCore.QEvent.Resize:
            self.move(self.obscured.pos())
            self.resize(self.obscured.size())
            #self.show()
        return False


class SidebarWrapper(QtWidgets.QMainWindow):
    def closeEvent(self, event):
        if self._preview != None and self.isVisible():
            self._preview.liberate_sidebar(by_close_button=True)
        return super(SidebarWrapper, self).closeEvent(event)

class ReportPreview(QtWidgets.QWidget):
    def __init__(self, report, session, exports_dir, manager=None):
        super(ReportPreview, self).__init__(manager.main_window)

        self.is_running = False
        self.needs_explicit_close = False

        # 2) Init connections
        self.report = report
        self.client = session.std_client()
        self.backgrounder = apputils.Backgrounder(self)
        self.exports_dir = exports_dir

        # 3) Make widgets
        self.layout = QtWidgets.QVBoxLayout(self)
        #self.layout.setContentsMargins(0, 5, 0, 0)
        self.top_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(self.top_layout)

        self.sidebar_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.grid = widgets.TreeView()
        self.grid.header().setStretchLastSection(False)
        self.grid.setUniformRowHeights(True)
        self.grid.setGridLines(True)
        self.grid.setSelectionBehavior(self.grid.SelectItems)
        self.grid.setSelectionMode(self.grid.ExtendedSelection)
        self.grid.setSortingEnabled(True)

        self.gridmgr = gridmgr.GridManager(self.grid, self)
        self.gridmgr.ctxmenu.triggerReload.connect(self.launch_report)
        self.gridmgr.ctxmenu.statisticsUpdate.connect(self.stat_update)

        self.layout.addWidget(self.sidebar_split)
        self.sidebar_split.addWidget(self.grid)

        self._sidebar_lock = False
        self.sidebar_wrapper = None
        self.sidebar = rtapp_report_sidebar(self.report.name)
        if self.sidebar != None and isinstance(self.sidebar, QtWidgets.QWidget):
            self.sidebar_split.addWidget(self.sidebar)
            self.sidebar_split.setStretchFactor(0, 5)
            self.sidebar_split.setStretchFactor(1, 1)

            self.sidebar_free_action = QtWidgets.QAction('&Liberate Sidebar', self)
            self.sidebar_free_action.setCheckable(True)
            self.sidebar_free_action.setShortcut('Ctrl+Right')
            self.sidebar_free_action.triggered.connect(self.liberate_sidebar)
            self.addAction(self.sidebar_free_action)

            if hasattr(self.sidebar, 'toggle_liberated'):
                self.sidebar.toggle_liberated.connect(self.liberate_sidebar)
        if hasattr(self.sidebar, 'refresh'):
            self.sidebar.refresh.connect(self.launch_report)

        self.prompt_form = dialogs.InternalLabelFormLayout()
        if len(self.report.prompts.optional_attrs) > 0:
            self.opt_group = QtWidgets.QGroupBox('Optional Filters')
            self.opt_prompt_form = dialogs.InternalLabelFormLayout(self.opt_group)

        self.bound_prompts = collections.OrderedDict()
        for prompt in self.report.prompts:
            widget = prompt.widget_factory(self, **prompt.widget_kwargs)
            self.bound_prompts[prompt.attr] = (prompt, widget)

        relevance = {v[0] for v in self.report.prompts.relevance_groups.values()}
        for prompt in self.report.prompts:
            if prompt.attr in relevance:
                continue
            if prompt.attr in self.report.prompts.optional_attrs:
                form = self.opt_prompt_form
            else:
                form = self.prompt_form
            if prompt.attr in self.report.prompts.relevance_groups:
                rtuple = self.report.prompts.relevance_groups[prompt.attr]
                if rtuple[1] == 'relevant-if-not':
                    def update_relevant_enabled(w1, w2, neg_value):
                        curr = w1.value()
                        w2.setEnabled(curr != neg_value)

                    widget = QtWidgets.QWidget()
                    widget.lay2 = QtWidgets.QHBoxLayout(widget)
                    widget.lay2.setContentsMargins(0, 0, 0, 0)

                    w1 = self.bound_prompts[rtuple[0]][1]
                    w2 = self.bound_prompts[prompt.attr][1]
                    widget.lay2.addWidget(w1)
                    widget.lay2.addWidget(w2)

                    self.bound_prompts[rtuple[0]][1].valueChanged.connect(lambda w1=w1, w2=w2, neg_value=rtuple[2]: update_relevant_enabled(w1, w2, neg_value))
                elif rtuple[1] == 'end-range':
                    widget = QtWidgets.QWidget()
                    widget.lay2 = QtWidgets.QHBoxLayout(widget)
                    widget.lay2.setContentsMargins(0, 0, 0, 0)

                    endprompt = self.bound_prompts[rtuple[0]][0]
                    if prompt.label.startswith('Begin ') and endprompt.label.startswith('End '):
                        prompt.label = prompt.label[6:]
                    elif prompt.label.startswith('First ') and endprompt.label.startswith('Last '):
                        prompt.label = prompt.label[6:]

                    w1 = self.bound_prompts[rtuple[0]][1]
                    w2 = self.bound_prompts[prompt.attr][1]
                    widget.lay2.addWidget(w2)
                    widget.lay2.addWidget(QtWidgets.QLabel('to'))
                    widget.lay2.addWidget(w1)
                    widget.lay2.addWidget(layoututils.stretcher())
                else:
                    raise NotImplementedError('relevancy method {} not known.'.format(rtuple[1]))
            else:
                widget = self.bound_prompts[prompt.attr][1]
            form.addRow(prompt.label, widget)

        prompts = [w for p, w in self.bound_prompts.values()]
        apputils.verify_settings_load(self, self.client, prompts)

        self.load_values({p.attr: v for p, v in zip(self.report.prompts, self.report.defaults)})

        self.layout.setStretch(1, 3)

        self.top_layout.addLayout(self.prompt_form)
        if len(self.report.prompts.optional_attrs) > 0:
            self.top_layout.addWidget(self.opt_group)

        self.hlayout = QtWidgets.QVBoxLayout()
        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.headers = QtWidgets.QLabel()
        self.hlayout.addWidget(self.headers)
        self.hlayout.addStretch(2)
        self.top_layout.addLayout(self.hlayout)

        self.top_layout.addStretch(3)

        self.buttons = QtWidgets.QDialogButtonBox(QtCore.Qt.Vertical)
        self.top_layout.addWidget(self.buttons)
        self.preview_button = QtWidgets.QPushButton('&Refresh')
        self.preview_button.clicked.connect(self.launch_report)
        self.export_button = QtWidgets.QPushButton('&Export')
        self.export_button.clicked.connect(self.export_data)
        self.buttons.addButton(self.preview_button, QtWidgets.QDialogButtonBox.ActionRole)
        self.buttons.addButton(self.export_button, QtWidgets.QDialogButtonBox.ActionRole)

        self.power_menu = QtWidgets.QMenu()
        self.power_btn = QtWidgets.QPushButton('&Tools')
        self.power_btn.setMenu(self.power_menu)

        if self.client.session.authorized('put_api_activities'):
            self.power_menu.addAction('&Edit Note').triggered.connect(self.cmd_edit_activity)

        self.button2 = QtWidgets.QDialogButtonBox(QtCore.Qt.Vertical)
        self.button2.addButton(self.power_btn, self.button2.ActionRole)
        self.top_layout.addWidget(self.button2)

        self.export_button.setEnabled(False)
        self.launcher = None

        self.geo = apputils.WindowGeometry(self, size=False, position=False, name=self.settings_key(), splitters=[self.sidebar_split])

    def cmd_edit_activity(self):
        content = self.client.get('api/activity/{}', self.report.autoid)
        t = rtlib.ClientTable(*content[1:])
        from . import useradmin
        if useradmin.edit_activity_dlg(self, t):
            self.report.description = t.rows[0].description
            self.report.note = t.rows[0].note
            self.note.setText(t.rows[0].note)

    def liberate_sidebar(self, *args, by_close_button=False):
        if self._sidebar_lock:
            return
        if self.sidebar == None:
            return

        liberated = self.sidebar_split.count() == 1

        if hasattr(self.sidebar, 'action_liberate'):
            self._sidebar_lock = True
            self.sidebar.action_liberate.setChecked(not liberated)
            self._sidebar_lock = False

        if liberated:
            if self.sidebar_wrapper != None:
                wrap = self.sidebar_wrapper

                # save relative location of wrapper
                tr = self.mapToGlobal(self.rect().topRight())
                tl = wrap.frameGeometry().topLeft()
                self.geo.save_xdata('liberator', locate=(tl-tr), size=wrap.size())

                self.sidebar_split.addWidget(self.sidebar_wrapper.centralWidget())
                self.sidebar_wrapper = None
                if not by_close_button:
                    wrap._preview = None
                    wrap.close()
        else:
            self.sidebar_wrapper = SidebarWrapper()
            self.sidebar_wrapper._preview = self
            self.sidebar_wrapper.setWindowIcon(QtWidgets.QApplication.instance().icon)
            self.sidebar_wrapper.setWindowTitle('{} Details'.format(self.report.description))

            self.sidebar_wrapper.setCentralWidget(self.sidebar)
            self.sidebar_wrapper.show()

            # retrieve relative location of wrapper
            tr = self.mapToGlobal(self.rect().topRight())
            xdata = self.geo.read_xdata('liberator')
            offset = xdata.get('locate', QtCore.QPoint(10, 0))
            self.sidebar_wrapper.move(tr+offset)

            def_size = self.size()
            def_size.setWidth(def_size.width() // 4 * 3)
            size = xdata.get('size', def_size)
            self.sidebar_wrapper.resize(size)

    def place_launcher(self):
        self.launcher = ReportLaunch(self, self.report, self.grid)
        self.launcher.resize(self.grid.size())
        self.launcher.launch.connect(self.launch_report)
        self.launcher.show()

    def stat_update(self, elements):
        try:
            sb = self.window().statusBar()
        except:
            sb = None

        if sb == None or not hasattr(sb, 'statistics'):
            return

        if len(elements) > 0:
            stats = []
            for stat, act in sb.statistics.actions_stattypes.items():
                if act.isChecked():
                    if stat == 'count':
                        stats.append('Count:  {}'.format(len(elements)))
                    if stat == 'total':
                        stats.append('Total:  {}'.format(sum(elements)))
                    if stat == 'average':
                        avg = sum(elements)/len(elements)
                        stats.append('Average:  {}'.format(avg))
                    if stat == 'minimum':
                        stats.append('Minimum:  {}'.format(min(elements)))
                    if stat == 'maximum':
                        stats.append('Maximum:  {}'.format(max(elements)))
            sb.statistics.setText('; '.join(stats))
        else:
            sb.statistics.setText('')

    def export_data(self):
        fname = self.exports_dir.user_output_filename(self.report.description, 'xlsx')

        rtlib.server.export_view(fname, self.grid, self.header_strings)
        utils.xlsx_start_file(self.window(), fname)

    def export_data_custom(self, export):
        fname = self.exports_dir.user_output_filename(self.report.description, 'xlsx')
        export.export(fname, self.grid, self.run.content)
        utils.xlsx_start_file(self.window(), fname)

    def launch_report(self):
        if self.launcher != None:
            self.launcher.hide()
        self.needs_explicit_close = True
        values = {}
        for k, v in self.bound_prompts.items():
            try:
                values[k] = v[1].value()
            except apputils.ModValueError as e:
                if v[0].attr in self.report.prompts.optional_attrs:
                    m = 'Clear {} or enter a valid value.\n\n{}'
                else:
                    m = 'Enter a valid value for {}.\n\n{}'
                apputils.information(self.window(), m.format(v[0].label, str(e)))
                return
        self.run, tail, params = self.report.prepare_url(values)
        self.backgrounder.named['main-report'](self.run_wrapper, self.client.get, tail, **params)

    def run_wrapper(self):
        self.is_running = True
        try:
            content = yield apputils.JointBackgrounder(apputils.AnimateWait(self.grid), self.report_request_waiter())
        except:
            utils.exception_message(self.window(), 'The report {} generated a server error.'.format(self.report.description))
            return
        finally:
            if self.grid.model() != None:
                apputils.write_grid_geometry(self.grid, self.settings_key())
            self.clear_run_status()
        self.process_report_data(content)

    def load_values(self, values, from_strings=False):
        v2 = values.copy()
        if from_strings:
            for prompt in self.report.prompts:
                if prompt.attr in v2:
                    v2[prompt.attr] = rtlib.str_column_coerce(prompt, v2[prompt.attr])
        for k, pw in self.bound_prompts.items():
            if k in v2:
                pw[1].setValue(v2[k])
            pw[1].setWidgetModified(True)

    def clear_run_status(self):
        self.is_running = False
        self.grid.setModel(None)
        self.headers.setText('')
        self.headers.setStyleSheet(None)
        self.export_button.setEnabled(False)

    def process_report_data(self, content):
        self.needs_explicit_close = True
        self.export_button.setEnabled(True)
        self.run.set_content(content)
        self._prepare_current_run()

    def watch_run(self):
        while True:
            time.sleep(.05)
            if hasattr(self.run, 'content'):
                return self.run.content

    def set_imported_run(self, run):
        self.run = run
        self.load_values(self.run.prompt_values)
        if hasattr(run, 'content'):
            self.needs_explicit_close = True
            self.export_button.setEnabled(True)
            self._prepare_current_run()
        else:
            self.backgrounder(self.run_wrapper, self.watch_run)

    def _prepare_current_run(self):
        self.header_strings = self.run.content.keys['headers']
        self.expansions = self.run.content.keys.get('expansions', [])
        mixin = None if len(self.expansions) == 0 else TreeRowMixin
        self.report_data = self.run.content.main_table(mixin=mixin)
        self.stack = [self.report_data]
        column_stack = self.run.content.main_columns()
        for t, _ in self.expansions:
            column_stack.append(self.run.content.named_columns(t))
            self.stack.append(self.run.content.named_table(t, mixin=mixin))

        self.grid.setRootIsDecorated(len(self.stack) > 1)

        if len(self.stack) == 1:
            self.model = gridmgr.client_table_as_model(self.report_data, self, True)
            for col in self.report_data.columns_full:
                if col.type_ == 'text_color':
                    self.model.rowprops['foreground'] = col.attr
        else:
            # A "ragged" group-by report is one whose header rows are not
            # simply aggregates of sent rows.  The following code supports this
            # as configured by "keys['expansions']".

            # make an aggregate type & model
            exp = rtlib.ExpansionAlignment(*tuple(column_stack))
            classes = [t.DataRow for t in self.stack]
            self.model = models.TieredObjectQtModel(rtlib.parse_columns(exp.aggregate), classes, descendant_attr='_children')

            keys = []
            for index in range(len(self.expansions)):
                keyfields = [e[1] for e in self.expansions[:1+index]]
                keys.append(lambda x, kf=keyfields: tuple([getattr(x, k) for k in kf]))

            # Note that there is (according to the unpacking of the content
            # above) exactly one more table in self.stack than there is
            # expansions.
            for index in range(len(self.expansions)):
                # use keys[index] to group self.stack[index+1].rows in self.stack[index](==table)
                inners = {key: list(grp) for key, grp in itertools.groupby(self.stack[index+1].rows, key=keys[index])}
                for wrow in self.stack[index].rows:
                    wrow._inners = inners.get(keys[index](wrow), [])

            self.model.set_rows(self.stack[0].rows)

        self.grid.setModel(self.model)

        self.selmodel = self.grid.selectionModel()
        self.selmodel.currentRowChanged.connect(self.update_report_line_selection)

        if 'report-formats' in self.run.content.keys:
            menu = QtWidgets.QMenu()
            for fmt in self.run.content.keys['report-formats']:
                export = rtapp_report_export(fmt)
                f = functools.partial(self.export_data_custom, export)
                menu.addAction(export.TITLE).triggered.connect(f)
            menu.addAction('&Flat Export').triggered.connect(self.export_data)
            self.export_button.setMenu(menu)
            self.rpt_export_menu = menu

        augmented_head = self.header_strings.copy()
        augmented_head.append('{:,} rows'.format(len(self.model.rows)))
        self.headers.setStyleSheet('QLabel {background: white; padding: 5px}')
        self.headers.setText('\n'.join(augmented_head))

        apputils.read_grid_geometry(self.grid, self.settings_key())

        if self.sidebar != None and hasattr(self.sidebar, 'set_report_keys'):
            self.sidebar.set_report_keys(self.run.content.keys, self.run.prompt_values)
        if self.sidebar != None and hasattr(self.sidebar, 'init_grid_menu'):
            self.sidebar.init_grid_menu(self.gridmgr)

        self.gridmgr._post_model_action()
        # add client-row-relateds
        gridmgr.apply_client_row_relateds(self.gridmgr.ctxmenu, self.run.content)
        self.my_actions = gridmgr.apply_client_relateds(self.power_menu, self.run.content)

    def settings_key(self):
        return 'reports/{}'.format(self.report.url.replace('/', '_'))

    def update_report_line_selection(self, current, previous):
        if self.sidebar != None and hasattr(self.sidebar, 'highlight'):
            row = current.data(models.ObjectRole)
            if row != None:
                # remake row from the row with the appointed info
                params = {k: getattr(row, v) for k, v in self.report.sidebars[0]['on_highlight_row'].items()}
                row = rtlib.inline_object(**params)
            self.sidebar.highlight(row)

    def closeEvent(self, event):
        if self.is_running:
            apputils.information(self.window(), 'The report is running on the server.  Aborting reports is not (yet) supported.')
            event.ignore()
            return False
        if self.grid.model() != None:
            apputils.write_grid_geometry(self.grid, self.settings_key())
        if self.sidebar_wrapper != None:
            self.sidebar_wrapper._preview = None
            self.sidebar_wrapper.close()
        return super(ReportPreview, self).closeEvent(event)


class RotatingTabTextBackgrounder:
    def __init__(self, manager, tab):
        self.manager = manager
        self.tab = tab
        self.icon = QtGui.QIcon(':/clientshell/static-spin.png')
        self.set = False

    def terminated(self, exception):
        index = self.manager.tabs.indexOf(self.tab)
        self.manager.tabs.setTabIcon(index, QtGui.QIcon())

    def continuing(self):
        if self.set:
            return
        self.set = True
        index = self.manager.tabs.indexOf(self.tab)
        self.manager.tabs.setTabIcon(index, self.icon)


class ReportsManager(QtCore.QObject):
    ID = 'reports_window'

    def __init__(self, session, exports_dir, main_window=None):
        super(ReportsManager, self).__init__(main_window)

        self.main_window = main_window
        self.tabs = main_window.workspace

        # 1) Init window
        self.setObjectName(self.ID)

        # 2) Init connections
        self.client = session.std_client()
        self.exports_dir = exports_dir
        self.backgrounder = apputils.Backgrounder(self)

    def close_tab(self, index):
        tab = self.tabs.widget(index)
        if tab.close():
            #self.disown_tab(tab)
            self.tabs.removeTab(index)

    def closeEvent(self, event):
        if len(self.backgrounder.futures) > 0:
            event.ignore()
            return False
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            widget.close()
        return super(ReportsManager, self).closeEvent(event)

    def adopt_preview(self, report, w):
        currentWidget = self.tabs.currentWidget()
        w._shell_tab_id = None
        index = self.main_window.addWorkspaceWindow(w, report.description.replace('&', '&&'), fixedpos=True)
        #self.tabs.setCurrentIndex(index)
        if currentWidget != None and \
                isinstance(currentWidget, ReportPreview) and \
                not currentWidget.needs_explicit_close:
            self.tabs.removeTab(self.tabs.indexOf(currentWidget))

    def construct_waiter(self, tab):
        return RotatingTabTextBackgrounder(self, tab)

    def preview(self, reportmeta):
        report = ReportClientInfo(reportmeta)

        w = ReportPreview(report, self.client.session, self.exports_dir, self)
        w.report_request_waiter = lambda tab=w: self.construct_waiter(tab)
        w.place_launcher()
        self.adopt_preview(report, w)

    def data_loaded_adoption(self, report, run):
        w = ReportPreview(report, self.client.session, self.exports_dir, self)
        w.report_request_waiter = lambda tab=w: self.construct_waiter(tab)
        index = self.tabs.addTab(w, report.description.replace('&', '&&'))
        self.tabs.setCurrentIndex(index)
        w.set_imported_run(run)

    def launch_with_params(self, name, values):
        cb = lambda v=values: self.run_one(True, v)
        self.backgrounder(cb, self.client, 'api/report/{}/runmeta', name)

    def preview_by_name(self, name):
        cb = lambda v={}: self.run_one(False, v)
        self.backgrounder(cb, self.client, 'api/report/{}/runmeta', name)

    def run_one(self, launch, values):
        try:
            content = yield
        except:
            utils.exception_message(self.main_window, 'Report failed to load.')
            return

        reports_data = rtlib.ClientTable(*content[1:])
        report = ReportClientInfo(reports_data.rows[0])
        w = ReportPreview(report, self.client.session, self.exports_dir, self)
        w.report_request_waiter = lambda tab=w: self.construct_waiter(tab)
        w.load_values(values, from_strings=True)
        index = self.main_window.addWorkspaceWindow(w, report.description.replace('&', '&&'), fixedpos=True)
        #self.tabs.setCurrentIndex(index)
        if launch:
            w.launch_report()
        else:
            w.place_launcher()

import urllib.parse
from PySide6 import QtCore, QtWidgets
import apputils

RTX_EXTENSION_PLUGS = []


def add_extension_plug(plug):
    global RTX_EXTENSION_PLUGS
    RTX_EXTENSION_PLUGS.append(plug)


def attr_extension_plug(attr):
    global RTX_EXTENSION_PLUGS
    for plug in RTX_EXTENSION_PLUGS:
        f = getattr(plug, attr, None)
        if f != None:
            yield f


def get_plugin_export(sbname, state=None):
    app = QtCore.QCoreApplication.instance()
    if state is None:
        state = app

    for f in attr_extension_plug("report_formats"):
        sb = f(state, sbname)
        if sb != None:
            return sb


def get_plugin_sidebar(sbname, state=None):
    app = QtCore.QCoreApplication.instance()
    if state is None:
        state = app

    for f in attr_extension_plug("load_sidebar"):
        sb = f(state, sbname)
        if sb != None:
            return sb


def get_plugin_menus():
    for f in attr_extension_plug("get_menus"):
        yield from f()


def plugin_initialize(parent):
    state = QtWidgets.QApplication.instance()

    for f in attr_extension_plug("initialize"):
        f(state, parent)


def url_params(url):
    values = urllib.parse.parse_qs(url.query())
    # dict(url.queryItems())
    # TODO figure out correct +-decoding
    # values = {k: v.replace('+', ' ') for k, v in values.items()}
    # values = {k: urllib.parse.unquote(v) for k, v in values.items()}
    values = {k: v[0] for k, v in values.items()}
    return values


def show_link_parented(parent, url):
    if not isinstance(url, QtCore.QUrl):
        url = QtCore.QUrl(url)

    if url.scheme() in ("https", "http"):
        import cliutils

        cliutils.xdg_open(url.url())
        return

    # prepare API on url for plugs
    url.parameters = lambda url=url: url_params(url)
    state = QtWidgets.QApplication.instance()

    global RTX_EXTENSION_PLUGS
    handled = False
    for plug in RTX_EXTENSION_PLUGS:
        if plug.show_link_parented(state, parent, url):
            handled = True
            break

    if not handled:
        apputils.information(parent, f"Invalid URL string:  {url}")


def show_link(url):
    from . import winlist

    show_link_parented(winlist.main_window(), url)

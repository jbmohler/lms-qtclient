# no global imports, this is a site specific file which defines the set of
# plug-ins and styling that fleshes out the rtx client.


def qt_app_init(plugpoint):
    from PySide2 import QtWidgets, QtGui
    import rtlib
    import apputils
    import client as climod
    import lmssystem.lmsicons

    app = QtWidgets.QApplication([])
    app.setOrganizationDomain('lms.kiwistrawberry.us')
    app.setOrganizationName('Mohler')
    app.setApplicationName('lms Data Suite')
    app.icon = QtGui.QIcon(':/lms/jlm_initials.ico')
    app.exports_dir = climod.LocalDirectory(appname='lmsDataSuite', tail='Exports')

    import platform
    if platform.system() == "Windows":
        # This is needed to display the app icon on the taskbar on Windows 7
        import ctypes
        myappid = f'{app.organizationDomain()}.1.0.0' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    import pyhacc.gui as pg
    import contacts.gui as cg
    import databits.gui as dbg
    import client.qt.rtauth as rtauth

    rtlib.add_type_definition_plugin(pg.AccountingWidgetsPlugin())
    rtlib.add_type_definition_plugin(rtlib.BasicTypePlugin())
    rtlib.add_type_definition_plugin(apputils.BasicWidgetsPlugin())

    plugpoint.add_extension_plug(pg.AccountingExtensions())
    plugpoint.add_extension_plug(cg.ContactExtensions())
    plugpoint.add_extension_plug(dbg.DataBitExtensions())
    plugpoint.add_extension_plug(rtauth.RtAuthPlugs())

    app.report_sidebar = plugpoint.search_sidebar
    app.report_export = plugpoint.search_export

    return app

def replicate_init():
    # import the modules that create new CLI routes
    import cliplugs.ytauth # noqa: F401
    import cliplugs.finance # noqa: F401
    import cliplugs.contacts # noqa: F401
    import cliplugs.roscoe # noqa: F401


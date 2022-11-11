# no global imports, this is a site specific file which defines the set of
# plug-ins and styling that fleshes out the rtx client.

VENDOR_SLUG = "lmsDataSuite"
APPLICATION_SLUG = "lmsDataSuite"
APPLICATION_NAME = "lms Data Suite"


def set_identity(profile=None):
    import client.identity as identity

    if not profile:
        appslug = APPLICATION_SLUG
    else:
        appslug = f"{APPLICATION_SLUG}-{profile}"

    identity.update_identity(
        vendor_slug=VENDOR_SLUG, app_slug=appslug, app_name=APPLICATION_NAME
    )


def qt_app_init(plugpoint):
    from PySide6 import QtWidgets, QtGui
    import rtlib
    import apputils
    import client as climod
    import lmssystem.lmsicons

    app = QtWidgets.QApplication([])
    app.setOrganizationDomain("lms.kiwistrawberry.us")
    app.setOrganizationName(VENDOR_SLUG)
    app.setApplicationName(APPLICATION_NAME)
    app.icon = QtGui.QIcon(":/lms/jlm_initials.ico")
    app.exports_dir = climod.LocalDirectory(appname=APPLICATION_SLUG, tail="Exports")

    import platform

    if platform.system() == "Windows":
        # This is needed to display the app icon on the taskbar on Windows 7
        import ctypes

        myappid = f"{app.organizationDomain()}.1.0.0"  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    import pyhacc.gui as pg
    import contacts.gui as cg
    import databits.gui as dbg
    import client.qt.rtauth as rtauth

    rtlib.add_type_definition_plugin(pg.AccountingWidgetsPlugin())
    rtlib.add_type_definition_plugin(cg.WidgetsPlugin())
    rtlib.add_type_definition_plugin(rtlib.BasicTypePlugin())
    rtlib.add_type_definition_plugin(apputils.BasicWidgetsPlugin())

    plugpoint.add_extension_plug(pg.AccountingExtensions())
    plugpoint.add_extension_plug(pg.RoscoeExtensions())
    plugpoint.add_extension_plug(cg.ContactExtensions())
    plugpoint.add_extension_plug(dbg.DataBitExtensions())
    plugpoint.add_extension_plug(rtauth.RtAuthPlugs())

    return app


def replicate_init():
    # import the modules that create new CLI routes
    import cliplugs.ytauth  # noqa: F401
    import cliplugs.finance  # noqa: F401
    import cliplugs.contacts  # noqa: F401
    import cliplugs.roscoe  # noqa: F401

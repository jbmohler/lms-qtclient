#!/usr/bin/env python
import sys
import platform
import argparse
import client as climod
import client.qt as cqt
import localconfig

if platform.system() != "Windows":
    # if one wanted to support windows, it may be reasonable to start at
    # https://stackoverflow.com/questions/48542644/python-and-windows-named-pipes
    import client.cmdserver_unix as cmdserver

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rtx Client Application")
    parser.add_argument(
        "--server",
        "-s",
        dest="server_url",
        help="base URL on webapp server (e.g. https://rtx.rtlib.com/app)",
    )
    parser.add_argument("--profile", "-p", help="profile name")
    parser.add_argument("--document", "-d", help="document to show immediately")

    args = parser.parse_args()

    localconfig.set_identity(args.profile)
    session = climod.auto_session(args.server_url)

    launch = True
    if platform.system() != "Windows":
        if cmdserver.is_server_running():
            launch = not cmdserver.request_document(args.document)

    if launch:
        app = localconfig.qt_app_init(cqt.plugpoint)
        cqt.basic_shell_window(app, session, document=args.document)

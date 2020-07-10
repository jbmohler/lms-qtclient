#!/usr/bin/env python
import sys
import argparse
import client as climod
import client.qt as cqt
import localconfig

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rtx Client Application')
    parser.add_argument('--server', '-s', dest='server_url', 
            help='base URL on webapp server (e.g. https://rtx.rtlib.com/app)')
    parser.add_argument('--document', '-d', 
            help='document to show immediately')

    args = parser.parse_args()

    presession = climod.auto_env_url(args.server_url)

    if presession == None:
        sys.stderr.write('provide a session in --server or .yenot_pass')
        parser.print_help()
        sys.exit(2)

    app = localconfig.qt_app_init(cqt.gridmgr)
    cqt.basic_shell_window(app, presession, document=args.document)

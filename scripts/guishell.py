#!/usr/bin/env python
import os
import urllib.parse
import sys
import argparse
import client.qt as cqt

def read_yenotpass():
    ypfile = os.path.join(os.path.expanduser('~'), '.yenotpass')

    results = {}

    if os.path.exists(ypfile):
        with open(ypfile, 'r') as yp:
            lines = list(yp)
            results = dict(s.strip().split('=') for s in lines if s.strip() != '')

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rtx Client Application')
    parser.add_argument('--server', dest='server_url', 
            help='base URL on webapp server (e.g. https://rtx.rtlib.com/app)')
    parser.add_argument('--document', '-d', 
            help='document to show immediately')

    args = parser.parse_args()

    server = None
    if args.server_url != None:
        server = args.server_url
    elif 'RTX_SERVER' in os.environ:
        server = os.environ['RTX_SERVER']
    else:
        servers = read_yenotpass()

        if 'default' in servers:
            url = servers['default']

            raw = urllib.parse.urlparse(url)
            nl = raw.netloc
            username = raw.username
            password = raw.password
            raw = raw._replace(netloc=nl.split('@')[1])
            server = raw.geturl()

            os.environ['RTX_CREDENTIALS'] = '{}:{}'.format(username, password)

    if server == None or not server.startswith('http'):
        sys.stderr.write('error:  server string must point to an http server\n')
        parser.print_help()
        sys.exit(2)

    if not server.endswith('/'):
        server += '/'

    cqt.basic_shell_window(server, document=args.document)

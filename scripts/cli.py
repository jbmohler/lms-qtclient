#!/usr/bin/env python
import os
import re
import getpass
import argparse
import datetime
import rtxsite
import client as rtxclient
import rtlib

def prompt(self):
    return 'rtx {}$'.format(self.rtx_user.lower())
rtxclient.RtxSession.prompt = prompt

class ProcessorExit(BaseException):
    pass

class Processor:
    def __init__(self, session):
        self.session = session
        self.app = None
        self.last_table = None

    def execute(self, cmd):
        processed = False
        if cmd == 'quit':
            raise ProcessorExit()
        if cmd == 'chpass':
            oldpass = getpass.getpass('Old Password:  ')
            while True:
                newpas1 = getpass.getpass('New Password:  ')
                newpass = getpass.getpass('Re-enter Password:  ')
                if newpas1 == newpass:
                    client = self.session.get_client()
                    client.post('api/user/me/change-password', data={'oldpass': oldpass, 'newpass': newpass})
                    break
                else:
                    print('passwords not matched; re-enter')
            processed = True
        if cmd == 'gui':
            import client.qt as cqt
            if self.app == None:
                self.app = cqt.qt_app_init()
            cqt.rtx_main_window_embedded(session=self.session)
            processed = True
        if cmd == 'reports':
            client = self.session.std_client()
            payload = client.get('api/user/logged-in/reports')
            table = payload.main_table()
            self.show_table(table)
            processed = True
        if cmd == 'balsheet':
            client = self.session.std_client()
            payload = client.get('api/gledger/balance-sheet', date=datetime.date.today())
            table = payload.main_table()
            self.show_table(table)
            processed = True
        m = re.match(r'\.([0-9]+)( |$)', cmd)
        if m != None:
            row = self.last_table.rows[int(m.group(1))-1]
            client = self.session.std_client()
            payload = client.get(row.url)
            table = payload.main_table()
            self.show_table(table)
            processed = True
        return processed

    def show_table(self, table):
        self.last_table = table
        columns = []
        for c in table.columns:
            if c.attr in table.DataRow.model_columns:
                columns.append(c)
            if len(columns) > 3:
                break
        def width(c):
            return 15
        for c in columns:
            c.cli_width = width(c)
        def formatter(row, c):
            v = getattr(row, c.attr)
            s = c.formatter(v)
            if len(s) >= c.cli_width:
                s = s[:c.cli_width-3]+'...'
            if c.alignment == 'right':
                return s.rjust(c.cli_width)
            else:
                return s.ljust(c.cli_width)
        for index, row in enumerate(table.rows):
            x = ['.{:<2n}']+['{:15s}']*len(columns)
            args = [index+1]
            args += [formatter(row, c) for c in columns]
            print(' '.join(x).format(*args))


def main(username=None):
    session = rtxclient.RtxSession(os.environ['RTHACC_SERVER'])

    if username != None:
        print('Username:  {}'.format(username))
    else:
        username = input('Username:  ')
    while True:
        password = getpass.getpass('Password:  ')
        try:
            session.authenticate(username, password)
            break
        except Exception as e:
            print(e)
    p = Processor(session)

    while True:
        try:
            cmd = input(session.prompt()+'  ')
            if not p.execute(cmd):
                print('unrecognized')
        except KeyboardInterrupt:
            print()
            break
        except ProcessorExit:
            break
        except Exception as e:
            print(e)

    session.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser('hacc2 command line')
    parser.add_argument('--user', '-u', default=None, help='username')
    args = parser.parse_args()

    main(args.user)

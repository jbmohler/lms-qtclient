import atexit
import os
import sys
import shlex
import readline
import argparse
import getpass
import replicate
import client as climod
import localconfig

def loop(session, commands=None):
    cli = replicate.init_global_router({'session': session})

    localconfig.replicate_init()

    import rtlib
    rtlib.add_type_definition_plugin(rtlib.BasicTypePlugin())

    while True:
        if commands != None:
            if len(commands) == 0:
                return
            cmd = commands[0]
            commands = commands[1:]
        else:
            try:
                cmd = input('>>> ')
            except EOFError:
                print()
                return

        if cmd in ('', '?'):
            cli.basic_help()
            continue
        cmd, *args = shlex.split(cmd)
        if cmd in ('quit', 'exit'):
            return

        readline.set_auto_history(False)
        try:
            if cli.execute(cmd, args):
                pass
            else:
                print('No command found.')
        except replicate.UserError as e:
            print(str(e))
        except climod.RtxError as e:
            print(str(e))
        except Exception as e:
            print('ERROR -- {}'.format(str(e)))
        finally:
            readline.set_auto_history(True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Yenot CLI')
    parser.add_argument('--server', '-s', dest='server_url', 
            help='base URL on webapp server (e.g. https://rtx.rtlib.com/app)')
    parser.add_argument('--command', '-c', nargs='*', 
            help='command(s) to run and then exit')

    args = parser.parse_args()

    presession = climod.auto_env_url(args.server_url)

    if presession == None:
        sys.stderr.write('provide a session in --server or ~/.yenotpass\n')
        parser.print_help()
        sys.exit(2)

    histfile = os.path.join(os.path.expanduser("~"), ".yenot_history")

    try:
        readline.read_history_file(histfile)
        h_len = readline.get_current_history_length()
    except FileNotFoundError:
        open(histfile, 'wb').close()
        h_len = 0

    def save(prev_h_len, histfile):
        new_h_len = readline.get_current_history_length()
        readline.set_history_length(1000)
        readline.append_history_file(new_h_len - prev_h_len, histfile)
    atexit.register(save, h_len, histfile)

    session = climod.RtxSession(presession.server)
    client = session.raw_client()
    client.get('api/monitor')

    print('Connected to {} ...'.format(session.server_url), file=sys.stderr)

    if presession.username is None or presession.password is None:
        username = input('username [{}]: '.format(presession.username))
        if username == '':
            username = presession.username
        password = getpass.getpass('password: ')
    else:
        username = presession.username
        password = presession.password

    session.authenticate(username, password)

    try:
        loop(session, args.command)
    finally:
        session.close()

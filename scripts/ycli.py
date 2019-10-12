import atexit
import os
import readline
import argparse
import urllib.parse
import getpass
import replicate
import client as climod

def loop(session, commands=None):
    cli = replicate.init_global_router({'session': session})

    # import the modules that create new CLI routes
    import cliplugs.ytauth # noqa: F401
    import cliplugs.finance # noqa: F401
    import cliplugs.contacts # noqa: F401

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
        cmd, *args = cmd.split(' ')
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
    parser.add_argument('--server', '-s', help='server to connect to')
    parser.add_argument('--command', '-c', nargs='*', help='command(s) to run and then exit')

    args = parser.parse_args()

    if args.server != None:
        server = args.server
    else:
        servers = climod.read_yenotpass()

        if 'default' in servers:
            url = servers['default']

            raw = urllib.parse.urlparse(url)
            nl = raw.netloc
            username = raw.username
            password = raw.password
            raw = raw._replace(netloc=nl.split('@')[1])
            server = raw.geturl()
        else:
            server = input('Server Name:  ')
            username = input('Username:  ')
            password = getpass.getpass('Password:  ')

    session = climod.RtxSession(server)

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

    client = session.raw_client()
    client.get('api/monitor')

    print('Connected to {} ...'.format(server))

    session.authenticate(username, password)

    try:
        loop(session, args.command)
    finally:
        session.close()

import re
import getpass
import json
import fuzzyparsers
import rtlib
import replicate as api

cli = api.get_global_router()

@cli.command
def change_pin(cmd, args):
    client = cli.session.std_client()
    pw = getpass.getpass('confirm password:')
    pin = getpass.getpass('new pin:')
    phno = input('SMS target:')
    data = {'oldpass': pw, 'newpin': pin, 'target_2fa': json.dumps({'sms': phno})}
    client.post('api/user/me/change-pin', data=data)

@cli.command
def reports(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/user/logged-in/reports')
    api.show_table(results.main_table())

@cli.command
def report(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/user/logged-in/reports')
    regex = args[0]
    for report in results.main_table().rows:
        if re.search(regex, report.act_name):
            print(report)
            results = client.get(report.url)
            api.show_table(results.main_table())
            break

@cli.command
def users(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/users/list')
    api.show_table(results.main_table())

@cli.command
def add_user(cmd, args):
    client = cli.session.std_client()
    username = input('new user name:  ')
    fullname = input('new user full name:  ')
    pass1 = getpass.getpass('new user password:  ')
    pass2 = getpass.getpass('new user password (confirm):  ')
    if pass1 != pass2:
        raise api.UserError('two passwords do not match')
    
    results = client.get('api/roles/list')
    roles = results.main_table()
    api.show_table(roles)
    while True:
        rstr = input('roles (comma separated):  ')

        elected = []
        try:
            for role in rstr.split(','):
                role = role.strip()
                if role == '':
                    continue

                mfunc = lambda t, item: fuzzyparsers.default_match(t.role_name, item)
                match = fuzzyparsers.fuzzy_match(roles.rows, role, mfunc)
                elected.append(match)
        except ValueError:
            print('ambiguous match for "{}"'.format(role))
            continue
        break

    usertab = rtlib.simple_table(['username', 'full_name', 'password', 'roles'])
    with usertab.adding_row() as r2:
        r2.username = username
        r2.full_name = fullname
        r2.password = pass1
        r2.roles = [e.id for e in elected]

    client.post('api/user', files={'user': usertab.as_http_post_file()})

@cli.command
def delete_user(cmd, args):
    client = cli.session.std_client()

    results = client.get('api/users/list')
    users = results.main_table()

    try:
        mfunc = lambda t, item: fuzzyparsers.default_match(t.username, item)
        match = fuzzyparsers.fuzzy_match(users.rows, args[0], mfunc)
    except ValueError:
        raise api.UserError('user not matched')

    client.delete('api/user/{}', match.id)

@cli.command
def roles(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/roles/list')
    api.show_table(results.main_table())

@cli.command
def endpoints(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/endpoints')
    api.show_table(results.main_table())

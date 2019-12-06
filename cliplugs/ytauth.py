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

    table = results.main_table()
    #api.show_table(table)

    if len(args) > 0:
        regex = args[0]
        table.rows = [row for row in table.rows if re.search(regex,
            row.description, flags=re.IGNORECASE)]

    roles = set([(row.role, row.role_sort) for row in table.rows])
    table.rows.sort(key=lambda x: (x.role_sort, x.description))

    rcodes = []
    repcodes = []

    def code1(used, name):
        for c in sorted(name):
            if c == ' ':
                continue
            if c.lower() not in used:
                used.append(c.lower())
                return c.lower()
        raise NotImplementedError('no code found')

    def code3(used, name, prefix):
        uppers = ''.join([c for c in name if 'A' <= c <= 'Z'])
        if len(uppers) >= 2:
            candidate = (prefix+uppers[:2]).lower()
            if candidate not in used:
                used.append(candidate)
                return candidate

        for c, d in zip(name[:-1], name[1:]):
            candidate = (prefix+c+d).lower()
            if candidate not in used:
                used.append(candidate)
                return candidate
        raise NotImplementedError('no code found')

    for role, rs in sorted(roles, key=lambda x: x[1]):
        code = code1(rcodes, role)
        print('{} {}'.format(code, role))

        for row in table.rows:
            if row.role == role:
                icode = code3(repcodes, row.description, code)
                row.code = icode
                print('   {} {}'.format(icode, row.description))

    while True:
        rcode = input('report (code):  ')
        for row in table.rows:
            if rcode == row.code:
                _run_report(row)
                return

def _run_report(report):
    client = cli.session.std_client()
    #print(report)
    kwargs = {}
    for pattr, props in report.prompts:
        if props != None and 'default' in props:
            kwargs[pattr] = props['default']
    results = client.get(report.url, **kwargs)
    api.show_table(results.main_table())

@cli.command
def report(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/user/logged-in/reports')
    regex = args[0]
    for report in results.main_table().rows:
        if re.search(regex, report.act_name):
            _run_report(report)
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

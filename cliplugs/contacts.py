import os
import subprocess
import textwrap
import curtsies
import replicate as api
import cliutils

cli = api.get_global_router()

class KeyTerm(Exception):
    pass

def keywatcher(shortcuts):
    with curtsies.Input(keynames='curtsies') as input_generator:
        for e in curtsies.Input():
            if e in shortcuts:
                shortcuts[e]()

def copy_clip(s):
    if cliutils.is_wsl():
        p = subprocess.Popen(['clip.exe'], stdin=subprocess.PIPE)
        p.communicate(input=s.encode('ascii'))
    elif os.environ.get('DISPLAY', '') != '':
        p = subprocess.Popen(['xclip', '-sel', 'clip'], stdin=subprocess.PIPE)
        p.communicate(input=s.encode('ascii'))
    else:
        print('>>>{}<<<'.format(s))

def open_browser(u):
    cliutils.xdg_open(u)

@cli.command
def contact(cmd, args):
    client = cli.session.std_client()
    results = client.get('api/personas/list', frag=' '.join(args))
    table = results.main_table()
    if len(table.rows) > 1:
        api.show_table(table)
        while True:
            ii = input('row index to expand:  ')
            if len(ii) == 0:
                break
            try:
                rowindex = int(ii)
                table.rows = [table.rows[rowindex-1]]
                break
            except:
                pass
    elif len(table.rows) == 0:
        print('no contacts found')

    if len(table.rows) == 1:
        content = client.get('api/persona/{}', table.rows[0].id)

        def stop():
            raise KeyTerm('exit loop')

        shortcuts = {
                '<Ctrl-d>': stop,
                '<Ctrl-j>': stop}
        print(persona_to_text(content, shortcuts))
        try:
            print('press enter to continue')
            keywatcher(shortcuts)
        except KeyTerm:
            pass

def wraptext(paragraph):
    concat = []
    lines = paragraph.split('\n')
    for line in lines:
        wrapped = textwrap.wrap(line, width=60)
        wrapped = '\n'.join(wrapped)
        concat.append(textwrap.indent(wrapped, ' '*4))
    return '\n'.join(concat)

def bit_wrap(bit, actual):
    concat = []
    if bit.name != None and bit.name != '':
        concat.append('Name:  {}'.format(bit.name))
    concat.append(actual)
    if bit.memo != None and bit.memo != '':
        concat.append(wraptext(bit.memo))
    return '\n'.join(concat+[''])

def persona_to_text(content, shortcuts):
    per = content.named_table('persona')
    bits = content.named_table('bits')

    chunks = []
    head = "{0.l_name} {0.f_name}".format(per.rows[0])
    chunks.append(head)
    if per.rows[0].memo not in ['', None]:
        chunks.append(wraptext(per.rows[0].memo))
    chunks.append('')

    for bit in bits.rows:
        if bit.bit_type == 'email_addresses':
            data = 'e-mail:  {}'.format(bit.bit_data['email'])
        if bit.bit_type == 'urls':
            lines = []
            if bit.bit_data['url'] not in [None, '']:
                lines.append('url:  {} (view u)'.format(bit.bit_data['url']))
                shortcuts['u'] = lambda x=bit.bit_data['url']: open_browser(x)
            if bit.bit_data['username'] not in [None, '']:
                lines.append('username:  {} (copy b)'.format(bit.bit_data['username']))
                shortcuts['b'] = lambda x=bit.bit_data['username']: copy_clip(x)
            if bit.bit_data['password'] not in [None, '']:
                lines.append('password:  {} (copy c)'.format('** hidden **'))
                shortcuts['c'] = lambda x=bit.bit_data['password']: copy_clip(x)
            data = '\n'.join(lines)
        if bit.bit_type == 'street_addresses':
            lines = []
            if bit.bit_data['address1'] not in [None, '']:
                lines.append(bit.bit_data['address1'])
            if bit.bit_data['address2'] not in [None, '']:
                lines.append(bit.bit_data['address2'])
            if bit.bit_data['city'] not in [None, '']:
                lines.append('{} {} {}'.format(bit.bit_data['city'],
                    bit.bit_data['state'], bit.bit_data['zip']))
            if bit.bit_data['country'] not in [None, '']:
                lines.append(bit.bit_data['country'])
            data = '\n'.join(lines)
        if bit.bit_type == 'phone_numbers':
            data = 'phone:  {}'.format(bit.bit_data['number'])
        chunks.append(bit_wrap(bit, data))
    return '\n'.join(chunks)

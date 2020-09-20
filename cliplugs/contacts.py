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
    with curtsies.Input(keynames="curtsies") as input_generator:
        for e in curtsies.Input():
            if e in shortcuts:
                shortcuts[e]()


def copy_clip(s):
    if cliutils.is_wsl():
        p = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE)
        p.communicate(input=s.encode("ascii"))
    elif os.environ.get("DISPLAY", "") != "":
        p = subprocess.Popen(["xclip", "-sel", "clip"], stdin=subprocess.PIPE)
        p.communicate(input=s.encode("ascii"))
    else:
        print(f">>>{s}<<<")


def open_browser(u):
    cliutils.xdg_open(u)


@cli.command
def contact(cmd, args):
    client = cli.session.std_client()
    results = client.get("api/personas/list", frag=" ".join(args))
    table = results.main_table()
    if len(table.rows) > 1:
        api.show_table(table)
        while True:
            ii = input("row index to expand:  ")
            if len(ii) == 0:
                break
            try:
                rowindex = int(ii)
                table.rows = [table.rows[rowindex - 1]]
                break
            except:
                pass
    elif len(table.rows) == 0:
        print("no contacts found")

    if len(table.rows) == 1:
        content = client.get("api/persona/{}", table.rows[0].id)

        def stop():
            raise KeyTerm("exit loop")

        shortcuts = {"<Ctrl-d>": stop, "<Ctrl-j>": stop}
        print(persona_to_text(content, shortcuts=shortcuts))
        try:
            print("press enter to continue")
            keywatcher(shortcuts)
        except KeyTerm:
            pass


@cli.command
def generate_security_answers(cmd, args):
    client = cli.session.std_client()

    bits = 50
    if len(args) > 0:
        bits = int(args[0])

    print("For each security question entered a random word answer will be generated.")

    index = 1
    while True:
        q1 = input(f"Q{index}: ")
        if q1 == "":
            break

        content = client.get("api/password/generate", mode="words", bits=bits)

        a1 = content.keys["password"]

        print(f"A{index}: {a1}")

        index += 1


def wraptext(paragraph):
    concat = []
    lines = paragraph.split("\n")
    for line in lines:
        wrapped = textwrap.wrap(line, width=60)
        wrapped = "\n".join(wrapped)
        concat.append(textwrap.indent(wrapped, " " * 4))
    return "\n".join(concat)


def bit_wrap(bit, actual):
    concat = []
    if bit.name != None and bit.name != "":
        concat.append(f"Name:  {bit.name}")
    concat.append(actual)
    if bit.memo != None and bit.memo != "":
        concat.append(wraptext(bit.memo))
    return "\n".join(concat + [""])


def persona_to_text(content, static=False, shortcuts=None, tagtable=None):
    if static and shortcuts:
        raise NotImplementedError("no shortcuts given for static output")
    if not static and not shortcuts:
        raise NotImplementedError("shortcuts required if not static")

    per = content.named_table("persona").rows[0]
    bits = content.named_table("bits")

    chunks = []
    chunks.append(per.entity_name)
    if per.memo not in ["", None]:
        chunks.append(wraptext(per.memo))
    chunks.append("")

    for bit in bits.rows:
        if bit.bit_type == "email_addresses":
            data = f"e-mail:  {bit.bit_data['email']}"
        if bit.bit_type == "phone_numbers":
            data = f"phone:  {bit.bit_data['number']}"
        if bit.bit_type == "urls":
            lines = []
            if static:
                if bit.bit_data["url"] not in [None, ""]:
                    lines.append(f"url:  {bit.bit_data['url']}")
                if bit.bit_data["username"] not in [None, ""]:
                    lines.append(f"username:  {bit.bit_data['username']}")
                if bit.bit_data["password"] not in [None, ""]:
                    lines.append(f"password:  {bit.bit_data['password']}")
            else:
                if bit.bit_data["url"] not in [None, ""]:
                    lines.append(f"url:  {bit.bit_data['url']} (view u)")
                    shortcuts["u"] = lambda x=bit.bit_data["url"]: open_browser(x)
                if bit.bit_data["username"] not in [None, ""]:
                    lines.append(f"username:  {bit.bit_data['username']} (copy b)")
                    shortcuts["b"] = lambda x=bit.bit_data["username"]: copy_clip(x)
                if bit.bit_data["password"] not in [None, ""]:
                    lines.append("password:  ** hidden ** (copy c)")
                    shortcuts["c"] = lambda x=bit.bit_data["password"]: copy_clip(x)
            data = "\n".join(lines)
        if bit.bit_type == "street_addresses":
            lines = []
            if bit.bit_data["address1"] not in [None, ""]:
                lines.append(bit.bit_data["address1"])
            if bit.bit_data["address2"] not in [None, ""]:
                lines.append(bit.bit_data["address2"])
            if bit.bit_data["city"] not in [None, ""]:
                lines.append(
                    "{} {} {}".format(
                        bit.bit_data["city"], bit.bit_data["state"], bit.bit_data["zip"]
                    )
                )
            if bit.bit_data["country"] not in [None, ""]:
                lines.append(bit.bit_data["country"])
            data = "\n".join(lines)
        chunks.append(bit_wrap(bit, data))

    if tagtable:
        for tag in tagtable.rows:
            if tag.id in per.tag_ids:
                chunks.append(tag.path_name)

    return "\n".join(chunks)


@cli.command
def dump_tagged_contacts(cmd, args):
    client = cli.session.std_client()

    (tagname,) = args

    tags = client.get("api/tags/list")

    tag_id = [tag.id for tag in tags.main_table().rows if tag.name == tagname][0]

    personas = client.get("api/personas/list", tag_id=tag_id)

    for persona in personas.main_table().rows:
        content = client.get("api/persona/{}", persona.id)

        print(persona_to_text(content, static=True, tagtable=tags.main_table()))
        print("\n#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#\n")

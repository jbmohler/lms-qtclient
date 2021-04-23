import os
import json
import socket
import threading
import select
from . import identity


SUCCESS = b"launched"


def get_signal_filename():
    return os.path.join(identity.get_appdata_dir(), "gui-server")


def launch_document_server(callback):
    t = threading.Thread(target=_server_thread, args=(callback,))
    t.start()


def close_document_server():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(get_signal_filename())
    obj = {"type": "close_thread"}

    s.send(json.dumps(obj).encode("utf8"))
    s.close()


def _server_thread(callback):
    sigfile = get_signal_filename()

    launcher = callback()

    try:
        sockdir = os.path.dirname(sigfile)
        os.mkdir(os.path.expanduser(sockdir))
    except FileExistsError:
        pass
    if os.path.exists(sigfile):
        os.remove(sigfile)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sigfile)
    running = True
    while running:
        server.listen(1)
        conn, addr = server.accept()
        datagram = conn.recv(1024)
        if datagram:
            obj = json.loads(datagram.decode("utf8"))
            if obj["type"] == "open":
                launcher.open(obj["url"])
                conn.send(SUCCESS)
            elif obj["type"] == "close_thread":
                running = False
            else:
                conn.send("-1")
            conn.close()
    os.remove(sigfile)


def is_server_running():
    return os.path.exists(get_signal_filename())


def request_document(document):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(get_signal_filename())
    obj = {"type": "open", "url": document}

    s.send(json.dumps(obj).encode("utf8"))
    select.select([s], [], [], 10)
    result = s.recv(1024) == SUCCESS
    s.close()

    return result

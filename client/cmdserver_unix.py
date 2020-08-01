#!/usr/bin/env python
import os
import json
import socket
import threading
import select

PATH = os.path.expanduser("~/.rtx/gui-server")
SUCCESS = b"launched"


def launch_document_server(callback):
    t = threading.Thread(target=_server_thread, args=(callback,))
    t.start()


def close_document_server():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(PATH)
    obj = {"type": "close_thread"}

    s.send(json.dumps(obj).encode("utf8"))
    s.close()


def _server_thread(callback):
    launcher = callback()

    try:
        sockdir = os.path.dirname(PATH)
        os.mkdir(os.path.expanduser(sockdir))
    except FileExistsError:
        pass
    if os.path.exists(PATH):
        os.remove(PATH)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(PATH)
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
    os.remove(PATH)


def is_server_running():
    return os.path.exists(PATH)


def request_document(document):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(PATH)
    obj = {"type": "open", "url": document}

    s.send(json.dumps(obj).encode("utf8"))
    select.select([s], [], [], 10)
    result = s.recv(1024) == SUCCESS
    s.close()

    return result

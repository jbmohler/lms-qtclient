import rtxsite
import client as climod

ENTITIES = [
    ("transaction", "transactions"),
    ("account", "accounts"),
    ("accounttype", "accounttypes"),
    ("journal", "journals"),
]

URL_LIST = "api/{p}/list"
URL_NEW = "api/{s}/new"
URL_EDIT = "api/{s}/{id}"


def test_entity(client, singular, plural):
    payload = client.get(URL_LIST.format(p=plural))
    items = payload.main_table()

    payload = client.get(URL_NEW.format(s=singular))
    item = payload.main_table()


def main(session):
    global ENTITIES

    blah = session.std_client()

    for singular, plural in ENTITIES:
        test_entity(blah, singular, plural)


if __name__ == "__main__":
    session = climod.auto_session()
    try:
        main(session)
    finally:
        session.close()
